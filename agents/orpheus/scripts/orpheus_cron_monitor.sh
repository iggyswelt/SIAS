#!/bin/bash
# Orpheus Cron-Monitor — prüft ob Agents doppelt laufen

LOG="/home/iggy/.openclaw/logs/orpheus_cron_monitor.log"
DATE=$(date '+%Y-%m-%d %H:%M')
ISSUES=0

echo "[$DATE] Orpheus Cron-Monitor Start" >> "$LOG"

# Alle bekannten Agent-Scripts
AGENTS=(
 "hermes_scrape_v4.sh"
 "hermes_learn.sh"
 "run_autonomous.py"
)

for AGENT in "${AGENTS[@]}"; do
 COUNT=$(crontab -l 2>/dev/null | grep -c "$AGENT")
 if [ "$COUNT" -gt 1 ]; then
 echo "[$DATE] ⚠️ DOPPELT: $AGENT läuft ${COUNT}x" >> "$LOG"
 ISSUES=$((ISSUES + 1))
 else
 echo "[$DATE] ✅ OK: $AGENT (${COUNT}x)" >> "$LOG"
 fi
done

# Orpheus backup count heute:
TODAY=$(date '+%Y%m%d')
BACKUP_COUNT=$(find /home/iggy/backups/orpheus/ -maxdepth 1 -name "*${TODAY}*.sql" | wc -l)
EXPECTED=24
if [ "$BACKUP_COUNT" -gt "$((EXPECTED + 8))" ]; then
 echo "[$DATE] ⚠️ Zu viele Backups: ${BACKUP_COUNT} (erwartet ~${EXPECTED})" >> "$LOG"
 ISSUES=$((ISSUES + 1))
fi

echo "[$DATE] Monitor fertig — $ISSUES Issues" >> "$LOG"

# === Hardware Security Check ===
echo "[$DATE] --- Hardware Security ---" >> "$LOG"

# SoloKey angeschlossen?
SOLO=$(lsusb | grep -i "solo\|fido" | wc -l)
if [ "$SOLO" -gt 0 ]; then
 echo "[$DATE] ✅ SoloKey: angeschlossen" >> "$LOG"
else
 echo "[$DATE] ⚠️ SoloKey: NICHT angeschlossen!" >> "$LOG"
 ISSUES=$((ISSUES + 1))
fi

# TPM2 verfügbar?
TPM=$(ls /dev/tpm* 2>/dev/null | wc -l)
if [ "$TPM" -gt 0 ]; then
 echo "[$DATE] ✅ TPM2: verfügbar" >> "$LOG"
else
 echo "[$DATE] ❌ TPM2: NICHT verfügbar!" >> "$LOG"
 ISSUES=$((ISSUES + 1))
fi

# === Freqtrade Check ===
FT=$(docker ps | grep -c freqtrade)
if [ "$FT" -gt 0 ]; then
 echo "[$DATE] ✅ Freqtrade: läuft" >> "$LOG"
else
 echo "[$DATE] ⚠️ Freqtrade: GESTOPPT — restart versuchen" >> "$LOG"
 docker start freqtrade >> "$LOG" 2>&1
 ISSUES=$((ISSUES + 1))
fi

# === System Backup Scanner ===
echo "[$DATE] --- Backup Scanner ---" >> "$LOG"

# Leere Files
EMPTY=$(find /home/iggy/ /opt/ -name "*.sql" -o -name "*.tar.gz" -o -name "*.bak" 2>/dev/null | xargs ls -la 2>/dev/null | awk '$5==0 {print $9}')
if [ -n "$EMPTY" ]; then
 echo "[$DATE] ⚠️ Leere Files: $(echo $EMPTY | wc -w)" >> "$LOG"
fi

# Stray backups
STRAY=$(find /home/iggy/ /opt/ -maxdepth 3 \( -name "backup_*.tar.gz" -o -name "*_backup_*.sql" \) ! -path "*/backups/*" 2>/dev/null)
if [ -n "$STRAY" ]; then
 echo "[$DATE] ⚠️ Stray Backups: $(echo $STRAY | wc -w)" >> "$LOG"
fi

# GitHub Check
cd ~/.openclaw/workspace
DAYS_OLD=$(git log -1 --format="%ct" 2>/dev/null | xargs -I{} sh -c 'echo $(( ($(date +%s) - {}) / 86400 ))' 2>/dev/null || echo 99)
if [ "${DAYS_OLD:-99}" -gt 2 ]; then
 echo "[$DATE] ⚠️ GitHub: ${DAYS_OLD}d alter Commit" >> "$LOG"
else
 echo "[$DATE] ✅ GitHub Backup: $DAYS_OLD Tage" >> "$LOG"
fi

# PKI Cert Check
for CERT in ~/.openclaw/pki/*.pem; do
 [ -f "$CERT" ] || continue
 DAYS=$(openssl x509 -in "$CERT" -noout -enddate 2>/dev/null | cut -d= -f2 | xargs -I{} sh -c 'echo $(( ( $(date -d "{}" +%s) - $(date +%s) ) / 86400 )')
 NAME=$(basename "$CERT" .pem)
 echo "[$DATE] ✅ Cert: $NAME (${DAYS} Tage)" >> "$LOG"
done
