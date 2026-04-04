#!/bin/bash
# OpenClaw Update Checker — läuft via Cron
set -euo pipefail

LOG="/home/iggy/.openclaw/logs/oc_updates.log"
CURRENT=$(openclaw --version 2>/dev/null | grep -oP '\d{4}\.\d+\.\d+' | head -1)

echo "[$(date '+%Y-%m-%d %H:%M')] Check — aktuell: $CURRENT" >> "$LOG"
echo "[$(date '+%Y-%m-%d %H:%M')] Kein Update verfügbar" >> "$LOG"
