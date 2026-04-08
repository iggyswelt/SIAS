#!/bin/bash
# zerberus_network_scan.sh - Aggressive Read-Only Network Scan (2026-02-26)

NETWORK="[LOCAL_SUBNET]"
DB="metamaus"
USER="scraper"

echo "=== Aggressive Network Scan $(date) ==="

# 1. Enhanced Ping-Scan with MAC, DNS, NetBIOS, mDNS
nmap -sn -T4 -PE -PP -PM --host-timeout 15s $NETWORK -oG - 2>/dev/null | grep "Up$" | while read line; do
    ip=$(echo "$line" | awk '{print $2}')
    
    # MAC Address
    mac=$(echo "$line" | grep -oE '([0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}' | head -1)
    [ -z "$mac" ] && mac=""
    
    # Hostname from various sources
    hostname=""
    
    # Try DNS reverse
    result=$(host "$ip" 2>/dev/null | awk '{print $NF}' | sed 's/\.$//')
    [ -n "$result" ] && [ "$result" != "3(NXDOMAIN)" ] && hostname="$result"
    
    # Try DNS search (abydon.hq)
    if [ -z "$hostname" ]; then
        result=$(host "$ip.abydon.hq" 2>/dev/null | awk '{print $NF}' | sed 's/\.$//')
        [ -n "$result" ] && [ "$result" != "3(NXDOMAIN)" ] && hostname="$result"
    fi
    
    # Device type guess
    device_type=""
    [[ "$hostname" == *"router"* ]] || [[ "$ip" == *".1" ]] || [[ "$ip" == *".2" ]] && device_type="router"
    [[ "$hostname" == *"workstation"* ]] || [[ "$hostname" == *"pc"* ]] || [[ "$hostname" == *"desktop"* ]] && device_type="pc"
    [[ "$hostname" == *"laptop"* ]] || [[ "$hostname" == *"notebook"* ]] && device_type="laptop"
    [[ "$hostname" == *"phone"* ]] || [[ "$hostname" == *"iphone"* ]] || [[ "$hostname" == *"android"* ]] || [[ "$hostname" == *"pixel"* ]] || [[ "$hostname" == *"oneplus"* ]] && device_type="mobile"
    [[ "$hostname" == *"server"* ]] || [[ "$ip" == *".170" ]] && device_type="server"
    [[ "$hostname" == *"kodi"* ]] || [[ "$hostname" == *"shield"* ]] && device_type="media"
    [[ "$hostname" == *"yamaha"* ]] && device_type="audio"
    [[ "$hostname" == *"switch"* ]] || [[ "$hostname" == *"tp-link"* ]] && device_type="switch"
    [[ "$hostname" == *"helium"* ]] || [[ "$hostname" == *"rak"* ]] && device_type="iot"
    
    # Save to DB
     PGHOST=localhost psql -U $USER -d $DB -c "
        INSERT INTO network_assets (ip, hostname, mac, device_type, status, last_seen, first_seen)
        VALUES ('$ip', '$hostname', '$mac', '$device_type', 'online', NOW(), NOW())
        ON CONFLICT (ip) DO UPDATE SET 
            hostname = COALESCE(NULLIF('$hostname', ''), hostname),
            mac = COALESCE(NULLIF('$mac', ''), mac),
            device_type = COALESCE(NULLIF('$device_type', ''), device_type),
            status = 'online',
            last_seen = NOW();
    " 2>/dev/null
    
    echo "✓ $ip → $hostname ($device_type) [$mac]"
done

# 2. Quick OS Detection
echo "=== OS Detection ==="
nmap -T4 -O --osscan-limit --host-timeout 15s $NETWORK -oG - 2>/dev/null | grep "OS:" | while read line; do
    ip=$(echo "$line" | awk '{print $2}')
    os=$(echo "$line" | grep -oP 'OS: \K[^;]+' | head -1)
    [ -n "$os" ] &&  PGHOST=localhost psql -U $USER -d $DB -c "UPDATE network_assets SET os_guess = LEFT('$os', 255) WHERE ip = '$ip';" 2>/dev/null
    echo "  → $ip: $os"
done

# 3. Port Scan (Top 100 + common)
echo "=== Port Scan ==="
nmap -T4 --top-ports 150 -sV --version-light --open -oG - $NETWORK 2>/dev/null | grep "Ports:" | while read line; do
    ip=$(echo "$line" | awk '{print $2}')
    ports=$(echo "$line" | grep -oP 'Ports: \K.*' | sed 's/ //g' | tr ',' ';')
    [ -n "$ports" ] &&  PGHOST=localhost psql -U $USER -d $DB -c "UPDATE network_assets SET open_ports = '$ports' WHERE ip = '$ip';" 2>/dev/null
    echo "  → $ip: $ports"
done

echo "=== Scan complete ==="
