#!/bin/bash
# GitHub Backup Script für systemd

source /home/iggy/.openclaw/.env
CHAT_ID="[TELEGRAM_ID]"

send_telegram() {
    if [[ -n "$TOKEN" ]]; then
        curl -s -X POST "https://api.telegram.org/bot${TOKEN}/sendMessage" \
            -d chat_id="$CHAT_ID" \
            -d text="$1" > /dev/null
    fi
}

exec >> /home/iggy/.openclaw/logs/github-backup.log 2>&1

echo "=== GitHub Backup gestartet: $(date) ==="

cd "$HOME/.openclaw/workspace"
git add -A
git commit -m "Backup $(date +%Y-%m-%d\ %H:%M)"

GIT_SSH_COMMAND="ssh -i $HOME/.openclaw/ssh/metamaus-backup-2026" git push origin master

if [[ $? -eq 0 ]]; then
    RESULT="✅ GitHub Backup erfolgreich - $(date +%H:%M)"
    echo "$RESULT"
    send_telegram "$RESULT"
else
    RESULT="❌ GitHub Backup fehlgeschlagen - $(date +%H:%M)"
    echo "$RESULT"
    send_telegram "$RESULT"
fi
