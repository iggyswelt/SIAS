#!/bin/bash
set -euo pipefail
LOG="/home/iggy/.openclaw/logs/zerberus_zombie.log"
MAX_MINUTES=15

ZOMBIES=$(psql -h 127.0.0.1 -U scraper -d metamaus -t -c "
  SELECT id, agent, LEFT(task, 40)
  FROM agent_tasks
  WHERE status = 'running'
  AND started_at < NOW() - INTERVAL '${MAX_MINUTES} minutes'
  ORDER BY started_at ASC;" 2>/dev/null)

if [ -z "$ZOMBIES" ]; then
  echo "[$(date '+%Y-%m-%d %H:%M')] Clean" >> "$LOG"
  exit 0
fi

KILLED=0
while IFS='|' read -r id agent task; do
  id=$(echo "$id" | tr -d ' ')
  [ -z "$id" ] && continue
  psql -h 127.0.0.1 -U scraper -d metamaus -c "
    UPDATE agent_tasks SET status='failed', done_at=NOW(),
    result='ZOMBIE KILLED by Zerberus — ${MAX_MINUTES}min timeout'
    WHERE id=${id} AND status='running';" 2>/dev/null
  echo "[$(date '+%Y-%m-%d %H:%M')] KILLED #${id}" >> "$LOG"
  KILLED=$((KILLED + 1))
done <<< "$ZOMBIES"

echo "[$(date '+%Y-%m-%d %H:%M')] $KILLED Zombies gekillt" >> "$LOG"
