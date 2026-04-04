#!/usr/bin/env python3
"""Content Tracker - Check for new articles about tracked games/films"""
import requests
from bs4 import BeautifulSoup
import psycopg2
import os
from datetime import datetime, timedelta

DB_CONFIG = {'host': 'localhost', 'database': 'demo_scraper', 'user': 'scraper', }

SOURCES = [
    {'name': 'IGN', 'url': 'https://www.ign.com/articles', 'search': 'https://www.ign.com/search?q={query}', 'article_selector': 'searchResult'},
    {'name': 'Eurogamer', 'url': 'https://www.eurogamer.de', 'search': 'https://www.eurogamer.de/search?q={query}', 'article_selector': 'search-results__item'},
    {'name': 'GameStar', 'url': 'https://www.gamestar.de', 'search': 'https://www.gamestar.de/suche/?q={query}', 'article_selector': 'searchResults'},
    {'name': 'Rock Paper Shotgun', 'url': 'https://www.rockpapershotgun.com', 'search': 'https://www.rockpapershotgun.com/search?q={query}', 'article_selector': 'article'},
]

def get_db_connection():
    return psycopg2.connect(**DB_CONFIG)

def get_tracked_items():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, title, type, last_checked FROM content_tracker")
    items = cur.fetchall()
    cur.close()
    conn.close()
    return items

def search_articles(query, source):
    """Search for articles about a game/film"""
    articles = []
    try:
        search_url = source['search'].format(query=query)
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.37'}
        resp = requests.get(search_url, headers=headers, timeout=15)
        soup = BeautifulSoup(resp.text, 'html.parser')
        
        # Find all article-like elements
        for article in soup.find_all(['article', 'div'], class_=lambda x: x and ('article' in str(x).lower() or 'result' in str(x).lower() or 'card' in str(x).lower()) if x else False):
            link = article.find('a', href=True)
            if link:
                href = link.get('href', '')
                text = link.get_text(strip=True)
                if text and len(text) > 15:
                    full_url = href if href.startswith('http') else source['url'] + href
                    articles.append({
                        'title': text[:200],
                        'url': full_url,
                        'source': source['name']
                    })
        
        # Fallback: any link with query in it
        if not articles:
            for link in soup.find_all('a', href=True):
                href = link.get('href', '')
                text = link.get_text(strip=True)
                if query.lower() in text.lower() or query.lower() in href.lower():
                    if len(text) > 20:
                        full_url = href if href.startswith('http') else source['url'] + href
                        articles.append({
                            'title': text[:200],
                            'url': full_url,
                            'source': source['name']
                        })
    except Exception as e:
        print(f"  ⚠️ Error searching {source['name']}: {e}")
    return articles[:5]

def save_article(title, url, source, tracked_id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO news_articles (title, url, source_name, category, fetched_at)
        VALUES (%s, %s, %s, 'content-update', NOW())
        ON CONFLICT (url) DO NOTHING
    """, (title, url, source))
    conn.commit()
    cur.close()
    conn.close()

def update_last_checked(tracked_id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("UPDATE content_tracker SET last_checked = NOW() WHERE id = %s", (tracked_id,))
    conn.commit()
    cur.close()
    conn.close()

def main():
    print(f"🔍 Content Tracker - {datetime.now()}")
    items = get_tracked_items()
    print(f"📋 Checking {len(items)} tracked items...")
    
    for item_id, title, item_type, last_checked in items:
        print(f"\n🎮 Checking: {title}")
        for source in SOURCES:
            articles = search_articles(title, source)
            for article in articles:
                print(f"  📰 {article['title'][:50]}... ({article['source']})")
                save_article(article['title'], article['url'], article['source'], item_id)
        update_last_checked(item_id)
    
    print("\n✅ Content check complete!")

if __name__ == '__main__':
    main()
