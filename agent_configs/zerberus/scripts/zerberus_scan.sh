#!/bin/bash
# Zerberus Network Scanner - LAN Asset Inventory
# Scan only [LOCAL_SUBNET] - Internal LAN only!

# Memory in DB, nicht als File!
# Logs → security_logs Tabelle

SUBNET="[LOCAL_SUBNET]"
DB_USER="scraper"
DB_NAME="metamaus"

SCAN_START=$(date '+%Y-%m-%d %H:%M:%S')

# Phase 1: Host Discovery (ping only, quiet)
echo "Phase 1: Host Discovery..."
HOSTS=$(nmap -sn -T2 --host-timeout 30s "$SUBNET" 2>/dev/null | grep "Nmap scan report for" | awk '{print $5}')

# Phase 2: Port Scan (top 100 ports, slow)
echo "Phase 2: Port Scan..."
SCAN_RESULTS=""
for IP in $HOSTS; do
    echo "Scanning $IP..."
    PORTS=$(nmap -sV -T2 -F --open --host-timeout 60s "$IP" 2>/dev/null | grep -E "^[0-9]+/tcp|^Service|^OS" | head -5)
    SCAN_RESULTS="${SCAN_RESULTS}${IP}: ${PORTS}\n"
done

SCAN_END=$(date '+%Y-%m-%d %H:%M:%S')

# In DB speichern
psql -U "$DB_USER" -d "$DB_NAME" -c "
INSERT INTO security_logs (event_type, message, severity, scan_details, created_at)
VALUES ('network_scan', 'Zerberus LAN Scan complete', 'info', E'\$SCAN_RESULTS', NOW());
" 2>/dev/null

# In DB speichern: network_assets Tabelle
echo "$HOSTS" | while read -r IP; do
    if [ -n "$IP" ]; then
        psql -U "$DB_USER" -d "$DB_NAME" -c "
INSERT INTO network_assets (ip_address, hostname, status, last_seen, created_at)
VALUES ('$IP', 'unknown', 'online', NOW(), NOW())
ON CONFLICT (ip_address) DO UPDATE SET
    status = 'online',
    last_seen = NOW(),
    updated_at = NOW();
" 2>/dev/null
    fi
done

echo "Scan complete - saved to DB (security_logs + network_assets)"
