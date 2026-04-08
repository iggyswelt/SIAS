#!/usr/bin/env python3
import requests
import json
import psycopg2

TAVILY_KEY = "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"

def save_to_db(topic, content, source='athena_autonomous'):
    import psycopg2
    try:
        pg = psycopg2.connect("dbname=metamaus user=scraper host=localhost")
        cur = pg.cursor()
        cur.execute("""
            INSERT INTO athena_research 
            (topic, content, source, created_at)
            VALUES (%s, %s, %s, NOW())
            ON CONFLICT DO NOTHING
        """, (topic, str(content), source))
        pg.commit()
        pg.close()
        print(f"✅ DB: {topic} gespeichert")
        return True
    except Exception as e:
        print(f"❌ DB Error: {e} — kein JSON-Fallback!")
        return False

def search(q):
    r = requests.post("https://api.tavily.com/search", json={"api_key": TAVILY_KEY, "query": q, "max_results": 3}, timeout=30)
    return r.json()

for topic in ["DutchCryptoDad strategy", "crypto scalping indicators"]:
    print(f"ATHENA: {topic}")
    result = search(topic)
    if "results" in result:
        print(f"  -> {len(result['results'])} results")
    else:
        print(f"  -> Error: {result}")
