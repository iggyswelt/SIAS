#!/usr/bin/env python3
"""Token Usage Snapshot Collector - runs periodically to track token usage"""
import subprocess
import json
from datetime import datetime
import os

def run_sql(sql):
    """Run SQL via subprocess (peer auth works)"""
    result = subprocess.run(
        ['sudo', '-u', 'postgres', 'psql', '-d', 'demo_scraper', '-t', '-A', '-c', sql],
        capture_output=True, text=True
    )
    return result.stdout.strip() if result.returncode == 0 else None

def get_gateway_status():
    """Fetch gateway status for token info"""
    result = subprocess.run(
        ['/usr/bin/openclaw', 'status', '--json'],
        capture_output=True, text=True, timeout=30
    )
    if result.returncode == 0:
        try:
            return json.loads(result.stdout)
        except Exception as e:
            print(f"  ⚠️ JSON parse error: {e}")
    return None

def get_current_reset_cycle():
    """Calculate current reset cycle (5-hour blocks since epoch)"""
    import time
    return int(time.time()) // (5 * 3600)

def main():
    print(f"Token Snapshot - {datetime.now()}")
    
    # Get gateway status
    status = get_gateway_status()
    if not status:
        print("  ⚠️ Could not fetch gateway status")
        return
    
    # Parse sessions for token usage - correct path
    sessions_data = status.get('sessions', {})
    sessions = sessions_data.get('recent', [])
    
    total_tokens = 0
    model_counts = {}
    session_count = 0
    
    for session in sessions:
        # Get total tokens - use totalTokens if available, else calculate
        tokens = session.get('totalTokens', 0)
        if tokens and isinstance(tokens, int):
            total_tokens += tokens
            
            model = session.get('model', 'unknown')
            if model not in model_counts:
                model_counts[model] = {'tokens': 0, 'sessions': 0}
            model_counts[model]['tokens'] += tokens
            model_counts[model]['sessions'] += 1
            session_count += 1
    
    # Get current cycle
    cycle = get_current_reset_cycle()
    
    print(f"  📊 Found {session_count} active sessions, {total_tokens} total tokens")
    
    # Save snapshot per model
    for model, data in model_counts.items():
        sql = f"""
            INSERT INTO token_usage_history (timestamp, model_name, tokens_total, reset_cycle, session_count)
            VALUES (NOW(), '{model}', {data['tokens']}, {cycle}, {data['sessions']})
        """
        run_sql(sql)
        print(f"  ✅ {model}: {data['tokens']} tokens ({data['sessions']} sessions)")
    
    # Overall summary
    overall_sql = f"""
        INSERT INTO token_usage_history (timestamp, agent_name, tokens_total, reset_cycle, session_count)
        VALUES (NOW(), 'overall', {total_tokens}, {cycle}, {session_count})
    """
    run_sql(overall_sql)
    print(f"  ✅ Total: {total_tokens} tokens across {session_count} sessions")
    
    # Print history summary
    today = run_sql("SELECT COUNT(*), COALESCE(SUM(tokens_total),0) FROM token_usage_history WHERE timestamp::date = CURRENT_DATE AND agent_name = 'overall'")
    if today and '|' in today:
        count, total = today.split('|')
        print(f"  📊 Today: {count} snapshots, {total} total tokens (overall)")

if __name__ == "__main__":
    main()
