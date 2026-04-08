#!/usr/bin/env python3
"""Zerberus Network Scanner - Scan local network and save to DB"""
import subprocess
import psycopg2
import re
from datetime import datetime

DB_CONFIG = {'host': 'localhost', 'database': 'metamaus', 'user': 'scraper', }

def get_db_connection():
    return psycopg2.connect(**DB_CONFIG)

def scan_network():
    """Scan local network with nmap"""
    print(f"🔍 Starting network scan - {datetime.now()}")
    
    try:
        # Quick scan of local network
        result = subprocess.run(
            ['nmap', '-sn', '192.168.23.0/24', '-T2'],
            capture_output=True,
            text=True,
            timeout=120
        )
        
        found_devices = []
        current_ip = None
        
        for line in result.stdout.split('\n'):
            # Nmap report line
            if 'Nmap scan report for' in line:
                # Extract IP
                match = re.search(r'(\d+\.\d+\.\d+\.\d+)', line)
                if match:
                    current_ip = match.group(1)
                    hostname = None
                    
                    # Check for hostname in parentheses
                    host_match = re.search(r'\(([^)]+)\)', line)
                    if host_match:
                        hostname = host_match.group(1)
                    
                    if current_ip:
                        found_devices.append({'ip': current_ip, 'hostname': hostname or 'unknown'})
        
        return found_devices
        
    except Exception as e:
        print(f"❌ Scan error: {e}")
        return []

def save_to_db(devices):
    """Save devices to network_assets table"""
    conn = get_db_connection()
    cur = conn.cursor()
    
    saved = 0
    for dev in devices:
        try:
            # Check if exists
            cur.execute("SELECT id FROM network_assets WHERE ip = %s", (dev['ip'],))
            exists = cur.fetchone()
            
            if exists:
                # Update
                cur.execute("""
                    UPDATE network_assets 
                    SET hostname = %s, last_seen = NOW(), status = 'online'
                    WHERE ip = %s
                """, (dev['hostname'], dev['ip']))
            else:
                # Insert
                cur.execute("""
                    INSERT INTO network_assets (ip, hostname, status, first_seen, last_seen)
                    VALUES (%s, %s, 'online', NOW(), NOW())
                """, (dev['ip'], dev['hostname']))
                saved += 1
                
        except Exception as e:
            print(f"  ⚠️ Error saving {dev['ip']}: {e}")
    
    conn.commit()
    cur.close()
    conn.close()
    return saved

def main():
    print("=" * 50)
    print("ZERBERUS NETWORK SCAN")
    print("=" * 50)
    
    devices = scan_network()
    print(f"📡 Found {len(devices)} devices")
    
    for dev in devices:
        print(f"  • {dev['ip']} - {dev['hostname']}")
    
    if devices:
        saved = save_to_db(devices)
        print(f"✅ Saved {saved} new devices to DB")
    
    print("=" * 50)
    print("Scan complete!")

if __name__ == '__main__':
    main()
