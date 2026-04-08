#!/bin/bash
# Wrapper für Demo Scout NRW - läuft via system crontab

LOGFILE="/home/iggy/.openclaw/logs/demo_scout_nrw.log"
source /home/iggy/.openclaw/.env
CHAT_ID="[TELEGRAM_ID]"

# Ausführung
echo "=== Demo Scout NRW - $(date) ===" >> "$LOGFILE"
OUTPUT=$(python3 /home/iggy/.openclaw/scripts/demo_scout_nrw.py 2>&1)
echo "$OUTPUT" >> "$LOGFILE"

# Parse Output für Telegram
if echo "$OUTPUT" | grep -q "Keine neuen"; then
    # Keine Events - kein Spam (leise)
    echo "$(date): Keine neuen Events - keine Nachricht" >> "$LOGFILE"
else
    # Events gefunden - Telegram
    MSG="🕵️ Demo Scout NRW: Events gefunden, Details im Log"
    curl -s -X POST "https://api.telegram.org/bot$TELEGRAM_BOT_TOKEN/sendMessage" \
        -d "chat_id=$CHAT_ID" -d "text=$MSG" -d "parse_mode=Markdown" > /dev/null 2>&1
    echo "$(date): Telegram gesendet" >> "$LOGFILE"
fi
