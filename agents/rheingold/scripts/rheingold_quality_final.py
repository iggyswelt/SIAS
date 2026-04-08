#!/usr/bin/env python3
"""Rheingold QUALITY Crawler - nur echte Foerderungen"""
import requests, re, time, logging
from bs4 import BeautifulSoup
import psycopg2
from urllib.parse import urljoin, urlparse

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger(__name__)
DB = dict(database='metamaus', user='scraper', host='localhost')
ALLOWED = {'offenedaten-koeln.de','stadt-koeln.de','fragdenstaat.de','demokratie-leben.de',
            'foerderportal.nrw.de','land.nrw','vereinsregister.de',
            'handelsregister.de','bundestag.de','bundesregierung.de','bmfsfj.de','bmi.bund.de','oparl.org'}
GOOD_KW = ['foerder','zuschuss','zuwendung','bewilligt','auszahlung','empfanger','haushaltsplan','haushalt']
BAD_KW = ['kredit','darlehen','kfw','klimaneutral','klimaschutz','gutachten','spende',
           'menu','navigation','footer','kontakt','impressum']
MIN_AMT = 100
MAX_AMT = 50000000

def db():
    c = psycopg2.connect(**DB)
    return c

def log(type, msg):
    try:
        c = db()
        cur = c.cursor()
        cur.execute("INSERT INTO rheingold_activity_log (action_type, description, status) VALUES (%s,%s,'running')", (type, msg[:200]))
        c.commit()
        cur.close(); c.close()
    except: pass

def pending():
    c = db()
    cur = c.cursor()
    cur.execute("SELECT id,url,depth,parent_url FROM rheingold_crawl_queue WHERE status='pending' ORDER BY added_at LIMIT 5")
    rows = list(cur.fetchall())
    cur.close(); c.close()
    return rows

def mark(uid, status, fc=0):
    try:
        c = db()
        cur = c.cursor()
        cur.execute("UPDATE rheingold_crawl_queue SET status=%s,crawled_at=NOW(),findings_count=%s WHERE id=%s", (status, fc, uid))
        c.commit()
        cur.close(); c.close()
    except: pass

def save_f(f):
    amt = f.get('betrag', 0)
    ctx = (f.get('beschreibung','') + ' ' + f.get('quelle','')).lower()
    if any(b in ctx for b in BAD_KW): return 0
    if amt and (amt > MAX_AMT or amt < MIN_AMT): return 0
    if amt > 1000000 and not any(g in ctx for g in GOOD_KW): return 0
    if not any(g in ctx for g in GOOD_KW): return 0
    try:
        c = db()
        cur = c.cursor()
        cur.execute(
            "INSERT INTO rheingold_findings "
            "(quelle,beschreibung,empfaenger,betrag,kategorie,fokus,region,is_verified,created_at) "
            "VALUES (%s,%s,%s,%s,'foerderung','bund','bund',TRUE,NOW()) "
            "ON CONFLICT DO NOTHING",
            (f.get('quelle','')[:200], f.get('beschreibung','')[:500],
             f.get('empfaenger','')[:100], amt)
        c.commit(); cur.close(); conn.close()
        return 1
    except Exception as e:
        logger.error("save_f failed: %s", e)
        try: c.close()
        except: pass
        return 0

def qlinks(html, base):
    soup = BeautifulSoup(html, 'html.parser')
    found = []
    for a in soup.find_all('a', href=True):
        href = a['href']
        url = urljoin(base, href)
        parsed = urlparse(url)
        if parsed.netloc and parsed.netloc not in ALLOWED: continue
        lt = (a.get_text() + ' ' + href).lower()
        if any(b in lt for b in BAD_KW): continue
        if not any(g in lt for g in GOOD_KW): continue
        found.append(url)
    seen = {}
    for u in found: seen[u] = 1
    return list(seen)[:10]

def crawl_one(uid, url, depth=0):
    log('start', 'Crawle: ' + url[:50])
    hdrs = {'User-Agent': 'Mozilla/5.0 (compatible; RheingoldBot/1.0)'}
    try:
        r = requests.get(url, headers=hdrs, timeout=20)
        r.raise_for_status()
        html = r.text
        text = html.lower()
        if not any(g in text for g in GOOD_KW):
            mark(uid, 'crawled', 0)
            return 0
        soup = BeautifulSoup(html, 'html.parser')
        saved = 0
        # Extract amounts
        for m in re.findall(r'[\d.,]+\s*(?:Euro|EUR|Mio|EUR|eur)', html):
            try:
                raw = re.sub(r'[^\d.]', '', m.replace(',', '.'))
                amt = float(raw)
                if amt < MIN_AMT or amt > MAX_AMT: continue
                om = re.search(r'([A-Z][a-z]+(?: [A-Z][a-z]+)*?(?:gGmbH|e\.?V\.|Stiftung|Verband|Verein|Stiftung b\.?R\.)', html)
                org = om.group(1) if om else ''
                dm = re.search(r'[^.!?]{30,200}', html[:3000])
                desc = dm.group(0)[:200] if dm else url
                if save_f({'quelle': url[:200], 'beschreibung': desc, 'empfaenger': org, 'betrag': amt}):
                    saved += 1
            except: pass
        # Self-feeding
        if depth < 3:
            links = qlinks(html, url)
            if links:
                c = db()
                cur = c.cursor()
                for lnk in links:
                    cur.execute("INSERT INTO rheingold_crawl_queue (url,status,depth,parent_url,added_at) VALUES (%s,'pending',%s,%s,NOW()) ON CONFLICT DO NOTHING", (lnk, depth+1, url))
                c.commit()
                cur.close(); c.close()
        mark(uid, 'crawled', saved)
        log('done', 'Crawled: ' + url[:50] + ' (' + str(saved) + ' Finds)')
        return saved
    except Exception as e:
        logger.error('Error %s', e)
        mark(uid, 'failed', 0)
        return 0

def refill():
    c = db()
    cur = c.cursor()
    cur.execute("SELECT COUNT(*) FROM rheingold_crawl_queue WHERE status='pending'")
    cnt = cur.fetchone()[0]
    cur.close(); c.close()
    if cnt < 5:
        seeds = [
            'https://offenedaten-koeln.de/dataset?q=foerderung',
            'https://offenedaten-koeln.de/dataset?q=zuschuss',
            'https://offenedaten-koeln.de/dataset?q=zuwendung',
            'https://fragdenstaat.de/bund/',
            'https://fragdenstaat.de/nordrhein-westfalen/',
            'https://www.demokratie-leben.de/projekte',
            'https://www.demokratie-leben.de/foerderung',
            'https://www.foerderportal.nrw.de/',
            'https://www.land.nrw/foerderung',
            'https://www.vereinsregister.de/',
        ]
        c = db()
        cur = c.cursor()
        for s in seeds:
            cur.execute("INSERT INTO rheingold_crawl_queue (url,status,depth,added_at) VALUES (%s,'pending',0,NOW()) ON CONFLICT DO NOTHING", (s,))
        c.commit()
        cur.close(); c.close()
        log('refill', 'Seeds eingefügt')

def main():
    logger.info('Rheingold QUALITY Crawler gestartet')
    log('startup', 'Quality Crawler gestartet')
    last_ping = time.time()
    while True:
        try:
            refill()
            rows = pending()
            if not rows:
                time.sleep(60)
                continue
            for uid, url, depth, parent in rows:
                crawl_one(uid, url, depth or 0)
                time.sleep(3)
            if time.time() - last_ping > 300:
                log('ping', 'Rheingold lebt')
                last_ping = time.time()
        except KeyboardInterrupt:
            log('shutdown', 'Gestoppt')
            break
        except Exception as e:
            logger.error('Loop error: %s', e)
            time.sleep(30)

if __name__ == '__main__':
    main()
