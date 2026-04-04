#!/bin/bash
# Wrapper für News Fetch - läuft via system crontab

# Token aus .env laden
source /home/iggy/.openclaw/.env

LOGFILE="/home/iggy/.openclaw/logs/news_fetch.log"
CHAT_ID="[TELEGRAM_ID]"

# News Fetch via Dashboard API
RESULT=$(curl -s -X POST http://localhost:5000/api/news/fetch)

if echo "$RESULT" | grep -q "error\|failed"; then
    MSG="⚠️ News Fetch: Fehler"
else
    COUNT=$(echo "$RESULT" | grep -oP '"fetched":\s*\K\d+' || echo "unbekannt")
    MSG="📰 News Fetch ✅ - $COUNT neue Artikel"
fi

# Telegram
curl -s -X POST "https://api.telegram.org/bot$TELEGRAM_BOT_TOKEN/sendMessage" \
    -d "chat_id=$CHAT_ID" -d "text=$MSG" -d "parse_mode=Markdown" > /dev/null 2>&1

echo "$(date): $MSG" >> "$LOGFILE"
