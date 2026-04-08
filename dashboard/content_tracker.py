#!/usr/bin/env python3
"""Content Tracker - Check RSS feeds for tracked games/films"""
import feedparser
import subprocess
from datetime import datetime

def run_sql(sql):
    """Run SQL via subprocess (peer auth works)"""
    result = subprocess.run(
        ['sudo', '-u', 'postgres', 'psql', '-d', 'demo_scraper', '-t', '-A', '-c', sql],
        capture_output=True, text=True
    )
    return result.stdout.strip() if result.returncode == 0 else None

def get_tracked_items():
    """Get tracked items from DB"""
    result = run_sql("SELECT id, title, type FROM content_tracker")
    if not result:
        return []
    items = []
    for line in result.split('\n'):
        if '|' in line:
            parts = line.split('|')
            if len(parts) >= 3:
                items.append((parts[0].strip(), parts[1].strip(), parts[2].strip()))
    return items

def get_rss_feeds():
    """Get RSS feeds from DB"""
    result = run_sql("SELECT name, url FROM news_sources WHERE category='gaming' AND active=true")
    if not result:
        return []
    feeds = []
    for line in result.split('\n'):
        if '|' in line:
            parts = line.split('|')
            if len(parts) >= 2:
                feeds.append((parts[0].strip(), parts[1].strip()))
    return feeds

def search_in_feed(query, feed_url, source_name):
    """Search for articles about a game/film in RSS feed"""
    articles = []
    try:
        feed = feedparser.parse(feed_url)
        for entry in feed.entries[:20]:  # Check last 20 entries
            title = entry.get('title', '').lower()
            summary = entry.get('summary', '').lower()
            query_lower = query.lower()
            
            if query_lower in title or query_lower in summary:
                articles.append({
                    'title': entry.get('title', '')[:200],
                    'url': entry.get('link', ''),
                    'source': source_name,
                    'published': entry.get('published', '')
                })
    except Exception as e:
        print(f"  ⚠️ Error parsing {source_name}: {e}")
    return articles

def save_article(title, url, source, tracked_id):
    """Save article to DB"""
    sql = f"""
        INSERT INTO news_articles (title, url, source_name, category, fetched_at)
        VALUES ('{title.replace("'", "''")}', '{url}', '{source}', 'content-update', NOW())
        ON CONFLICT (url) DO NOTHING
    """
    run_sql(sql)

def update_last_checked(tracked_id):
    """Update last_checked timestamp"""
    sql = f"UPDATE content_tracker SET last_checked = NOW() WHERE id = {tracked_id}"
    run_sql(sql)

def main():
    print(f"🔍 Content Tracker RSS - {datetime.now()}")
    items = get_tracked_items()
    feeds = get_rss_feeds()
    print(f"📋 Checking {len(items)} tracked items in {len(feeds)} feeds...")
    
    total_found = 0
    
    for item_id, title, item_type in items:
        print(f"\n🎮 Checking: {title}")
        for feed_name, feed_url in feeds:
            articles = search_in_feed(title, feed_url, feed_name)
            for article in articles:
                print(f"  📰 {article['title'][:60]}... ({article['source']})")
                save_article(article['title'], article['url'], article['source'], item_id)
                total_found += 1
        update_last_checked(item_id)
    
    print(f"\n✅ Content check complete! Found {total_found} articles")

if __name__ == '__main__':
    main()
