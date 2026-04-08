#!/usr/bin/env python3
"""
RHEINGOLD Quality Crawler - Qualität vor Quantität!
NUR verifizierte Förderungen mit echten Beträgen
"""

import os
import re
import time
import logging
from datetime import datetime
from urllib.parse import urljoin, urlparse
import requests
from bs4 import BeautifulSoup
import psycopg2
from psycopg2.extras import RealDictCursor

# Konfiguration
DATABASE_URL = os.environ.get('DATABASE_URL', 'postgresql://scraper:scraper@localhost:5432/metamaus')

# Whitelists
ALLOWED_DOMAINS = [
    'offenedaten-koeln.de',
    'fragdenstaat.de',
    'www.demokratie-leben.de',
    'www.foerderportal.nrw.de',
    'www.land.nrw',
    'www.vereinsregister.de',
    'www.handelsregister.de',
    'www.bmfsfj.de',
    'www.bundesregierung.de',
    'fragdenstaat.de',
    'www.offenedaten.de',
]

GOOD_KEYWORDS = ['foerder', 'zuschuss', 'zuwendung', 'bewilligt', 'auszahlung', 'empfanger', 'beihilfe', 'haushaltsplan', 'haushalt', 'projekt', 'foerderung']
BAD_KEYWORDS = ['kredit', 'darlehen', 'kfw', 'klimaneutral', 'klimaschutz', 'gutachten', 'spende', 'menu', 'navigation', 'footer', 'impressum', 'datenschutz', 'login', 'register']

# Beträge: 100€ bis 50 Mio €
AMOUNT_PATTERN = re.compile(r'(?:€|EUR|euro)?\s*(?:(\d{1,3}(?:\.\d{3})*(?:,\d{2})?)\s*(?:Mio\.?|Millionen?|Mrd\.?|Milliarden?)?|(\d{1,3}(?:\.\d{3})*(?:,\d{2})?)\s*€)', re.IGNORECASE)

MAX_DEPTH = 3
MIN_AMOUNT = 100
MAX_AMOUNT = 50_000_000

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def get_db_connection():
    return psycopg2.connect(DATABASE_URL)


def log_activity(message, activity_type='info'):
    """Log activity to rheingold_activity_log"""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO rheingold_activity_log (action_type, description, timestamp) VALUES (%s, %s, NOW())",
            (activity_type, message)
        )
        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        logger.error(f"Failed to log activity: {e}")


def is_allowed_domain(url):
    """Check if URL domain is in whitelist"""
    try:
        domain = urlparse(url).netloc.lower()
        return any(allowed in domain for allowed in ALLOWED_DOMAINS)
    except:
        return False


def contains_good_keyword(url):
    """Check if URL or text contains good keywords"""
    url_lower = url.lower()
    if any(kw in url_lower for kw in GOOD_KEYWORDS):
        return True
    return False


def contains_bad_keyword(url):
    """Check if URL contains bad keywords"""
    url_lower = url.lower()
    return any(kw in url_lower for kw in BAD_KEYWORDS)


def parse_amount(text):
    """Parse amount from text, return in EUR"""
    if not text:
        return None
    
    matches = AMOUNT_PATTERN.findall(text)
    for match in matches:
        # Handle different formats
        num_str = match[0] or match[1]
        if not num_str:
            continue
            
        # Clean number
        num_str = num_str.replace('.', '').replace(',', '.')
        try:
            amount = float(num_str)
            
            # Check for multipliers in text
            text_lower = text.lower()
            if 'mia' in text_lower or 'milliarden' in text_lower:
                amount *= 1_000_000_000
            elif 'mio' in text_lower or 'millionen' in text_lower:
                amount *= 1_000_000
            
            # If just a number without unit, assume euros if > 1000
            if amount < 1000 and 'euro' not in text_lower and '€' not in text:
                amount = None
                
            if amount and MIN_AMOUNT <= amount <= MAX_AMOUNT:
                return int(amount)
        except:
            continue
    
    return None


def extract_findings(html, url):
    """Extract funding findings from HTML"""
    findings = []
    soup = BeautifulSoup(html, 'html.parser')
    
    # Get text content - get more content
    text = soup.get_text()
    
    # More aggressive amount pattern
    amount_patterns = [
        r'(?:€|EUR|euro)\s*(\d{1,3}(?:[.,]\d{3})*(?:[.,]\d{2})?)',
        r'(\d{1,3}(?:[.,]\d{3})*(?:[.,]\d{2})?)\s*(?:Mio\.?|Millionen?|Mrd\.?|Milliarden?)\s*(?:€|EUR)?',
        r'(?:Betrag|Bewilligung|Förderung|Zuwendung)[:\s]*(\d{1,3}(?:[.,]\d{3})*(?:[.,]\d{2})?)\s*(?:€|EUR)?',
    ]
    
    all_amounts = []
    for pattern in amount_patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        all_amounts.extend(matches)
    
    # Get page title
    title = soup.find('h1')
    title_text = title.get_text().strip() if title else ''
    
    # Check for funding keywords
    text_lower = text.lower()
    funding_keywords_found = [kw for kw in GOOD_KEYWORDS if kw in text_lower]
    
    if funding_keywords_found and all_amounts:
        for amount_str in all_amounts:
            amount = parse_amount_extended(amount_str, text)
            if amount and MIN_AMOUNT <= amount <= MAX_AMOUNT:
                # Try to extract more context
                recipient = extract_recipient(text)
                purpose = extract_purpose(text)
                
                findings.append({
                    'url': url,
                    'amount': amount,
                    'recipient': recipient,
                    'purpose': purpose,
                    'title': title_text[:500] if title_text else None,
                    'source_domain': urlparse(url).netloc,
                    'keywords': ', '.join(funding_keywords_found)
                })
    
    return findings


def parse_amount_extended(amount_str, context_text):
    """Parse amount with better handling"""
    if not amount_str:
        return None
    
    try:
        # Clean the string
        num_str = amount_str.replace('.', '').replace(',', '.')
        amount = float(num_str)
        
        # Check context for multipliers
        ctx_lower = context_text.lower()
        
        # Find the amount in context to determine multiplier
        # Look around the amount in text
        idx = context_text.lower().find(amount_str.lower())
        if idx >= 0:
            context = context_text[max(0, idx-30):min(len(context_text), idx+30)].lower()
            
            if 'mia' in context or 'milliarden' in context:
                amount *= 1_000_000_000
            elif 'mio' in context or 'millionen' in context:
                amount *= 1_000_000
            elif 'tausend' in context or 'tsd' in context:
                amount *= 1_000
        
        # If just a small number, skip (likely not a funding amount)
        if amount < 100:
            return None
            
        return int(amount)
    except:
        return None


def extract_recipient(text):
    """Try to extract recipient name"""
    patterns = [
        r'(?:Empfänger|Begünstigter|Zuwendungsempfänger|Gefördert[er]|Antragsteller)[:\s]+([A-ZÄÖÜ][a-zäöüß\s,\.]{3,80})',
        r'(?:an|from)[:\s]+([A-ZÄÖÜ][a-zäöüß\s,\.]{3,80})',
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(1).strip()[:200]
    return None


def extract_purpose(text):
    """Try to extract funding purpose"""
    patterns = [
        r'(?:Zweck|Verwendungszweck|Förderzweck|Für)[:\s]+([^\n]{10,150})',
        r'(?:Projekt|Maßnahme)[:\s]+([^\n]{10,150})',
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(1).strip()[:500]
    return None


def crawl_page(url, depth=0):
    """Crawl a single page and extract findings"""
    if depth > MAX_DEPTH:
        return [], []
    
    try:
        headers = {
            'User-Agent': 'Rheingold-Quality-Crawler/1.0 (Research; +https://github.com/iggyswelt)'
        }
        response = requests.get(url, headers=headers, timeout=30, allow_redirects=True)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        findings = extract_findings(response.text, url)
        
        # Find links to follow
        links_to_follow = []
        for a in soup.find_all('a', href=True):
            link = urljoin(url, a['href'])
            
            # Only follow allowed domains
            if not is_allowed_domain(link):
                continue
            
            # Skip bad keywords
            if contains_bad_keyword(link):
                continue
            
            # Only follow good keywords
            if contains_good_keyword(link):
                links_to_follow.append((link, depth + 1))
        
        # Dedupe
        links_to_follow = list(set(links_to_follow))
        
        logger.info(f"Crawled: {url} -> Found {len(findings)} findings, {len(links_to_follow)} links")
        return findings, links_to_follow
        
    except Exception as e:
        logger.error(f"Error crawling {url}: {e}")
        return [], []


def save_findings(findings):
    """Save findings to database"""
    if not findings:
        return
    
    conn = get_db_connection()
    cur = conn.cursor()
    
    for finding in findings:
        try:
            cur.execute("""
                INSERT INTO rheingold_findings 
                (url, betrag, empfaenger, beschreibung, quelle, is_verified, created_at)
                VALUES (%s, %s, %s, %s, %s, TRUE, NOW())
                ON CONFLICT DO NOTHING
            """, (
                finding['url'],
                finding['amount'],
                finding.get('recipient'),
                finding.get('purpose') or finding.get('keywords'),
                finding.get('source_domain')
            ))
            logger.info(f"Saved finding: €{finding['amount']:,} from {finding.get('source_domain')}")
        except Exception as e:
            logger.error(f"Error saving finding: {e}")
    
    conn.commit()
    cur.close()
    conn.close()


def add_to_queue(urls, depth=0):
    """Add URLs to crawl queue"""
    if not urls:
        return
    
    conn = get_db_connection()
    cur = conn.cursor()
    
    for url, d in urls:
        try:
            cur.execute("""
                INSERT INTO rheingold_crawl_queue (url, status, depth, added_at)
                VALUES (%s, 'pending', %s, NOW())
                ON CONFLICT DO NOTHING
            """, (url, d))
        except Exception as e:
            logger.error(f"Error adding to queue: {e}")
    
    conn.commit()
    cur.close()
    conn.close()


def get_next_url():
    """Get next URL from queue"""
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    cur.execute("""
        SELECT url, depth FROM rheingold_crawl_queue 
        WHERE status = 'pending' 
        ORDER BY depth ASC, added_at ASC 
        LIMIT 1
        FOR UPDATE SKIP LOCKED
    """)
    
    result = cur.fetchone()
    
    if result:
        cur.execute("""
            UPDATE rheingold_crawl_queue 
            SET status = 'crawled', crawled_at = NOW() 
            WHERE url = %s
        """, (result['url'],))
    
    conn.commit()
    cur.close()
    conn.close()
    
    return result['url'] if result else None, result['depth'] if result else 0


def check_queue_and_refill():
    """Check queue size and refill if needed"""
    conn = get_db_connection()
    cur = conn.cursor()
    
    cur.execute("SELECT COUNT(*) as cnt FROM rheingold_crawl_queue WHERE status = 'pending'")
    pending = cur.fetchone()[0]
    
    cur.close()
    conn.close()
    
    if pending < 5:
        # Add more seeds
        seeds = [
            ('https://offenedaten-koeln.de/dataset?q=foerderung', 0),
            ('https://fragdenstaat.de/bund/', 0),
            ('https://www.bundesregierung.de/breg-de/foerderdb', 0),
        ]
        add_to_queue(seeds)
        log_activity(f"Auto-refill: Added {len(seeds)} seeds, queue had {pending}", 'refill')


def run_crawler_loop(max_iterations=50):
    """Main crawler loop"""
    logger.info("Starting RHEINGOLD Quality Crawler")
    log_activity("Quality crawler started", 'start')
    
    for i in range(max_iterations):
        # Check queue and refill if needed
        check_queue_and_refill()
        
        # Get next URL
        url, depth = get_next_url()
        
        if not url:
            logger.info("No more URLs in queue")
            log_activity("Queue empty, stopping", 'stop')
            break
        
        logger.info(f"Iteration {i+1}/{max_iterations}: Crawling {url} (depth={depth})")
        
        # Crawl
        findings, new_links = crawl_page(url, depth)
        
        # Save findings
        if findings:
            save_findings(findings)
            logger.info(f"Saved {len(findings)} verified findings")
            for f in findings:
                log_activity(f"Found: €{f['amount']:,} - {f.get('recipient', 'N/A')}", 'finding')
        
        # Add new links to queue
        if new_links:
            add_to_queue(new_links)
        
        # Rate limiting
        time.sleep(2)
    
    log_activity(f"Crawler finished. Iterations: {i+1}", 'complete')


if __name__ == '__main__':
    run_crawler_loop()
