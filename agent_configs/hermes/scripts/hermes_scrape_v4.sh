#!/bin/bash
# Hermes V4 – Demo-Scraper Agent
# March 2026 Update - Priorisiert neue Quellen

set -e

LOGFILE="/home/iggy/.openclaw/logs/hermes_$(date +%Y%m%d).log"
echo "[$(date)] Hermes V4 starting..." >> "$LOGFILE"

# Load environment
source ~/.openclaw/.env 2>/dev/null || true

python3 << 'EOF' >> "$LOGFILE" 2>&1
import requests
from bs4 import BeautifulSoup
import psycopg2
import os
import json
import re
from datetime import datetime, timedelta

# Database connection
DB_CONFIG = {
    "dbname": os.getenv("DB_NAME", "metamaus"),
    "user": os.getenv("DB_USER", "scraper"),
    "host": "localhost"
}

def get_secret(key_name):
    """Get secret from Vault (PostgreSQL)"""
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()
    cur.execute("SELECT value_encrypted FROM secrets WHERE name = %s", (key_name,))
    row = cur.fetchone()
    cur.close()
    conn.close()
    if row:
        # For now return the encrypted blob - in production use proper decryption
        return row[0]
    return None

def is_likely_valid(event, bad_keywords=None):
    """Validation check for an event"""
    today = datetime.now().date()
    try:
        event_date = datetime.strptime(event['date'], "%Y-%m-%d").date()
    except:
        return None, "Invalid date format"
    
    # Older than 1 week → invalid
    if event_date < today - timedelta(days=7):
        return False, "Datum in Vergangenheit"
    
    # Manual label detection
    title_lower = event.get('title', '').lower()
    if "abgelaufen" in title_lower or "vorbei" in title_lower:
        return False, "Abgelaufen im Titel"
    
    # Bad keywords from feedback learning
    if bad_keywords:
        for kw in bad_keywords:
            if kw.lower() in title_lower:
                return False, f"Bad keyword: {kw}"
    
    # No URL → pending
    if not event.get('source_url'):
        return None, "Noch nicht geprüft"
    
    return None, "Wartet auf User-Feedback"

# Primary source 1: Friedenskooperative NRW
URL_FRIEDEN = "https://www.friedenskooperative.de/termine/text/bundesland/nordrhein-westfalen"

# Additional News Sources
NEWS_SOURCES = [
    "https://www.ksta.de/rss/koeln.xml",
    "https://www.express.de/xml/rss/koeln"
]

# === NEUE FRIEDENSKOOPERATIVE PARSING-FUNKTION ===
def parse_friedenskooperative():
    import requests
    from bs4 import BeautifulSoup
    import re
    
    url = "https://www.friedenskooperative.de/termine/text/bundesland/nordrhein-westfalen"
    response = requests.get(url, timeout=30, headers={
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    })
    soup = BeautifulSoup(response.text, 'html.parser')
    
    monate = {
        'januar': '01', 'februar': '02', 'märz': '03',
        'april': '04', 'mai': '05', 'juni': '06',
        'juli': '07', 'august': '08', 'september': '09',
        'oktober': '10', 'november': '11', 'dezember': '12'
    }
    
    events = []
    for div in soup.find_all('div', class_='text'):
        text = div.get_text(separator=' ').strip()
        text = re.sub(r'\s+', ' ', text)
        
        # Datum-Pattern: "10.03.2026" oder "10.03." oder "10. März"
        date = None
        
        # Pattern 1: DD.MM.YYYY
        m = re.search(r'(\d{1,2})\.(\d{2})\.2026', text)
        if m:
            date = f"2026-{m.group(2)}-{m.group(1).zfill(2)}"
        
        # Pattern 2: DD. Monatsname
        if not date:
            for monat, num in monate.items():
                m = re.search(rf'(\d{{1,2}})\.\s*{monat}', text.lower())
                if m:
                    date = f"2026-{num}-{m.group(1).zfill(2)}"
                    break
        
        # Auch wiederkehrende Events speichern
        recurring = bool(re.search(r'jeden\s+(Mo|Di|Mi|Do|Fr|Sa|So)', text))
        
        if date or recurring:
            # VA: extrahieren
            va_match = re.search(r'VA:\s*(.+?)(?:\||$)', text)
            organizer = va_match.group(1).strip() if va_match else ''
            
            events.append({
                'title': text[:120],
                'date': date or 'wiederkehrend',
                'organizer': organizer,
                'source': 'Friedenskooperative NRW',
                'url': url
            })
    
    return events

try:
    print("Fetching Friedenskooperative NRW...")
    
    # Use new parser
    friedens_events = parse_friedenskooperative()
    print(f"Testing new parser: Found {len(friedens_events)} raw events")
    
    # Convert to database format
    import re
    from datetime import datetime
    
    # Clean date parsing function
    def parse_date(title):
        import re
        from datetime import datetime
        
        # German month names
        month_map = {
            'januar': '01', 'februar': '02', 'märz': '03',
            'april': '04', 'mai': '05', 'juni': '06',
            'juli': '07', 'august': '08', 'september': '09',
            'oktober': '10', 'november': '11', 'dezember': '12'
        }
        
        # Range "24.-26. März" → nimm nur "24. März"
        title = re.sub(r'(\d+)\.\s*-\s*\d+\.\s*', r'\1. ', title)
        
        # Try to find DD. Monat or DD.MM.YYYY
        for monat, num in month_map.items():
            if monat in title.lower():
                day_match = re.search(r'(\d{1,2})\.', title)
                if day_match:
                    return f"2026-{num}-{day_match.group(1).zfill(2)}"
        
        # Try DD.MM.YYYY
        match = re.search(r'(\d{1,2})\.(\d{1,2})\.(\d{4})', title)
        if match:
            return f"{match.group(3)}-{match.group(2)}-{match.group(1).zfill(2)}"
        
        return None
    
    events = []
    
    for e in friedens_events:
        title = e.get('title', '')
        event_date = e.get('date', None)
        
        # Skip if no date and not recurring
        if event_date == 'wiederkehrend' or event_date:
            events.append({
                'title': title[:200],
                'date': event_date if event_date != 'wiederkehrend' else None,
                'location': e.get('organizer', ''),
                'organizer': e.get('organizer', ''),
                'source_url': e.get('url', ''),
                'source': 'Friedenskooperative NRW',
                'category': 'Frieden',
                'location_group': 'NRW',
                'recurring': event_date == 'wiederkehrend'
            })
    
    print(f"Found {len(events)} valid events from Friedenskooperative")
    
    # Load bad_keywords from database
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()
        cur.execute("SELECT jsonb_array_elements_text(value::jsonb) as keyword FROM hermes_memory WHERE key = 'bad_keywords'")
        bad_keywords = [row[0].lower() for row in cur.fetchall()]
        cur.close()
        conn.close()
        print(f"Loaded {len(bad_keywords)} bad_keywords from DB")
    except Exception as e:
        bad_keywords = []
        print(f"Warning: Could not load bad_keywords: {e}")
    
    # ===== MASTODON RSS SOURCE =====
    print("Fetching Mastodon social.cologne...")
    try:
        import feedparser
        mastodon_url = "https://social.cologne/@Demos_und_Termine.rss"
        feed = feedparser.parse(mastodon_url)
        
        mastodon_events = []
        for entry in feed.entries[:20]:  # Limit to 20 entries
            title = entry.get('title', '')
            link = entry.get('link', '')
            pub_date = entry.get('published', '')
            
            # Extract date from title or description
            import re
            # Pattern: "8 März" or "8. März" or "08.03.2026"
            date_match = re.search(r'(\d{1,2})\.?\s*(\w+)\s*(\d{4})?', str(entry.description))
            
            if date_match:
                day = date_match.group(1)
                month = date_match.group(2)
                year = date_match.group(3) or str(datetime.now().year)
                
                month_map = {'Januar': '01', 'Februar': '02', 'März': '03', 'April': '04', 
                            'Mai': '05', 'Juni': '06', 'Juli': '07', 'August': '08',
                            'September': '09', 'Oktober': '10', 'November': '11', 'Dezember': '12',
                            'Jan': '01', 'Feb': '02', 'Mar': '03', 'Apr': '04', 'May': '05', 'Jun': '06',
                            'Jul': '07', 'Aug': '08', 'Sep': '09', 'Oct': '10', 'Nov': '11', 'Dec': '12'}
                month_num = month_map.get(month, '01')
                event_date = f"{year}-{month_num}-{day.zfill(2)}"
            else:
                event_date = datetime.now().strftime("%Y-%m-%d")
            
            # Extract location from description
            location = "Köln"
            loc_match = re.search(r'(Köln|Bonn|Düsseldorf|Dortmund|Essen)[\s,]', str(entry.description))
            if loc_match:
                location = loc_match.group(1)
            
            # Determine category based on hashtags
            desc_lower = str(entry.description).lower()
            if any(w in desc_lower for w in ['afd', 'alternative', 'rechts']):
                category = 'AfD'
            elif any(w in desc_lower for w in ['antifa', 'antifaschist', 'gegen rechts']):
                category = 'Antifa'
            elif any(w in desc_lower for w in ['frieden', 'friedensdemo']):
                category = 'Frieden'
            else:
                category = 'Demo'
            
            mastodon_events.append({
                'date': event_date,
                'title': title[:200],
                'location': location,
                'category': category,
                'source': 'mastodon_koeln',
                'source_url': link,
                'location_group': 'Köln/Bonn'
            })
        
        print(f"  📋 Mastodon: {len(mastodon_events)} events parsed")
        
        # Insert into DB
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()
        
        for e in mastodon_events:
            valid, note = is_likely_valid(e, bad_keywords)
            cur.execute("""
                INSERT INTO demo_events (date, title, location, category, source, source_url, location_group, is_valid, validation_note, user_feedback, scraped_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
                ON CONFLICT (date, title) DO UPDATE SET
                    location = EXCLUDED.location,
                    category = EXCLUDED.category,
                    source = EXCLUDED.source,
                    source_url = EXCLUDED.source_url,
                    is_valid = EXCLUDED.is_valid,
                    validation_note = EXCLUDED.validation_note,
                    scraped_at = NOW()
            """, (e['date'], e['title'], e['location'], e['category'], e['source'], 
                  e['source_url'], e['location_group'], valid, note, 'pending'))
        
        conn.commit()
        cur.close()
        conn.close()
        print(f"  ✅ Mastodon: {len(mastodon_events)} saved to DB")
        
    except Exception as me:
        print(f"  ⚠️ Mastodon error: {me}")
    
    # ===== STADT KÖLN RSS =====
    print("Fetching Stadt Köln RSS...")
    try:
        import feedparser
        stadt_url = "https://www.stadt-koeln.de/externe-dienste/rss/verkehrskalender.xml"
        feed = feedparser.parse(stadt_url)
        
        stadt_events = []
        for entry in feed.entries[:15]:  # Limit to 15 entries
            title = entry.get('title', '')
            link = entry.get('link', '')
            desc = entry.get('description', '')
            
            # Check for demo-relevant keywords
            demo_keywords = ['versammlung', 'kundgebung', 'aufzug', 'demo', 'demonstration', 'protest', 'aktion', 'mahnwache']
            title_lower = title.lower()
            desc_lower = desc.lower()
            
            if any(kw in title_lower or kw in desc_lower for kw in demo_keywords):
                category = 'Demo'
            else:
                category = 'Sonstiges'  # Mostly traffic/events, not demos
            
            # Try to extract date
            import re
            # Look for date patterns in description
            date_match = re.search(r'(\d{1,2})\.\s*(\w+)\s*(\d{4})?', str(entry))
            if date_match:
                day = date_match.group(1)
                month = date_match.group(2)
                year = date_match.group(3) or str(datetime.now().year)
                month_map = {'Januar': '01', 'Februar': '02', 'März': '03', 'April': '04', 
                            'Mai': '05', 'Juni': '06', 'Juli': '07', 'August': '08',
                            'September': '09', 'Oktober': '10', 'November': '11', 'Dezember': '12'}
                month_num = month_map.get(month, str(datetime.now().month).zfill(2))
                event_date = f"{year}-{month_num}-{day.zfill(2)}"
            else:
                # Use current date for entries without clear date
                event_date = datetime.now().strftime("%Y-%m-%d")
            
            stadt_events.append({
                'date': event_date,
                'title': title[:200],
                'location': 'Köln',
                'category': category,
                'source': 'stadt_koeln_verkehr',
                'source_url': link,
                'location_group': 'Köln'
            })
        
        print(f"  📋 Stadt Köln: {len(stadt_events)} events parsed")
        
        # Insert into DB
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()
        
        for e in stadt_events:
            valid, note = is_likely_valid(e, bad_keywords)
            cur.execute("""
                INSERT INTO demo_events (date, title, location, category, source, source_url, location_group, is_valid, validation_note, user_feedback, scraped_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
                ON CONFLICT (date, title) DO UPDATE SET
                    category = EXCLUDED.category,
                    source = EXCLUDED.source,
                    is_valid = EXCLUDED.is_valid,
                    scraped_at = NOW()
            """, (e['date'], e['title'], e['location'], e['category'], e['source'], 
                  e['source_url'], e['location_group'], valid, note, 'pending'))
        
        conn.commit()
        cur.close()
        conn.close()
        print(f"  ✅ Stadt Köln: {len(stadt_events)} saved to DB")
        
    except Exception as stadt_err:
        print(f"  ⚠️ Stadt Köln error: {stadt_err}")
    
    # ===== KÖLN GEGEN RECHTS RSS =====
    print("Fetching Köln gegen Rechts RSS...")
    try:
        import feedparser
        kgr_url = "https://koelngegenrechts.org/feed/"
        feed = feedparser.parse(kgr_url)
        
        kgr_events = []
        for entry in feed.entries[:10]:  # Limit to 10 recent posts
            title = entry.get('title', '')
            link = entry.get('link', '')
            
            # Check for demo-relevant keywords in title
            demo_keywords = ['demo', 'kundgebung', 'versammlung', 'aktion', 'protest', 'mahnwache', 'aufruf', 'demo', 'parteitag']
            title_lower = title.lower()
            
            if any(kw in title_lower for kw in demo_keywords):
                category = 'Antifa'
            else:
                category = 'Antifa'  # All posts from this source are anti-fascist relevant
            
            # Parse date from entry
            pub_date = entry.get('published', '')
            from email.utils import parsedate_to_datetime
            try:
                event_date = parsedate_to_datetime(pub_date).strftime("%Y-%m-%d")
            except:
                event_date = datetime.now().strftime("%Y-%m-%d")
            
            kgr_events.append({
                'date': event_date,
                'title': title[:200],
                'location': 'Köln',
                'category': category,
                'source': 'koeln_gegen_rechts',
                'source_url': link,
                'location_group': 'Köln'
            })
        
        print(f"  📋 Köln gegen Rechts: {len(kgr_events)} events parsed")
        
        # Insert into DB
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()
        
        for e in kgr_events:
            valid, note = is_likely_valid(e, bad_keywords)
            cur.execute("""
                INSERT INTO demo_events (date, title, location, category, source, source_url, location_group, is_valid, validation_note, user_feedback, scraped_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
                ON CONFLICT (date, title) DO UPDATE SET
                    category = EXCLUDED.category,
                    source = EXCLUDED.source,
                    is_valid = EXCLUDED.is_valid,
                    scraped_at = NOW()
            """, (e['date'], e['title'], e['location'], e['category'], e['source'], 
                  e['source_url'], e['location_group'], valid, note, 'pending'))
        
        conn.commit()
        cur.close()
        conn.close()
        print(f"  ✅ Köln gegen Rechts: {len(kgr_events)} saved to DB")
        
    except Exception as kgr_err:
        print(f"  ⚠️ Köln gegen Rechts error: {kgr_err}")
    
    # ===== PALÄSTINA SOLIDARITÄT =====
    print("Fetching Palästina-Solidarität events...")
    try:
        import feedparser
        pala_url = "https://palaestina-solidaritaet.de/mein-kalender/"
        # Fetch via web_fetch style (direct HTTP)
        response = requests.get(pala_url, timeout=10)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        pala_events = []
        # Parse events from the page - look for date + title patterns
        # The page has a calendar structure with dates and event links
        
        # Find all event links (links with mc_id parameter)
        event_links = soup.find_all('a', href=lambda x: x and 'mc_id=' in x if x else False)
        
        seen_titles = set()
        for link in event_links[:20]:  # Limit to 20 recent
            href = link.get('href', '')
            title = link.get_text(strip=True)
            if not title or len(title) < 5:
                continue
            if title in seen_titles:
                continue
            seen_titles.add(title)
            
            # Extract city from title
            city_match = re.search(r'(Köln|Bonn|Düsseldorf|Dortmund|Essen|München|Bochum|Wuppertal|Aachen|Duisburg|Hamburg|Berlin|Frankfurt|Hannover|Stuttgart|Leipzig|Dresden|Bremen)', title, re.IGNORECASE)
            city = city_match.group(1) if city_match else 'NRW'
            
            # Extract date from surrounding context or use current date
            event_date = datetime.now().strftime("%Y-%m-%d")
            
            # Determine category
            cat = 'Demo'
            if 'mahnwache' in title.lower():
                cat = 'Frieden'
            elif 'kundgebung' in title.lower() or 'demo' in title.lower():
                cat = 'Demo'
            
            pala_events.append({
                'date': event_date,
                'title': title[:200],
                'location': city,
                'category': cat,
                'source': 'palaestina_solidaritaet',
                'source_url': href,
                'location_group': city
            })
        
        print(f"  📋 Palästina-Solidarität: {len(pala_events)} events parsed")
        
        # Insert into DB
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()
        
        for e in pala_events:
            valid, note = True, 'auto-validated'
            cur.execute("""
                INSERT INTO demo_events (date, title, location, category, source, source_url, location_group, is_valid, validation_note, user_feedback, scraped_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
                ON CONFLICT (date, title) DO UPDATE SET
                    source_url = EXCLUDED.source_url,
                    scraped_at = NOW()
            """, (e['date'], e['title'], e['location'], e['category'], e['source'],
                  e['source_url'], e['location_group'], valid, note, 'pending'))
        
        conn.commit()
        cur.close()
        conn.close()
        print(f"  ✅ Palästina-Solidarität: {len(pala_events)} saved to DB")
        
    except Exception as pala_err:
        print(f"  ⚠️ Palästina-Solidarität error: {pala_err}")
    
    # ===== AFD NRW EVENTS (via Firecrawl Search) =====
    print("Fetching AfD NRW events via Firecrawl search...")
    try:
        import feedparser
        import subprocess
        import json
        import re
        
        # Use Firecrawl search to find AfD events
        result = subprocess.run([
            'python3', '-c', '''
import subprocess
import json
import re
from datetime import datetime
import os

result = subprocess.run([
    "python3", "/home/iggy/.openclaw/skills/firecrawl-search-1.0.0/scripts/search.py",
    "AfD NRW Veranstaltung Termin März April 2026", "--limit", "15", "--json"
], capture_output=True, text=True, env={**os.environ, "FIRECRAWL_API_KEY": "fc-05f858c2093e4c739349ae601b9f2060"})

if result.returncode == 0:
    data = json.loads(result.stdout)
    events = []
    
    for item in data.get("data", []):
        title = item.get("title", "")
        url = item.get("url", "")
        desc = item.get("description", "")
        
        # Extract date
        date_match = re.search(r"(\\d{1,2})\\.?\\s*(\\w+)\\s*(\\d{4})?", title + " " + desc)
        if date_match:
            day = date_match.group(1)
            month = date_match.group(2)
            year = date_match.group(3) or "2026"
            month_map = {"Januar": "01", "Februar": "02", "März": "03", "April": "04", 
                        "Mai": "05", "Juni": "06", "Juli": "07", "August": "08",
                        "September": "09", "Oktober": "10", "November": "11", "Dezember": "12"}
            month_num = month_map.get(month, "03")
            event_date = f"{year}-{month_num}-{day.zfill(2)}"
        else:
            event_date = datetime.now().strftime("%Y-%m-%d")
        
        # Skip past events
        if event_date < datetime.now().strftime("%Y-%m-%d"):
            continue
        
        # Extract location
        location = "NRW"
        loc_match = re.search(r"(München|Köln|Düsseldorf|Dortmund|Essen|Bonn|Aachen|Bochum|Wuppertal|Mülheim|Marl)", title + " " + desc)
        if loc_match:
            location = loc_match.group(1)
        
        # Skip non-AfD content
        if any(x in title.lower() or x in desc.lower() for x in ["dgb", "demo", "protest", "mahnwache", "gegenrechts"]):
            category = "Antifa"
        else:
            category = "AfD"
        
        events.append({
            "date": event_date,
            "title": title[:200],
            "location": location,
            "category": category,
            "source": "afd_nrw_search",
            "source_url": url,
            "location_group": "NRW"
        })
    
    print(json.dumps(events))
else:
    print("[]")
'''
        ], capture_output=True, text=True)
        
        afd_events = []
        if result.stdout.strip():
            try:
                afd_events = json.loads(result.stdout)
            except:
                pass
        
        print(f"  📋 AfD NRW: {len(afd_events)} events parsed")
        
        # Insert into DB
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()
        
        for e in afd_events:
            valid, note = is_likely_valid(e, bad_keywords)
            cur.execute("""
                INSERT INTO demo_events (date, title, location, category, source, source_url, location_group, is_valid, validation_note, user_feedback, scraped_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
                ON CONFLICT (date, title) DO UPDATE SET
                    category = EXCLUDED.category,
                    source = EXCLUDED.source,
                    is_valid = EXCLUDED.is_valid,
                    scraped_at = NOW()
            """, (e['date'], e['title'], e['location'], e['category'], e['source'], 
                  e['source_url'], e['location_group'], valid, note, 'pending'))
        
        conn.commit()
        cur.close()
        conn.close()
        print(f"  ✅ AfD NRW: {len(afd_events)} saved to DB")
        
    except Exception as afd_err:
        print(f"  ⚠️ AfD NRW error: {afd_err}")
    
    # ===== MULTI-SEARCH FOR DEMOS =====
    print("Searching for demos via multi_search...")
    try:
        import sys
        sys.path.insert(0, '/home/iggy/.openclaw/workspace/tools')
        from multi_search import multi_search
        
        # Search for demo events
        demo_query = "Demos Kundgebungen Demonstrationen Köln Bonn Düsseldorf NRW März April 2026"
        result = multi_search(demo_query, min_quality=2)
        
        print(f"  📊 Multi-search: {result.get('total_results', 0)} results, confidence: {result.get('confidence', 'unknown')}")
        
        # Parse results and save to DB
        multi_events = []
        for r in result.get('results', [])[:10]:
            title = r.get('title', '')[:200]
            url = r.get('url', '')
            
            # Extract date if present
            date_match = re.search(r'(\d{1,2})\.?\s*(\w+)\s*(\d{4})?', title)
            if date_match:
                day = date_match.group(1)
                month = date_match.group(2)
                year = date_match.group(3) or '2026'
                month_map = {'Januar': '01', 'Februar': '02', 'März': '03', 'April': '04', 
                            'Mai': '05', 'Juni': '06', 'Juli': '07', 'August': '08',
                            'September': '09', 'Oktober': '10', 'November': '11', 'Dezember': '12',
                            'Mar': '03', 'Apr': '04', 'May': '05', 'Jun': '06'}
                month_num = month_map.get(month, '03')
                event_date = f"{year}-{month_num}-{day.zfill(2)}"
            else:
                event_date = datetime.now().strftime("%Y-%m-%d")
            
            # Determine category
            title_lower = title.lower()
            if any(w in title_lower for w in ['afd', 'alternative']):
                category = 'AfD'
            elif any(w in title_lower for w in ['antifa', 'gegen rechts', 'antisemit']):
                category = 'Antifa'
            elif any(w in title_lower for w in ['frieden', 'friedensdemo']):
                category = 'Frieden'
            else:
                category = 'Demo'
            
            # Extract location
            location = 'NRW'
            loc_match = re.search(r'(Köln|Bonn|Düsseldorf|Dortmund|Essen|München|Bochum|Wuppertal|Aachen)', title)
            if loc_match:
                location = loc_match.group(1)
            
            multi_events.append({
                'date': event_date,
                'title': title,
                'location': location,
                'category': category,
                'source': 'multi_search',
                'source_url': url,
                'location_group': location
            })
        
        if multi_events:
            conn = psycopg2.connect(**DB_CONFIG)
            cur = conn.cursor()
            
            for e in multi_events[:5]:  # Limit to 5 to avoid spam
                valid, note = True, 'auto-validated'
                cur.execute("""
                    INSERT INTO demo_events (date, title, location, category, source, source_url, location_group, is_valid, validation_note, scraped_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
                    ON CONFLICT (date, title) DO NOTHING
                """, (e['date'], e['title'], e['location'], e['category'], e['source'], 
                      e['source_url'], e['location_group'], valid, note))
            
            conn.commit()
            cur.close()
            conn.close()
            print(f"  ✅ Multi-search: {len(multi_events[:5])} events saved to DB")
        
    except Exception as mse:
        print(f"  ⚠️ Multi-search error: {mse}")
    
    # ===== END MULTI-SEARCH =====
    
    # ===== END AFD NRW =====
    
    # DB Insert
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()
    
    inserted = 0
    for e in events:
        valid, note = is_likely_valid(e, bad_keywords)
        cur.execute("""
            INSERT INTO demo_events (date, title, location, category, source, source_url, location_group, is_valid, validation_note, user_feedback, scraped_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
            ON CONFLICT (date, title) DO UPDATE SET
                location = EXCLUDED.location,
                category = EXCLUDED.category,
                source = EXCLUDED.source,
                source_url = EXCLUDED.source_url,
                location_group = EXCLUDED.location_group,
                is_valid = EXCLUDED.is_valid,
                validation_note = EXCLUDED.validation_note,
                scraped_at = NOW()
        """, (
            e['date'], e['title'], e['location'], e['category'], e['source'],
            e.get('source_url', URL_FRIEDEN), e['location_group'],
            valid, note, 'pending'
        ))
        inserted += 1
    
    # Auto-invalidate old events
    cur.execute("""
        UPDATE demo_events 
        SET is_valid = false, validation_note = 'Auto: abgelaufen erkannt', user_feedback = 'invalid'
        WHERE title ILIKE '%DemoAbgelaufen%' 
           OR date < CURRENT_DATE - INTERVAL '7 days'
           OR (is_valid IS NULL AND date < CURRENT_DATE - INTERVAL '3 days')
    """)
    
    conn.commit()
    cur.close()
    conn.close()
    
    print(f"✅ {inserted} events saved to DB")
    
    # Dashboard refresh (both tabs)
    try:
        requests.post("http://localhost:5000/api/demo/refresh", timeout=3)
        requests.post("http://localhost:5000/api/news_events/refresh", timeout=3)
        print("📊 Dashboard refreshed (Demo + News)")
    except:
        pass  # Ignore if endpoint doesn't exist
    
    # Log to agent_logs
    try:
        conn = psycopg2.connect(
            host="localhost",
            database="metamaus",
            user="scraper",
            password="[REDACTED]"
        )
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO agent_logs (agent, level, message)
            VALUES ('hermes', 'debug', %s)
        """, (f"Scrape-Run: {inserted} Events gespeichert. Zeit: {datetime.now().strftime('%H:%M')}",))
        conn.commit()
        cur.close()
        conn.close()
    except:
        pass  # Ignore if logging fails
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()

EOF

