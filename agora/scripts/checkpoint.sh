#!/bin/bash
set -euo pipefail
DESCRIPTION="${1:-manual}"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
SAFE_DESC=$(echo "$DESCRIPTION" | tr ' ' '_' | tr -cd '[:alnum:]_-')
CHECKPOINT="/home/iggy/backups/checkpoints/${TIMESTAMP}_${SAFE_DESC}"
mkdir -p "$CHECKPOINT"
echo "🔒 Checkpoint: $DESCRIPTION → $CHECKPOINT"
tar -czf "${CHECKPOINT}/agents_core.tar.gz" \
 $(find /home/iggy/.openclaw/agents/ -name "*.md" 2>/dev/null) \
 /home/iggy/.openclaw/openclaw.json
pg_dump -h 127.0.0.1 -U scraper metamaus > "${CHECKPOINT}/metamaus_db.sql"
cp -r /home/iggy/.openclaw/agora/scripts/ "${CHECKPOINT}/scripts/"
echo "✅ Checkpoint fertig: $(du -sh ${CHECKPOINT}/)"
echo "${TIMESTAMP} | ${DESCRIPTION}" >> /home/iggy/backups/checkpoints/CHANGELOG.txt
find /home/iggy/backups/checkpoints/ -maxdepth 1 -mindepth 1 -type d -mtime +7 | xargs rm -rf 2>/dev/null || true
echo "📋 Aktive Checkpoints (letzte 5):"
ls -t /home/iggy/backups/checkpoints/ | grep -v CHANGELOG | head -5
