#!/usr/bin/env python3
"""
Rheingold Activity Logger
Automatisch Activities in rheingold_activity_log schreiben
"""

import psycopg2
import os
import sys
from datetime import datetime

DB_CONFIG = {
    'dbname': os.getenv('DB_NAME', 'metamaus'),
    'user': os.getenv('DB_USER', 'scraper'),
    'host': 'localhost'
}

def get_connection():
    return psycopg2.connect(**DB_CONFIG)

def log_activity(action_type, description, status='running', metadata=None):
    """Log activity to rheingold_activity_log"""
    try:
        conn = get_connection()
        cur = conn.cursor()
        
        import json
        cur.execute("""
            INSERT INTO rheingold_activity_log (action_type, description, status, metadata)
            VALUES (%s, %s, %s, %s)
        """, (action_type, description, status, json.dumps(metadata or {})))
        
        conn.commit()
        cur.close()
        conn.close()
        return True
    except Exception as e:
        print(f"ERROR logging activity: {e}")
        return False

def log_crawl_start(url):
    """Log that crawling has started"""
    return log_activity('crawl_start', f'🔍 Crawle: {url[:60]}...', 'running')

def log_crawl_done(url, findings_count):
    """Log that crawling is complete"""
    return log_activity('crawl_done', f'✅ Fertig: {url[:50]}... ({findings_count} Findings)', 'completed')

def log_finding_saved(empfaenger, betrag):
    """Log a new finding"""
    return log_activity('finding_saved', f'💾 Finding: {empfaenger[:40]} - {betrag}€', 'completed')

def log_error(url, error_msg):
    """Log an error"""
    return log_activity('error', f'❌ Error: {error_msg[:80]}', 'error')

def log_idle():
    """Log idle status"""
    return log_activity('idle', '😴 Idle - warte auf Tasks', 'idle')

def log_startup():
    """Log startup"""
    return log_activity('startup', '🚀 Rheingold gestartet', 'running')

# CLI mode for testing
if __name__ == '__main__':
    if len(sys.argv) > 1:
        action = sys.argv[1]
        desc = sys.argv[2] if len(sys.argv) > 2 else ''
        log_activity(action, desc)
        print(f"Logged: {action} - {desc}")
    else:
        # Test logging
        log_startup()
        print("Rheingold Activity Logger ready!")
        print("Usage: python rheingold_activity_logger.py <action> <description>")
        print("Actions: crawl_start, crawl_done, finding_saved, error, idle, startup")
