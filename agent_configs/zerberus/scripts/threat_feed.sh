#!/bin/bash
# threat_feed.sh — Zerberus Supply Chain Threat Monitor
# SILENT MODE: Kein Chat-Output
set -euo pipefail

exec 1>/dev/null 2>/dev/null

LOG="/var/log/cron-silent/zerberus_threat.log"
mkdir -p "$(dirname $LOG)" 2>/dev/null || true
echo "[$(date '+%Y-%m-%d %H:%M')] Threat Feed Check gestartet" >> "$LOG" 2>/dev/null || true

THREATS=("plain-crypto-js" "node-llama-cpp-malicious" "openclaw-fake" "clawdbot-stealer")
LOCAL_HITS=0
for threat in "${THREATS[@]}"; do
 hits=$(find /home/iggy/.npm-global/ -name "${threat}*" -type d 2>/dev/null | wc -l)
 if [ "$hits" -gt 0 ]; then
 echo "[$(date '+%Y-%m-%d %H:%M')] GEFUNDEN: $threat" >> "$LOG" 2>/dev/null || true
 LOCAL_HITS=$((LOCAL_HITS + hits))
 fi
done
psql -h 127.0.0.1 -U scraper -d metamaus -c "
 INSERT INTO agent_logs (agent, level, message, timestamp)
 VALUES ('zerberus', 'info', '[THREAT_SCAN] $LOCAL_HITS package(s) scanned', NOW());" 2>/dev/null || true

echo "[$(date '+%Y-%m-%d %H:%M')] Scan abgeschlossen: $LOCAL_HITS hits" >> "$LOG" 2>/dev/null || true
echo "EXIT_SILENT: threat_feed.sh complete" >> "$LOG" 2>/dev/null || true
exit 0
