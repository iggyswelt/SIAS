#!/usr/bin/env python3
"""Learn Cycle - Autonomous learning (optimized)"""
import subprocess
from datetime import datetime

def run_sql(sql):
    """Run SQL via subprocess (peer auth works)"""
    result = subprocess.run(
        ['sudo', '-u', 'postgres', 'psql', '-d', 'demo_scraper', '-t', '-A', '-c', sql],
        capture_output=True, text=True
    )
    return result.stdout.strip() if result.returncode == 0 else None

def add_learning(topic, content):
    """Add learning ONLY if it doesn't already exist with same title+content"""
    # Check if last learning with same title has same content
    check_sql = f"SELECT content FROM learnings WHERE title = 'learn_cycle: {topic}' ORDER BY created_at DESC LIMIT 1"
    last_content = run_sql(check_sql)
    
    if last_content == content:
        print(f"  ⏭ Skipping duplicate: {topic} = '{content}'")
        return False
    
    insert_sql = f"INSERT INTO learnings (type, title, area, priority, status, trigger_text, content, action, created_at) VALUES ('LRN', 'learn_cycle: {topic}', 'system', 'medium', 'active', 'auto-generated', '{content}', 'auto-learned', NOW())"
    run_sql(insert_sql)
    return True

if __name__ == "__main__":
    print(f"Learn Cycle - {datetime.now()}")
    
    # Check learning queue
    queue = run_sql("SELECT COUNT(*) FROM learning_queue WHERE status='pending'")
    print(f"Pending topics: {queue}")
    
    # Check total learnings
    learnings = run_sql("SELECT COUNT(*) FROM learnings")
    print(f"Total learnings: {learnings}")
    
    # Add system health learning ONLY if changed
    secrets = run_sql("SELECT COUNT(*) FROM secrets")
    if secrets:
        added = add_learning('vault', f'Vault stable: {secrets} secrets')
        if added:
            print(f"✅ Added NEW learning: Vault has {secrets} secrets")
        else:
            print(f"  ⏭ Vault status unchanged ({secrets} secrets)")
    
    print("Learn Cycle completed")
