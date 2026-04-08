#!/bin/bash
# Demo-Scraper Script für systemd

TOKEN_FILE="$HOME/.config/openclaw/telegram-token"
CHAT_ID="[TELEGRAM_ID]"

send_telegram() {
    if [[ -f "$TOKEN_FILE" ]]; then
        TOKEN=$(cat "$TOKEN_FILE")
        curl -s -X POST "https://api.telegram.org/bot${TOKEN}/sendMessage" \
            -d chat_id="$CHAT_ID" \
            -d text="$1" > /dev/null
    fi
}

exec >> /home/iggy/.openclaw/logs/demo-scraper.log 2>&1

echo "=== Demo-Scraper gestartet: $(date) ==="

# Use Hermes V4 script
bash "$HOME/.openclaw/scripts/hermes_scrape_v4.sh"

if [[ $? -eq 0 ]]; then
    RESULT="✅ Demo-Scraper erfolgreich - $(date +%H:%M)"
    echo "$RESULT"
    send_telegram "$RESULT"
else
    RESULT="❌ Demo-Scraper fehlgeschlagen - $(date +%H:%M)"
    echo "$RESULT"
    send_telegram "$RESULT"
fi
