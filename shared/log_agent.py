#!/usr/bin/env python3
"""Zentrale Logging-Funktion für alle Agents"""
import psycopg2
from datetime import datetime
import os

DB_HOST = os.environ.get('DB_HOST', 'localhost')
DB_USER = os.environ.get('DB_USER', 'scraper')
DB_NAME = os.environ.get('DB_NAME', 'metamaus')

def get_db_pass():
    """Lese Passwort aus .env"""
    with open(os.path.expanduser('~/.openclaw/.env')) as f:
        for line in f:
            if line.startswith('DB_PASS='):
                return line.split('=', 1)[1].strip()

def log_agent(agent, level, message, details=None):
    """Zentrale Logging-Funktion für alle Agents"""
    try:
        conn = psycopg2.connect(
            host=DB_HOST,
            database=DB_NAME,
            user=DB_USER,
            password=get_db_pass()
        )
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO agent_logs (agent, level, message, details, timestamp)
            VALUES (%s, %s, %s, %s, %s)
        """, (agent, level, message, details, datetime.now()))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Log error: {e}")
        return False

if __name__ == '__main__':
    import sys
    if len(sys.argv) >= 4:
        agent = sys.argv[1]
        level = sys.argv[2]
        message = sys.argv[3]
        details = sys.argv[4] if len(sys.argv) > 4 else None
        log_agent(agent, level, message, details)
