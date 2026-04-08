#!/usr/bin/env python3
"""
Demo Scout NRW - AfD/Antifa Event Scout
Sucht nach relevanten Demo-Events im Nahbereich (Köln + 80km)
Trigger-Wörter: AfD, Höcke, Weidel, Antifa, Gegenprotest, etc.
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

# Regionen im Nahbereich (Köln + 80km)
REGIONS = {
    "Köln": {"lat": 50.9375, "lon": 6.9603, "max_km": 0},
    "Düsseldorf": {"lat": 51.2277, "lon": 6.7735, "max_km": 40},
    "Bonn": {"lat": 50.7374, "lon": 7.0982, "max_km": 60},
    "Leverkusen": {"lat": 51.0465, "lon": 7.0192, "max_km": 25},
    "Neuss": {"lat": 51.1982, "lon": 6.6875, "max_km": 45},
    "Bergisch Gladbach": {"lat": 51.0999, "lon": 7.1480, "max_km": 30},
    "Gelsenkirchen": {"lat": 51.5177, "lon": 7.0857, "max_km": 70},
    "Oberhausen": {"lat": 51.4963, "lon": 6.8516, "max_km": 60},
    "Essen": {"lat": 51.4556, "lon": 7.0116, "max_km": 55},
}

# Trigger-Wörter (muss mindestens eines vorkommen)
TRIGGER_WORDS = [
    "AfD", "Höcke", "Weidel", "Chrupalla", 
    "Antifa", "Gegenprotest", "Blockade", 
    "Störaktion", "Protest gegen AfD", "AfD-Stand", 
    "Infostand AfD", "AfD Kundgebung"
]

# Keywords die Region definieren
REGION_KEYWORDS = {
    "Köln": ["köln", "kölner", "cologne", "dom"],
    "Düsseldorf": ["düsseldorf", "düsseldorfer", "ddorf", "dus", "garath"],
    "Bonn": ["bonn", "bad godesberg"],
    "Leverkusen": ["leverkusen", "wiesdorf"],
    "Neuss": ["neuss"],
    "Bergisch Gladbach": ["bergisch gladbach", "pardorf"],
    "Gelsenkirchen": ["gelsenkirchen", "buer"],
    "Oberhausen": ["oberhausen", "osterfeld"],
    "Essen": ["essen", "frintrop", "borbeck", "katern"],
}

def calculate_distance(lat1, lon1, lat2, lon2):
    """Berechnet Entfernung in km (einfache Approximation)"""
    import math
    R = 6371  # Erdradius in km
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    return R * c

def detect_region(text: str) -> tuple[str, int]:
    """Erkennt Region und Entfernung zu Köln"""
    text_lower = text.lower()
    
    for region, info in REGIONS.items():
        for keyword in REGION_KEYWORDS.get(region, []):
            if keyword in text_lower:
                km = calculate_distance(
                    REGIONS["Köln"]["lat"], REGIONS["Köln"]["lon"],
                    info["lat"], info["lon"]
                )
                return region, int(km)
    
    return "Unbekannt", 999

def extract_date_time(text: str) -> tuple[Optional[str], Optional[str]]:
    """Extrahiert Datum und Uhrzeit"""
    text_lower = text.lower()
    today = date.today()
    
    # Uhrzeit
    time_match = re.search(r'(\d{1,2}):(\d{2})\s*Uhr', text)
    if not time_match:
        time_match = re.search(r'um\s*(\d{1,2}):(\d{2})', text)
    
    time_str = None
    if time_match:
        time_str = f"{time_match.group(1).zfill(2)}:{time_match.group(2)}"
    
    # Datum
    date_str = None
    
    # Heute/Morgen
    if "heute" in text_lower:
        date_str = str(today)
    elif "morgen" in text_lower:
        date_str = str(today + timedelta(days=1))
    
    # Wochentage
    weekdays = {"montag": 0, "dienstag": 1, "mittwoch": 2, "donnerstag": 3, 
                "freitag": 4, "samstag": 5, "sonntag": 6}
    for day, wd in weekdays.items():
        if day in text_lower:
            days_ahead = wd - today.weekday()
            if days_ahead <= 0:
                days_ahead += 7
            date_str = str(today + timedelta(days=days_ahead))
            break
    
    # Datum-Formate
    if not date_str:
        for pattern in [r'(\d{1,2})\.(\d{1,2})\.(\d{4})', r'(\d{1,2})\.(\d{1,2})\.(\d{2})\b']:
            match = re.search(pattern, text)
            if match:
                try:
                    d, m, y = match.groups()
                    if len(y) == 2:
                        y = "20" + y
                    date_str = f"{y}-{m.zfill(2)}-{d.zfill(2)}"
                    break
                except:
                    pass
    
    return date_str, time_str

def is_relevant(text: str) -> bool:
    """Prüft ob Event relevant ist (Trigger-Wörter)"""
    text_upper = text.upper()
    for word in TRIGGER_WORDS:
        if word.upper() in text_upper:
            return True
    return False

def search_web(query: str, max_results: int = 10) -> List[Dict]:
    """Web-Suche durchführen"""
    results = []
    try:
        url = f"https://duckduckgo.com/html/?q={urllib.parse.quote(query)}"
        req = urllib.request.Request(url, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        with urllib.request.urlopen(req, timeout=10) as response:
            html = response.read().decode('utf-8', errors='ignore')
            
            # Extract links
            links = re.findall(r't\.me/[^"\'>\s]+', html)
            links = list(set(links))[:max_results]
            
            # Extract titles
            titles = re.findall(r'><a[^>]*class="result__a"[^>]*href="([^"]*)"[^>]*>([^<]*)</a>', html)
            
            for link, title in titles[:max_results]:
                results.append({
                    'url': link[:200],
                    'title': title[:200].strip()
                })
    except Exception as e:
        print(f"Search error: {e}")
    
    return results

def main():
    print("=== Demo Scout NRW ===")
    print(f"Zeit: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Such-Queries
    queries = [
        "AfD Kundgebung Köln Düsseldorf Protest 2026",
        "Antifa Demo Köln 2026",
        "AfD Infostand NRW Protest",
        "Gegenprotest AfD Düsseldorf",
    ]
    
    all_events = []
    
    for query in queries:
        print(f"\n🔍 Suche: {query}")
        results = search_web(query, max_results=5)
        
        for r in results:
            title = r.get('title', '')
            if not is_relevant(title):
                continue
            
            # Region + Entfernung
            region, km = detect_region(title)
            if km > 80:  # Filter: max 80km
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
                'source': 'Web-Suche'
            })
    
    # Deduplicate
    seen = set()
    unique_events = []
    for e in all_events:
        key = (e['title'][:50], e.get('date'))
        if key not in seen:
            seen.add(key)
            unique_events.append(e)
    
    # Sort by date
    unique_events.sort(key=lambda x: (x.get('date') or '9999', x.get('km', 999)))
    
    # Output
    print(f"\n📊 {len(unique_events)} relevante Events gefunden")
    
    for e in unique_events[:5]:
        print(f"\n  📍 {e['region']} ({e['km']}km)")
        print(f"     {e.get('date', 'N/A')} {e.get('time', ''):5} | {e['title'][:50]}")
    
    if not unique_events:
        print("\n  Keine neuen relevanten Events gefunden.")
    
    # Generate Telegram message
    message = "🕵️ **Demo Scout NRW**\n\n"
    
    if unique_events:
        for i, e in enumerate(unique_events[:5], 1):
            date_str = e.get('date', 'N/A')
            time_str = e.get('time', '')
            message += f"{i}. **{e['title'][:50]}**\n"
            message += f"   📍 {e['region']} ({e['km']}km) | {date_str} {time_str}\n"
            message += f"   🔗 {e['url'][:50]}\n\n"
    else:
        message += "Keine neuen relevanten Events in den letzten 36h.\n"
    
    message += "\nSoll ich eines in demo_events eintragen? (ja/nein)"
    
    print(f"\n📱 Telegram-Nachricht:\n{message}")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
