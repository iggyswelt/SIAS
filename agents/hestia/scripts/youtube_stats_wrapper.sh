#!/bin/bash
# Wrapper für YouTube Stats - läuft via system crontab

LOGFILE="/home/iggy/.openclaw/logs/youtube_stats.log"
source /home/iggy/.openclaw/.env
CHAT_ID="[TELEGRAM_ID]"

# YouTube Stats via Dashboard API
RESULT=$(curl -s -X POST http://localhost:5000/api/youtube/refresh)

if echo "$RESULT" | grep -q "error\|failed"; then
    MSG="⚠️ YouTube Stats: Fehler"
else
    MSG="📊 YouTube Stats ✅ aktualisiert"
fi

# Telegram
curl -s -X POST "https://api.telegram.org/bot$TELEGRAM_BOT_TOKEN/sendMessage" \
    -d "chat_id=$CHAT_ID" -d "text=$MSG" > /dev/null 2>&1

echo "$(date): $MSG" >> "$LOGFILE"
