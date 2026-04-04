#!/usr/bin/env python3
"""Sync OpenClaw Gateway tokens to token_usage_history"""
import json
import subprocess
from datetime import datetime

def run_sql(sql):
    result = subprocess.run(
        ['sudo', '-u', 'postgres', 'psql', '-d', 'demo_scraper', '-t', '-A', '-c', sql],
        capture_output=True, text=True
    )
    return result.stdout.strip() if result.returncode == 0 else None

def sync_openclaw_tokens():
    print(f"🔄 Syncing OpenClaw tokens - {datetime.now()}")
    
    sessions_path = "/home/iggy/.openclaw/agents/main/sessions/sessions.json"
    
    try:
        with open(sessions_path) as f:
            data = json.load(f)
    except Exception as e:
        print(f"  ⚠️ Error reading sessions: {e}")
        return
    
    total_tokens = 0
    model_counts = {}
    session_count = 0
    
    # Process all sessions
    for key, session in data.items():
        tokens = session.get('totalTokens', 0)
        if tokens and isinstance(tokens, int):
            total_tokens += tokens
            
            model = session.get('model', 'unknown')
            if model not in model_counts:
                model_counts[model] = {'tokens': 0, 'sessions': 0}
            model_counts[model]['tokens'] += tokens
            model_counts[model]['sessions'] += 1
            session_count += 1
    
    print(f"  📊 {session_count} sessions, {total_tokens} total tokens")
    
    # Save per model
    for model, data in model_counts.items():
        sql = f"""
            INSERT INTO token_usage_history (timestamp, model_name, tokens_total, session_count, details)
            VALUES (NOW(), '{model}', {data['tokens']}, {data['sessions']}, '{{"source": "openclaw_gateway"}}')
        """
        run_sql(sql)
        print(f"  ✅ {model}: {data['tokens']} tokens ({data['sessions']} sessions)")
    
    # Overall
    overall_sql = f"""
        INSERT INTO token_usage_history (timestamp, agent_name, tokens_total, session_count, details)
        VALUES (NOW(), 'overall', {total_tokens}, {session_count}, '{{"source": "openclaw_gateway"}}')
    """
    run_sql(overall_sql)
    print(f"  ✅ Total: {total_tokens} tokens")
    
    # Summary
    today = run_sql("""
        SELECT COUNT(*), COALESCE(SUM(tokens_total),0) 
        FROM token_usage_history 
        WHERE timestamp::date = CURRENT_DATE 
        AND agent_name = 'overall'
    """)
    if today and '|' in today:
        count, total = today.split('|')
        print(f"  📊 Today: {count} snapshots, {total} total tokens")

if __name__ == "__main__":
    sync_openclaw_tokens()
