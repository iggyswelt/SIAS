#!/bin/bash
# Athene stündlicher Trading-Check
LOG="/opt/dashboard/logs/athene_hourly.log"
mkdir -p /opt/dashboard/logs

echo "$(date): Athene hourly check starting" >> $LOG

# Offene Trades holen
OPEN=$(curl -s -u iggy:metamaus2026! http://localhost:8080/api/v1/status)
echo "$(date): Open trades: $OPEN" >> $LOG

# Profit-Stand holen  
PROFIT=$(curl -s -u iggy:metamaus2026! http://localhost:8080/api/v1/profit)
echo "$(date): Profit: $PROFIT" >> $LOG

# In PostgreSQL speichern (via ~/.pgpass)
PGHOST=localhost psql -U scraper -d demo_scraper -c "
INSERT INTO athene_memory (key, value) VALUES ('last_hourly_check', '$(date -Iseconds)') ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value;
INSERT INTO athene_memory (key, value) VALUES ('last_profit_snapshot', '$PROFIT') ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value;
" 2>> $LOG

echo "$(date): Athene hourly check done" >> $LOG
