#!/bin/bash
# Hourly Status Report Script
# Sends status update every hour to Telegram

STATUS_FILE="/tmp/metamaus_status.log"
TOKEN_TRACKER="/tmp/token_usage.log"

echo "$(date '+%Y-%m-%d %H:%M') - Status Check" >> $STATUS_FILE

# Count current tasks
TASKS_ACTIVE=$(ps aux | grep -E "(python|docker|node)" | grep -v grep | wc -l)
CPU_LOAD=$(uptime | awk -F'load average:' '{print $2}' | cut -d',' -f1)
MEMORY=$(free -m | awk 'NR==2{printf "%.1f%%", $3*100/$2}')

# Generate status message
cat << EOF
📊 **Stunden-Status $(date '+%H:%M')**

🔄 **Aktive Tasks:** $TASKS_ACTIVE
💻 **CPU:** $CPU_LOAD
💾 **RAM:** $MEMORY

📋 **Pipeline:**
$(cat /home/iggy/.openclaw/pipeline/current_tasks.txt 2>/dev/null || echo "   (wird geladen...)")

💰 **Token-Estimate:** $(wc -l < $TOKEN_TRACKER 2>/dev/null || echo "0") calls seit Start
EOF