#!/usr/bin/env python3
"""
Demo Calendar Scraper - Prototype
Scrapt plotter.infoladen.de (einfachste Quelle)
"""

import requests
from bs4 import BeautifulSoup
from datetime import datetime
# import psycopg2  # TODO: Install
import json


def scrape_plotter():
    """Scrape plotter.infoladen.de/upcoming"""
    url = "https://plotter.infoladen.de/upcoming"
    response = requests.get(url)
    soup = BeautifulSoup(response.content, 'html.parser')
    
    events = []
    for row in soup.select('.views-row'):
        title = row.select_one('.views-field-title')
        date = row.select_one('time')
        location = row.select_one('.views-field-field-ort-in-datenbank')
        
        if title and date:
            events.append({
                'title': title.get_text(strip=True),
                'date': date.get('datetime'),
                'location': location.get_text(strip=True) if location else 'Köln',
                'url': url,
                'source': 'plotter.infoladen.de'
            })
    
    return events


# def save_to_db(events):
#     """Save to PostgreSQL"""
#     conn = psycopg2.connect(
#         dbname='openclaw_demos',
#         user='openclaw',
#         password='AUS_VAULT_HOLEN',  # TODO: Vault integration
#         host='localhost'
#     )
#     cur = conn.cursor()
#     
#     for event in events:
#         cur.execute("""
#             INSERT INTO demos.events (title, event_date, location, url, source_id)
#             VALUES (%s, %s, %s, %s, 1)
#             ON CONFLICT DO NOTHING
#         """, (event['title'], event['date'], event['location'], event['url']))
#     
#     conn.commit()
#     conn.close()


if __name__ == '__main__':
    events = scrape_plotter()
    print(f"Found {len(events)} events")
    
    for e in events[:3]:
        print(f" - {e['title']} ({e['date']})")
    
    # save_to_db(events)  # Uncomment when DB ready
