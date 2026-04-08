#!/usr/bin/env python3
"""
Demo Scout NRW - AfD/Antifa Event Scout
Erweitert: Nur AfD-relevante Events im Nahbereich
"""

import os
import re
import sys
import json
import time
import urllib.request
import urllib.parse
from datetime import datetime, date, timedelta
from typing import Optional, List, Dict

# === KONFIGFIGURATION ===
DB_CONFIG = {
    "host": "localhost",
    "database": "demo_scraper",
    "user": "scraper",}

# Telegram Config
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = "737961726"

def send_telegram(message: str) -> bool:
    """Send message via Telegram Bot API"""
    if not TELEGRAM_TOKEN:
        print("⚠️ TELEGRAM_BOT_TOKEN nicht gesetzt")
        return False
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        data = urllib.parse.urlencode({
            "chat_id": TELEGRAM_CHAT_ID,
            "text": message,
            "parse_mode": "Markdown"
        }).encode()
        req = urllib.request.Request(url, data=data, method='POST')
        urllib.request.urlopen(req, timeout=10)
        return True
    except Exception as e:
        print(f"❌ Telegram send failed: {e}")
        return False

def save_to_db(events: List[Dict]) -> int:
    """Save events to demo_events table"""
    try:
        import psycopg2
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()
        saved = 0
        for e in events:
            cur.execute("""
                INSERT INTO demo_events (title, date, time, region, source, category, url, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, NOW())
                ON CONFLICT DO NOTHING
            """, (e['title'], e.get('date'), e.get('time'), e['region'], 'demo_scout_afd', 'AfD', e.get('url', '')))
            saved += cur.rowcount
        conn.commit()
        cur.close()
        conn.close()
        return saved
    except Exception as e:
        print(f"❌ DB save failed: {e}")
        return 0

# Regionen im Nahbereich (Köln + 80km)
REGIONS = {
    "Köln": {"lat": 50.9375, "lon": 6.9603},
    "Düsseldorf": {"lat": 51.2277, "lon": 6.7735},
    "Bonn": {"lat": 50.7374, "lon": 7.0982},
    "Leverkusen": {"lat": 51.0465, "lon": 7.0192},
    "Neuss": {"lat": 51.1982, "lon": 6.6875},
    "Bergisch Gladbach": {"lat": 51.0999, "lon": 7.1480},
    "Gelsenkirchen": {"lat": 51.5177, "lon": 7.0857},
    "Oberhausen": {"lat": 51.4963, "lon": 6.8516},
    "Essen": {"lat": 51.4556, "lon": 7.0116},
}

# MUSS eines dieser Keywords enthalten
AFD_KEYWORDS = [
    "AfD", "Höcke", "Weidel", "Chrupalla", 
    "AfD-Stand", "Infostand AfD", "AfD Kundgebung",
    "AfD Parteitag", "AfD Bürgerdialog", "AfD-Veranstaltung"
]

# Region-Keywords
REGION_KEYWORDS = {
    "Köln": ["köln", "kölner", "cologne"],
    "Düsseldorf": ["düsseldorf", "düsseldorfer", "ddorf", "garath"],
    "Bonn": ["bonn"],
    "Leverkusen": ["leverkusen"],
    "Neuss": ["neuss"],
    "Bergisch Gladbach": ["bergisch gladbach"],
    "Gelsenkirchen": ["gelsenkirchen"],
    "Oberhausen": ["oberhausen"],
    "Essen": ["essen"],
}

import math
def calculate_distance(lat1, lon1, lat2, lon2):
    R = 6371
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon/2)**2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))

def detect_region(text: str) -> tuple[str, int]:
    text_lower = text.lower()
    koln_lat, koln_lon = REGIONS["Köln"]["lat"], REGIONS["Köln"]["lon"]
    
    for region, info in REGIONS.items():
        for keyword in REGION_KEYWORDS.get(region, []):
            if keyword in text_lower:
                km = calculate_distance(koln_lat, koln_lon, info["lat"], info["lon"])
                if km <= 80:
                    return region, int(km)
    return "Unbekannt", 999

def is_afd_relevant(text: str) -> bool:
    text_upper = text.upper()
    for kw in AFD_KEYWORDS:
        if kw.upper() in text_upper:
            return True
    return False

def extract_date_time(text: str) -> tuple[Optional[str], Optional[str]]:
    text_lower = text.lower()
    today = date.today()
    
    # Time
    time_match = re.search(r'(\d{1,2}):(\d{2})\s*Uhr', text)
    if not time_match:
        time_match = re.search(r'um\s*(\d{1,2}):(\d{2})', text)
    time_str = f"{time_match.group(1).zfill(2)}:{time_match.group(2)}" if time_match else None
    
    # Date
    date_str = None
    if "heute" in text_lower:
        date_str = str(today)
    elif "morgen" in text_lower:
        date_str = str(today + timedelta(days=1))
    else:
        for pattern, parser in [
            (r'(\d{1,2})\.(\d{1,2})\.(\d{4})', lambda m: f"{m.group(3)}-{m.group(2).zfill(2)}-{m.group(1).zfill(2)}"),
            (r'(\d{1,2})\.(\d{1,2})\.(\d{2})\b', lambda m: f"20{m.group(3)}-{m.group(2).zfill(2)}-{m.group(1).zfill(2)}"),
        ]:
            match = re.search(pattern, text)
            if match:
                try:
                    date_str = parser(match)
                    break
                except:
                    pass
    
    return date_str, time_str

def search_web(query: str, max_results: int = 10) -> List[Dict]:
    results = []
    try:
        url = f"https://duckduckgo.com/html/?q={urllib.parse.quote(query)}"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=10) as response:
            html = response.read().decode('utf-8', errors='ignore')
            titles = re.findall(r'class="result__a"[^>]*>([^<]+)<', html)
            urls = re.findall(r'class="result__a"[^>]*href="([^"]*)"', html)
            for title, url in zip(titles[:max_results], urls[:max_results]):
                results.append({'title': title.strip()[:200], 'url': url.strip()[:200]})
    except Exception as e:
        print(f"Search error: {e}")
    return results

def main():
    print("=== Demo Scout NRW - AfD Focus ===")
    print(f"Zeit: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Such-Queries - NUR AfD
    queries = [
        "AfD Kundgebung Düsseldorf Köln 2026",
        "AfD Infostand NRW 2026",
        "AfD Veranstaltung Bonn Leverkusen 2026",
        "AfD Stand Köln Demonstration 2026",
    ]
    
    all_events = []
    
    for query in queries:
        print(f"\n🔍 Suche: {query}")
        results = search_web(query, max_results=5)
        
        for r in results:
            title = r.get('title', '')
            
            # Filter: AfD-Keyword muss enthalten sein
            if not is_afd_relevant(title):
                continue
            
            # Filter: Region muss im 80km-Radius sein
            region, km = detect_region(title)
            if km > 80:
                continue
            
            # Datum + Uhrzeit
            event_date, event_time = extract_date_time(title)
            
            all_events.append({
                'title': title[:100],
                'date': event_date,
                'time': event_time,
                'region': region,
                'km': km,
                'url': r.get('url', '')[:200],
            })
    
    # Deduplicate
    seen = set()
    unique_events = []
    for e in all_events:
        key = (e['title'][:50], e.get('date'))
        if key not in seen:
            seen.add(key)
            unique_events.append(e)
    
    # Sort
    unique_events.sort(key=lambda x: (x.get('date') or '9999', x.get('km', 999)))
    
    print(f"\n📊 {len(unique_events)} relevante AfD-Events gefunden")
    
    for e in unique_events[:5]:
        print(f"  📍 {e['region']} ({e['km']}km) | {e.get('date', 'N/A')} | {e['title'][:50]}")
    
    if not unique_events:
        print("\n  Keine AfD-Events im Nahbereich gefunden.")
    
    # Telegram message - NUR wenn Events gefunden!
    if unique_events:
        message = "🕵️ **Demo Scout AfD**\n\n"
        for i, e in enumerate(unique_events[:3], 1):
            message += f"{i}. **{e['title'][:50]}**\n"
            message += f"   📍 {e['region']} ({e['km']}km) | {e.get('date', 'N/A')}\n\n"
        
        # Save to DB
        saved = save_to_db(unique_events)
        if saved > 0:
            message += f"💾 {saved} Event(s) in DB gespeichert."
        
        # Send to Telegram
        print(f"\n📱 Sende Telegram-Nachricht...")
        if send_telegram(message):
            print("✅ Telegram-Nachricht gesendet!")
        else:
            print("❌ Telegram-Nachricht fehlgeschlagen")
    else:
        print("\n🤫 Keine Events - keine Nachricht (kein Spam)")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
