#!/bin/bash
# Wrapper für demo_scraper_v2.py - läuft via system crontab

LOGFILE="/home/iggy/.openclaw/logs/demo_scraper_v2.log"
source /home/iggy/.openclaw/.env
CHAT_ID="[TELEGRAM_ID]"

# Ausführung
echo "=== Demo Scraper v2 - $(date) ===" >> "$LOGFILE"
python3 /home/iggy/.openclaw/workspace/demo_scraper_v2.py >> "$LOGFILE" 2>&1
RESULT=$?

# Telegram wenn Fehler oder viele neue Demos
if [ $RESULT -ne 0 ]; then
    MSG="⚠️ Demo-Scraper v2: Fehler (Exit $RESULT)"
    curl -s -X POST "https://api.telegram.org/bot$TELEGRAM_BOT_TOKEN/sendMessage" \
        -d "chat_id=$CHAT_ID" -d "text=$MSG" > /dev/null 2>&1
fi

exit 0
