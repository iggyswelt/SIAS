#!/usr/bin/env python3
"""
Hermes News Scraper — SIAS V3
Fetches RSS feeds from news_sources table, inserts into news_articles.
Usage: python3 hermes_news_scrape.py
"""
import os
import sys
import json
import datetime
import feedparser
import hashlib
from urllib.parse import urlparse

DB_USER = os.getenv("DB_USER", "scraper")
DB_HOST = "127.0.0.1"
DB_NAME = "metamaus"

def run_sql(sql, params=None):
    import psycopg2
    conn = psycopg2.connect(host=DB_HOST, dbname=DB_NAME, user=DB_USER)
    cur = conn.cursor()
    if params:
        cur.execute(sql, params)
    else:
        cur.execute(sql)
    conn.commit()
    if cur.description:
        rows = cur.fetchall()
        colnames = [desc[0] for desc in cur.description]
        return rows, colnames
    return None, None

def get_sources():
    rows, cols = run_sql("SELECT id, name, url, category FROM news_sources ORDER BY id;")
    return rows, cols

def parse_feed(source_id, source_name, feed_url, category):
    """Fetch and parse RSS feed, return list of article dicts."""
    articles = []
    try:
        feed = feedparser.parse(feed_url, agent="SIAS-V3-Hermes/1.0")
        for entry in feed.entries[:30]:  # max 30 per source
            title = getattr(entry, 'title', '') or ''
            link = getattr(entry, 'link', '') or ''
            summary = getattr(entry, 'summary', '') or ''
            if hasattr(entry, 'content'):
                summary = entry.content[0].value if entry.content else summary
            published = None
            if getattr(entry, 'published_parsed', None):
                try:
                    published = datetime.datetime(*entry.published_parsed[:6])
                except Exception:
                    pass
            if not published and getattr(entry, 'updated_parsed', None):
                try:
                    published = datetime.datetime(*entry.updated_parsed[:6])
                except Exception:
                    pass
            if not title or not link:
                continue
            # Strip HTML tags from summary
            import re
            summary = re.sub(r'<[^>]+>', '', summary)
            summary = summary.strip()[:2000]
            articles.append({
                'title': title.strip()[:500],
                'url': link.strip(),
                'summary': summary,
                'published_at': published,
                'category': category,
                'source_id': source_id,
                'source_name': source_name,
            })
    except Exception as e:
        print(f"  [ERROR] {source_name}: {e}", file=sys.stderr)
    return articles

def upsert_article(article):
    """Insert article, skip if URL already exists."""
    sql = """
    INSERT INTO news_articles (source_id, title, url, summary, published_at, category, source_name, is_read, fetched_at)
    VALUES (%s, %s, %s, %s, %s, %s, %s, false, NOW())
    ON CONFLICT (url) DO UPDATE SET
        title = EXCLUDED.title,
        summary = EXCLUDED.summary,
        fetched_at = NOW()
    RETURNING id;
    """
    params = (
        article['source_id'],
        article['title'],
        article['url'],
        article['summary'],
        article['published_at'],
        article['category'],
        article['source_name'],
    )
    try:
        run_sql(sql, params)
        return True
    except Exception as e:
        print(f"  [DB ERROR] {article['title'][:50]}: {e}", file=sys.stderr)
        return False

def log_to_rheingold(key, data):
    """Write result to rheingold_findings."""
    sql = """
    INSERT INTO rheingold_findings (key, created_by, agent_id, finding_type, summary, details_json, created_at)
    VALUES (%s, %s, %s, %s, %s, %s, NOW())
    ON CONFLICT (key) DO UPDATE SET
        summary = EXCLUDED.summary,
        details_json = EXCLUDED.details_json,
        created_at = NOW();
    """
    import json
    params = (
        key,
        'hermes',
        'hermes',
        'system',
        data['summary'],
        json.dumps(data['details']),
    )
    try:
        run_sql(sql, params)
    except Exception as e:
        print(f"[RHEINGOLD LOG ERROR] {e}", file=sys.stderr)

def main():
    print("=== Hermes News Scraper — SIAS V3 ===")
    print(f"Started: {datetime.datetime.now().isoformat()}")
    
    sources, _ = get_sources()
    print(f"Sources found: {len(sources)}")
    
    total_new = 0
    total_errors = 0
    results = []
    
    for row in sources:
        source_id, source_name, feed_url, category = row
        print(f"\n[{source_id}] {source_name} ({category})")
        if not feed_url:
            print("  No URL, skipping.")
            continue
        
        articles = parse_feed(source_id, source_name, feed_url, category)
        print(f"  Parsed {len(articles)} articles")
        
        inserted = 0
        for article in articles:
            if upsert_article(article):
                inserted += 1
        print(f"  Inserted/Updated: {inserted}")
        total_new += inserted
        results.append({
            'source_id': source_id,
            'source_name': source_name,
            'category': category,
            'articles_parsed': len(articles),
            'articles_saved': inserted,
        })
    
    # Log to rheingold_findings
    summary = f"Hermes News Scrape {datetime.date.today().isoformat()}: {total_new} Artikel aus {len(sources)} Quellen"
    log_to_rheingold('news_refresh_20260406', {
        'summary': summary,
        'details': {
            'sources_count': len(sources),
            'total_articles': total_new,
            'scrape_time': datetime.datetime.now().isoformat(),
            'results': results,
        }
    })
    
    # Count in DB after scrape
    rows, _ = run_sql("SELECT COUNT(*) FROM news_articles;")
    db_count = rows[0][0] if rows else 0
    print(f"\n=== DONE ===")
    print(f"Total articles in DB: {db_count}")
    print(f"New/updated this run: {total_new}")
    print(f"Key logged: news_refresh_20260406")

if __name__ == '__main__':
    main()
