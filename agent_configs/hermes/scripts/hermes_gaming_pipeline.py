#!/usr/bin/env python3
"""
Hermes Gaming News Pipeline — V1
Scrapes 5 gaming sources: KotakuInAction (web), ThatParkPlace, FandomPulse, IGN DE, Insider Gaming (RSS).
Inserts into news_articles table.
"""
import os
import sys
import re
import json
import datetime
import feedparser
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse, urljoin

DB_USER = os.getenv("DB_USER", "scraper")
DB_HOST = "127.0.0.1"
DB_NAME = "metamaus"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/12127.0.0.1 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
}

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

def strip_html(text):
    if not text:
        return ""
    text = re.sub(r'<[^>]+>', ' ', text)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()[:2000]

def parse_rss_feed(source_id, source_name, feed_url, category):
    """Parse RSS/Atom feed and return article dicts."""
    articles = []
    try:
        feed = feedparser.parse(feed_url, agent="SIAS-V3-Hermes/1.0")
        if feed.bozo and not feed.entries:
            print(f"  [WARN] Feed parse error: {feed.bozo_exception}", file=sys.stderr)
            return articles
        for entry in feed.entries[:50]:
            title = getattr(entry, 'title', '') or ''
            link = getattr(entry, 'link', '') or ''
            summary = getattr(entry, 'summary', '') or ''
            if hasattr(entry, 'content') and entry.content:
                summary = entry.content[0].value
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
            articles.append({
                'title': title.strip()[:500],
                'url': link.strip(),
                'summary': strip_html(summary),
                'published_at': published,
                'category': category,
                'source_id': source_id,
                'source_name': source_name,
            })
    except Exception as e:
        print(f"  [ERROR] RSS parse failed: {e}", file=sys.stderr)
    return articles

def scrape_kotakuinaction(source_id, source_name, category, max_pages=3):
    """Scrape KotakuInAction from old.reddit.com (simpler HTML)."""
    articles = []
    base_url = "https://old.reddit.com/r/KotakuInAction/"
    try:
        for page in range(max_pages):
            url = base_url if page == 0 else f"{base_url}?count={page * 25}&after={last_after}" if page > 0 else base_url
            if page > 0 and last_after:
                url = f"{base_url}?count={page * 25}&after={last_after}"
            resp = requests.get(url, headers=HEADERS, timeout=15)
            if resp.status_code != 200:
                print(f"  [WARN] Reddit page {page}: HTTP {resp.status_code}", file=sys.stderr)
                break
            soup = BeautifulSoup(resp.text, 'html.parser')
            
            # Find post links
            posts = soup.select('div#siteTable > div.thing.link')
            if not posts:
                print(f"  [WARN] No posts found on page {page}", file=sys.stderr)
                break
            
            last_after = None
            for post in posts:
                data = post.get('data-fullname', '')
                if data:
                    last_after = data
                
                # Title
                title_el = post.select_one('a.title')
                if not title_el:
                    continue
                title = title_el.get_text(strip=True)
                link = title_el.get('href', '')
                if link.startswith('/'):
                    link = f"https://www.reddit.com{link}"
                
                # Time
                time_el = post.select_one('time')
                published = None
                if time_el and time_el.get('datetime'):
                    try:
                        published = datetime.datetime.fromisoformat(time_el['datetime'].replace('Z', '+00:00')).replace(tzinfo=None)
                    except Exception:
                        pass
                
                # Score
                score_el = post.select_one('div.score.unvoted')
                score = score_el.get_text(strip=True) if score_el else ''
                
                # Comments link for self-posts summary
                comments_link = post.select_one('a.comments')
                comments_text = comments_link.get_text(strip=True) if comments_link else ''
                
                summary = f"Score: {score} | Comments: {comments_text}"
                
                # Tag/flair
                flair_el = post.select_one('span.linkflairlabel')
                if flair_el:
                    summary = f"[{flair_el.get_text(strip=True)}] {summary}"
                
                if title and link:
                    articles.append({
                        'title': title[:500],
                        'url': link,
                        'summary': summary[:2000],
                        'published_at': published,
                        'category': category,
                        'source_id': source_id,
                        'source_name': source_name,
                    })
            
            print(f"  Page {page+1}: {len(posts)} posts, last_after={last_after}")
    except Exception as e:
        print(f"  [ERROR] KotakuInAction scrape failed: {e}", file=sys.stderr)
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
        print(f"  [DB] {article['title'][:60]}: {e}", file=sys.stderr)
        return False

def main():
    print("=== Hermes Gaming News Pipeline V1 ===")
    print(f"Started: {datetime.datetime.now().isoformat()}")
    
    # Define our 5 gaming sources
    gaming_sources = [
        # (source_id, name, url, type, category)
        (18, 'KotakuInAction', 'https://old.reddit.com/r/KotakuInAction/', 'web', 'gaming'),
        (19, 'ThatParkPlace', 'https://thatparkplace.com/feed/', 'rss', 'gaming'),
        (20, 'FandomPulse', 'https://fandompulse.substack.com/feed', 'rss', 'gaming'),
        (21, 'IGN DE', 'https://de.ign.com/rss', 'rss', 'gaming'),
        (22, 'Insider Gaming', 'https://insider-gaming.com/feed/', 'rss', 'gaming'),
    ]
    
    total_new = 0
    results = []
    
    for source_id, name, url, stype, category in gaming_sources:
        print(f"\n[{source_id}] {name} ({stype})")
        articles = []
        
        if stype == 'rss':
            articles = parse_rss_feed(source_id, name, url, category)
        elif stype == 'web':
            if 'KotakuInAction' in name:
                articles = scrape_kotakuinaction(source_id, name, category, max_pages=3)
        
        print(f"  Parsed {len(articles)} articles")
        
        inserted = 0
        for article in articles:
            if upsert_article(article):
                inserted += 1
        print(f"  Inserted/Updated: {inserted}")
        total_new += inserted
        results.append({
            'source_id': source_id,
            'source_name': name,
            'type': stype,
            'articles_parsed': len(articles),
            'articles_saved': inserted,
        })
    
    # Log to rheingold_findings
    summary = f"Hermes Gaming Pipeline {datetime.date.today().isoformat()}: {total_new} articles from {len(gaming_sources)} gaming sources"
    key = f"gaming_pipeline_{datetime.date.today().isoformat()}"
    try:
        run_sql("""
        INSERT INTO rheingold_findings (finding_type, content, quelle, relevanz, created_at)
        VALUES (%s, %s, %s, %s, NOW());
        """, (
            'pipeline',
            summary,
            'hermes',
            json.dumps({
                'sources_count': len(gaming_sources),
                'total_articles': total_new,
                'scrape_time': datetime.datetime.now().isoformat(),
                'results': results,
            }),
        ))
    except Exception as e:
        print(f"[RHEINGOLD LOG ERROR] {e}", file=sys.stderr)
    
    # Final count
    rows, _ = run_sql("SELECT COUNT(*) FROM news_articles WHERE source_id IN (18,19,20,21,22);")
    gaming_count = rows[0][0] if rows else 0
    rows2, _ = run_sql("SELECT COUNT(*) FROM news_articles;")
    total_count = rows2[0][0] if rows2 else 0
    
    print(f"\n=== DONE ===")
    print(f"Gaming articles in DB: {gaming_count}")
    print(f"Total articles in DB: {total_count}")
    print(f"New/updated this run: {total_new}")
    print(f"Key logged: {key}")

if __name__ == '__main__':
    main()
