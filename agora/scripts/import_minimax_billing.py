#!/usr/bin/env python3
"""Import MiniMax Billing CSV into token_usage_history"""
import csv
import subprocess
from datetime import datetime

def run_sql(sql):
    result = subprocess.run(
        ['sudo', '-u', 'postgres', 'psql', '-d', 'demo_scraper', '-t', '-A', '-c', sql],
        capture_output=True, text=True
    )
    return result.stdout.strip() if result.returncode == 0 else None

def parse_time(time_str):
    """Parse '2026-03-01 23:00-24:00' to datetime"""
    try:
        # Format: "2026-03-01 23:00-24:00" -> start of hour
        date_part = time_str.split(' ')[0]
        hour_part = time_str.split(' ')[1].split('-')[0]
        return f"{date_part} {hour_part}:00"
    except:
        return None

def import_csv(csv_path):
    print(f"📥 Importing {csv_path}...")
    
    imported = 0
    skipped = 0
    
    with open(csv_path, 'r') as f:
        reader = csv.DictReader(f)
        
        for row in reader:
            # Skip non-token rows (like subscriptions)
            if row.get('Total usage quantity') in ['', '<nil>', '0']:
                skipped += 1
                continue
            
            model = row.get('Consumed model', '').strip()
            api_type = row.get('Consumed API', '').strip()
            time_str = row.get('Consumption time(UTC)', '').strip()
            
            try:
                input_qty = int(row.get('Input usage quantity', 0) or 0)
                output_qty = int(row.get('Output usage quantity', 0) or 0)
                total_qty = int(row.get('Total usage quantity', 0) or 0)
            except:
                skipped += 1
                continue
            
            timestamp = parse_time(time_str)
            if not timestamp:
                skipped += 1
                continue
            
            # Determine if cache or chat
            is_cache = 'cache' in api_type.lower()
            
            sql = f"""
                INSERT INTO token_usage_history (timestamp, model_name, tokens_in, tokens_out, tokens_total, session_count, details)
                VALUES ('{timestamp}', '{model}', {input_qty}, {output_qty}, {total_qty}, 1, '{{"api_type": "{api_type}", "is_cache": {str(is_cache).lower()}}}')
            """
            run_sql(sql)
            imported += 1
    
    print(f"✅ Imported: {imported} rows")
    print(f"⏭ Skipped: {skipped} rows")
    return imported

if __name__ == "__main__":
    import sys
    csv_path = sys.argv[1] if len(sys.argv) > 1 else "/tmp/minimax_billing.csv"
    import_csv(csv_path)
    
    # Show summary
    print("\n📊 Summary by Model:")
    result = run_sql("""
        SELECT model_name, 
               SUM(tokens_in) as input_tokens, 
               SUM(tokens_out) as output_tokens, 
               SUM(tokens_total) as total_tokens,
               COUNT(*) as hours
        FROM token_usage_history 
        WHERE timestamp > '2026-02-18'
        GROUP BY model_name 
        ORDER BY total_tokens DESC
    """)
    if result:
        print("Model              Input       Output      Total       Hours")
        print("-" * 60)
        for line in result.split('\n'):
            if '|' in line:
                parts = [p.strip() for p in line.split('|')]
                if len(parts) >= 5:
                    print(f"{parts[0]:18} {parts[1]:>10} {parts[2]:>10} {parts[3]:>12} {parts[4]:>6}")
