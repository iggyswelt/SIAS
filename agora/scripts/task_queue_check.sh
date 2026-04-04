#!/bin/bash
# task_queue_check.sh — Agents holen sich Tasks selbst
# Usage: bash task_queue_check.sh <agent_name>
set -euo pipefail

AGENT="${1:-unknown}"

# Hole nächsten pending Task und update auf running mit einem einzigen query
TASK=$(psql -h 127.0.0.1 -U scraper -d metamaus -t -A -P footer=off -c \
  "WITH picked AS (
     SELECT id FROM agent_tasks
     WHERE agent='$AGENT' AND status='pending'
     ORDER BY priority DESC, created_at ASC
     LIMIT 1 FOR UPDATE SKIP LOCKED
   ), updated AS (
     UPDATE agent_tasks
     SET status='running', started_at=NOW()
     FROM picked
     WHERE agent_tasks.id = picked.id
     RETURNING agent_tasks.id, agent_tasks.task
   )
   SELECT id || '|' || task FROM updated;" 2>/dev/null || true)

# Whitespace trimmen
TASK="$(echo "$TASK" | xargs 2>/dev/null || echo "")"

if [ -n "$TASK" ] && echo "$TASK" | grep -q '|'; then
  TASK_ID="${TASK%%|*}"
  TASK_TEXT="${TASK#*|}"
  echo "📋 Task gefunden: [${TASK_ID}] ${TASK_TEXT}"
  echo "🔄 Status auf 'running' gesetzt — Agent ${AGENT} kann loslegen"
else
  echo "✅ Keine pending Tasks für $AGENT — HEARTBEAT_OK"
fi
