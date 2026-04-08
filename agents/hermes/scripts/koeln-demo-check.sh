#!/bin/bash
# Köln Demo Check Script für systemd

source /home/iggy/.openclaw/.env
CHAT_ID="[TELEGRAM_ID]"

send_telegram() {
    if [[ -n "$TOKEN" ]]; then
        curl -s -X POST "https://api.telegram.org/bot${TOKEN}/sendMessage" \
            -d chat_id="$CHAT_ID" \
            -d text="$1" > /dev/null
    fi
}

exec >> /home/iggy/.openclaw/logs/koeln-demo-check.log 2>&1

echo "=== Köln Demo Check gestartet: $(date) ==="

# Placeholder für die eigentliche Demo-Suche
RESULT_TEXT="📍 Heute Köln – Demos & Aktionen: Check erfolgt"

echo "$RESULT_TEXT"
send_telegram "$RESULT_TEXT"
