#!/usr/bin/env python3
"""
Telegram Kanal Scraper für @demotermine
- Nutzt Web-Suche um aktuelle Posts zu finden
- Extrahiert Datum, Uhrzeit, Ort, Region
- Speichert in demo_events Tabelle
"""

import os
import re
import sys
import json
import time
import urllib.request
import urllib.parse
from datetime import datetime, date, timedelta
from typing import Optional

# === KONFIGURATION ===
DB_CONFIG = {
    "host": "localhost",
    "database": "demo_scraper",
    "user": "scraper",
    
}

# === REGION MAPPING ===
REGION_KEYWORDS = {
    "Köln": ["köln", "kölner", "cologne", "dom", "rheinland", "deutz", "ehrenfeld", "nippes"],
    "Düsseldorf": ["düsseldorf", "düsseldorfer", "ddorf", "dus", "garath", "benrath", "unterbach"],
    "Bonn": ["bonn", "bad godesberg", "beuel"],
    "Ruhrpott": ["essen", "dortmund", "bochum", "duisburg", "gelsenkirchen", "oberhausen", "dinslaken"],
    "Berlin": ["berlin", "bebelplatz", "brandenburger tor", "kreuzberg", "neukölln"],
    "Sachsen": ["dresden", "leipzig", "chemnitz", "görlitz", "zwickau"],
    "NRW": ["nrw", "nordrhein", "westfalen", "wuppertal", "bielefeld", "münster", "aachen", "krefeld"],
}

# === DATUM PARSING ===
MONTH_MAP = {
    "januar": "01", "februar": "02", "märz": "03", "april": "04",
    "mai": "05", "juni": "06", "juli": "07", "august": "08",
    "september": "09", "oktober": "10", "november": "11", "dezember": "12"
}

WEEKDAY_MAP = {
    "montag": 0, "dienstag": 1, "mittwoch": 2, "donnerstag": 3,
    "freitag": 4, "samstag": 5, "sonntag": 6
}

def parse_german_date(text: str) -> Optional[str]:
    """Extrahiert Datum aus Text"""
    text = text.lower()
    today = date.today()
    
    # Heute/Morgen
    if "heute" in text:
        return str(today)
    if "morgen" in text:
        return str(today + timedelta(days=1))
    if "übermorgen" in text:
        return str(today + timedelta(days=2))
    
    # Wochentage
    for day_name, weekday in WEEKDAY_MAP.items():
        if day_name in text:
            days_ahead = weekday - today.weekday()
            if days_ahead <= 0:
                days_ahead += 7
            return str(today + timedelta(days=days_ahead))
    
    # Datum-Formate
    patterns = [
        (r'(\d{1,2})\.(\d{1,2})\.(\d{4})', lambda m: f"{m.group(3)}-{m.group(2).zfill(2)}-{m.group(1).zfill(2)}"),
        (r'(\d{1,2})\.(\d{1,2})\.(\d{2})\b', lambda m: f"20{m.group(3)}-{m.group(2).zfill(2)}-{m.group(1).zfill(2)}"),
    ]
    
    for pattern, parser in patterns:
        match = re.search(pattern, text)
        if match:
            try:
                result = parser(match)
                d = datetime.strptime(result, "%Y-%m-%d").date()
                if d >= today - timedelta(days=7) and d <= today + timedelta(days=365):
                    return result
            except:
                pass
    
    return None

def extract_time(text: str) -> Optional[str]:
    """Extrahiert Uhrzeit"""
    patterns = [
        r'(\d{1,2}):(\d{2})\s*Uhr',
        r'um\s*(\d{1,2}):(\d{2})',
        r'beginn[:\s]*(\d{1,2}):(\d{2})',
    ]
    for pattern in patterns:
        match = re.search(pattern, text.lower())
        if match:
            return f"{match.group(1).zfill(2)}:{match.group(2)}"
    return None

def detect_region(text: str) -> tuple[str, str]:
    """Erkennt Region aus Text"""
    text_lower = text.lower()
    
    for region, keywords in REGION_KEYWORDS.items():
        for keyword in keywords:
            if keyword in text_lower:
                return region, "high"
    
    return "Unbekannt", "low"

# === WEB SEARCH ===
def search_demotermine():
    """Sucht nach aktuellen Demo-Terminen via Web"""
    results = []
    
    # Search queries
    queries = [
        "site:t.me/demotermine demo",
        "site:t.me/demotermine Demonstration",
        "site:t.me/demotermine Kundgebung",
    ]
    
    for query in queries:
        try:
            url = f"https://duckduckgo.com/html/?q={urllib.parse.quote(query)}"
            req = urllib.request.Request(url, headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            })
            with urllib.request.urlopen(req, timeout=10) as response:
                html = response.read().decode('utf-8', errors='ignore')
                
                # Find Telegram links
                links = re.findall(r't\.me/Demotermine/(\d+)', html)
                results.extend(links)
        except Exception as e:
            print(f"Search error: {e}")
    
    return list(set(results))[:20]  # Unique, max 20

def fetch_telegram_post(message_id: str):
    """Holt einzelne Telegram-Post"""
    url = f"https://t.me/Demotermine/{message_id}"
    try:
        req = urllib.request.Request(url, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        with urllib.request.urlopen(req, timeout=10) as response:
            html = response.read().decode('utf-8', errors='ignore')
            
            # Extract text
            text_match = re.search(r'<meta property="og:description" content="([^"]*)"', html)
            if text_match:
                text = text_match.group(1)
                return text[:1000]  # Limit
    except:
        pass
    return None

# === DATABASE ===
def save_to_db(events: list):
    """Speichert Events in DB"""
    try:
        import psycopg2
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()
        
        saved = 0
        for event in events:
            cur.execute("SELECT id FROM demos WHERE url = %s", (event['url'],))
            if cur.fetchone():
                continue
            
            cur.execute("""
                INSERT INTO demos (title, event_date, event_time, location, source, url, region, verified)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (url) DO NOTHING
            """, (
                event['title'],
                event.get('date'),
                event.get('time'),
                event.get('location'),
                event.get('source'),
                event.get('url'),
                event.get('region'),
                event.get('confidence') == 'high'
            ))
            if cur.rowcount:
                saved += 1
        
        conn.commit()
        cur.close()
        conn.close()
        return saved
    except Exception as e:
        print(f"DB Error: {e}")
        return 0

# === MAIN ===
def main():
    print("=== Telegram Kanal Scraper: @demotermine (via Web-Suche) ===")
    print(f"Zeit: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Search for posts
    print("\n🔍 Suche nach Posts...")
    post_ids = search_demotermine()
    print(f"   {len(post_ids)} Posts gefunden")
    
    events = []
    for msg_id in post_ids[:15]:
        text = fetch_telegram_post(msg_id)
        if not text or len(text) < 30:
            continue
        
        # Extract info
        event_date = parse_german_date(text)
        event_time = extract_time(text)
        region, confidence = detect_region(text)
        
        # Title from first line
        title = text.split('\n')[0][:100]
        
        events.append({
            'title': title,
            'date': event_date,
            'time': event_time,
            'location': None,
            'source': '@Demotermine',
            'url': f'https://t.me/Demotermine/{msg_id}',
            'region': region,
            'confidence': confidence,
            'raw': text[:300]
        })
    
    # Show results
    print(f"\n📊 {len(events)} Events extrahiert")
    
    # By region
    regions = {}
    for e in events:
        r = e['region']
        regions[r] = regions.get(r, 0) + 1
    
    print("\nNach Region:")
    for r, c in sorted(regions.items(), key=lambda x: -x[1]):
        print(f"  {r}: {c}")
    
    # Sample events
    print("\n=== Events (Datum + Region) ===")
    for e in events[:8]:
        print(f"  {e.get('date', 'N/A'):12} {e.get('time', ''):5} [{e['region']:12}] {e['title'][:40]}")
    
    # Save
    print("\n💾 Speichere in DB...")
    saved = save_to_db(events)
    print(f"   {saved} neue Events gespeichert")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
