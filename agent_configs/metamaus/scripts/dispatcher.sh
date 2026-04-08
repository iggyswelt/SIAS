#!/bin/bash
# dispatcher.sh — Per-Agent Throttle (Iggy 22:40)
set -euo pipefail

LOG="/home/iggy/.openclaw/logs/dispatcher.log"
mkdir -p "$(dirname $LOG)"

# Timeout pro Agent (Minuten)
declare -A TIMEOUTS
TIMEOUTS[hestia]=180
TIMEOUTS[orpheus]=180
TIMEOUTS[athene]=60
TIMEOUTS[apollon]=15
TIMEOUTS[zerberus]=15
TIMEOUTS[rheingold]=15
TIMEOUTS[hermes]=15
TIMEOUTS[metamaus]=15
TIMEOUTS[pythia]=30

# Timeouts anwenden — alte Tasks zurück auf pending
for agent in "${!TIMEOUTS[@]}"; do
 timeout=${TIMEOUTS[$agent]}
 psql -h 127.0.0.1 -U scraper -d metamaus -c "
 UPDATE agent_tasks 
 SET status='pending', started_at=NULL
 WHERE status='running' 
 AND agent='$agent'
 AND started_at < NOW() - INTERVAL '$timeout minutes';" 2>/dev/null
done

# Dispatche nächsten Task — MAX 1 pro Agent, MAX 4 gesamt
TOTAL_RUNNING=$(psql -h 127.0.0.1 -U scraper -d metamaus -t -c "
 SELECT COUNT(*) FROM agent_tasks WHERE status='running';" \
 2>/dev/null | tr -d ' \n')

if [ "${TOTAL_RUNNING:-0}" -ge 4 ]; then
 echo "[$(date '+%Y-%m-%d %H:%M')] Max 4 erreicht ($TOTAL_RUNNING running)" >> "$LOG"
 exit 0
fi

# Nächsten pending Task holen (Agent darf nur 1 laufen haben)
NEXT=$(psql -h 127.0.0.1 -U scraper -d metamaus -t -c "
 SELECT id '|' agent '|' LEFT(task,80)
 FROM agent_tasks t
 WHERE status='pending'
 AND (
 SELECT COUNT(*) FROM agent_tasks 
 WHERE agent=t.agent AND status='running'
 ) = 0
 ORDER BY priority DESC, created_at ASC 
 LIMIT 1;" 2>/dev/null | tr -d ' ' | head -1)

if [ -z "$NEXT" ]; then
 echo "[$(date '+%Y-%m-%d %H:%M')] Keine pending Tasks" >> "$LOG"
 exit 0
fi

TASK_ID=$(echo "$NEXT" | cut -d'|' -f1)
TASK_AGENT=$(echo "$NEXT" | cut -d'|' -f2)
TASK_TEXT=$(echo "$NEXT" | cut -d'|' -f3-)

psql -h 127.0.0.1 -U scraper -d metamaus -c "
 UPDATE agent_tasks SET status='running', started_at=NOW()
 WHERE id=$TASK_ID;" 2>/dev/null

echo "[$(date '+%Y-%m-%d %H:%M')] DISPATCH [$TASK_ID] $TASK_AGENT" >> "$LOG"
echo "📋 [$TASK_ID] $TASK_AGENT → ${TASK_TEXT:0:60}"

# BLOCKER METRIK — nach jedem Dispatch prüfen
check_blockers() {
 local BLOCKED
 BLOCKED=$(psql -h 127.0.0.1 -U scraper -d metamaus -t -c "
   SELECT agent || ' waiting ' || COUNT(*) || 'x (min ' ||
     MIN(EXTRACT(EPOCH FROM (NOW()-created_at))/60)::int || 'm)'
   FROM agent_tasks
   WHERE status='pending'
   AND agent NOT IN (
     SELECT DISTINCT agent FROM agent_tasks WHERE status='running'
   )
   GROUP BY agent
   HAVING MIN(created_at) < NOW() - INTERVAL '30 minutes'
   ORDER BY MIN(EXTRACT(EPOCH FROM (NOW()-created_at))/60)::int DESC;" 2>/dev/null)

 if [ -n "$BLOCKED" ]; then
   echo "[$(date '+%Y-%m-%d %H:%M')] ⚠️ BLOCKER DETECTED:" >> "$LOG"
   echo "$BLOCKED" >> "$LOG"
 fi
}

check_blockers
