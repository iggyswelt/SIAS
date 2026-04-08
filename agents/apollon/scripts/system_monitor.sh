#!/bin/bash
# system_monitor.sh — Sammelt CPU/RAM/Load/Disk für metamaus
# Cron: */1 * * * * /home/iggy/.openclaw/scripts/system_monitor.sh

LOG_FILE="/home/iggy/.openclaw/logs/system_monitor.log"

# Load avg (last 1 min)
LOAD=$(cat /proc/loadavg | awk '{print $1}')

# CPU: % idle → 100-idle
CPU=$(top -bn1 | grep "Cpu(s)" | awk '{print $2}' | sed 's/%us,.*//')
if [ -z "$CPU" ]; then
    CPU=$(top -bn1 | grep "%Cpu" | awk '{print $2}' | sed 's/,.*//')
fi

# RAM: used/total %
MEM=$(free | grep Mem | awk '{printf "%.1f", $3/$2 * 100}')

# Disk: / usage %
DISK=$(df -h / | awk 'NR==2 {print $5}' | sed 's/%//')

# Hostname
HOST="metamaus"

# Insert
psql -h localhost -U scraper -d metamaus -t -c "
INSERT INTO system_metrics (host, cpu_percent, ram_percent, load_avg, disk_percent, timestamp)
VALUES ('$HOST', '$CPU', '$MEM', '$LOAD', '$DISK', NOW());
" >> "$LOG_FILE" 2>&1

echo "$(date '+%H:%M:%S') $HOST CPU=$CPU% RAM=$MEM% Load=$LOAD Disk=$DISK%" >> "$LOG_FILE"
