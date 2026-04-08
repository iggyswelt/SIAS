#!/usr/bin/env python3
"""Rheingold QUALITY Crawler - nur echte Foerderungen/Zuschuesse/Zuwendungen."""
import requests
import re
import time
import logging
from bs4 import BeautifulSoup
import psycopg2
from urllib.parse import urljoin, urlparse

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger()
DB = dict(database="metamaus", user="scraper", host="localhost")

ALLOWED = {
    "offenedaten-koeln.de", "stadt-koeln.de", "fragdenstaat.de",
    "demokratie-leben.de", "foerderportal.nrw.de", "land.nrw",
    "vereinsregister.de", "handelsregister.de", "bundestag.de",
    "bundesregierung.de", "bmfsfj.de", "bmi.bund.de", "oparl.org"
}

GOOD_KW = ["foerder", "zuschuss", "zuwendung", "bewilligt", "auszahlung", "empfanger", "beihilfe", "haushaltsplan", "haushalt"]
BAD_KW = ["kredit", "darlehen", "kfw", "investitionsbank", "klimaneutral", "klimaschutz", "gutachten", "spende", "menu", "navigation", "footer", "kontakt", "impressum", "datenschutz"]
MIN_AMT = 100
MAX_AMT = 50000000


def db_connect():
    return psycopg2.connect(**DB)


def log_msg(action, desc):
    try:
        c = db_connect()
        cur = c.cursor()
        cur.execute(
            "INSERT INTO rheingold_activity_log (action_type, description, status) "
            "VALUES (%s, %s, 'running')",
            (action, str(desc)[:200])
        )
        c.commit()
        cur.close()
        c.close()
    except Exception as e:
        logger.error("log failed: %s", e)


def get_pending():
    c = db_connect()
    cur = c.cursor()
    cur.execute(
        "SELECT id, url, depth, parent_url FROM rheingold_crawl_queue "
        "WHERE status='pending' ORDER BY added_at LIMIT 5"
    )
    rows = list(cur.fetchall())
    cur.close()
    c.close()
    return rows


def mark_done(uid, status, fc=0):
    try:
        c = db_connect()
        cur = c.cursor()
        cur.execute(
            "UPDATE rheingold_crawl_queue SET status=%s, crawled_at=NOW(), findings_count=%s WHERE id=%s",
            (status, fc, uid)
        )
        c.commit()
        cur.close()
        c.close()
    except Exception as e:
        logger.error("mark_done failed: %s", e)


def save_finding(data):
    amt = data.get("betrag", 0)
    ctx = (str(data.get("beschreibung", "") + " " + str(data.get("quelle", "")).lower()
    if any(b in ctx for b in BAD_KW):
        return 0
    if amt and (amt > MAX_AMT or amt < MIN_AMT):
        return 0
    if amt and amt > 1000000 and not any(g in ctx for g in GOOD_KW):
        return 0
    if not any(g in ctx for g in GOOD_KW):
        return 0
    try:
        c = db_connect()
        cur = c.cursor()
        cur.execute(
            "INSERT INTO rheingold_findings "
            "(beschreibung, quelle, betrag, kategorie, fokus, region, is_verified, created_at) "
            "VALUES (%s, %s, %s, 'foerderung', 'bund', 'bund', TRUE, NOW()) "
            "ON CONFLICT DO NOTHING",
            (str(data.get("beschreibung", "")[:500], str(data.get("quelle", "")[:200], amt)
        )
        c.commit()
        cur.close()
        c.close()
        return 1
    except Exception as e:
        logger.error("save failed: %s", e)
        try:
            db_connect().close()
        except:
            pass
        return 0


def quality_links(html, base_url):
    soup = BeautifulSoup(html, "html.parser")
    found = []
    for a in soup.find_all("a", href=True):
        href = a["href"]
        full_url = urljoin(base_url, href)
        parsed = urlparse(full_url)
        lt = (a.get_text() + " " + href).lower()
        if parsed.netloc and parsed.netloc not in ALLOWED:
            continue
        if any(b in lt for b in BAD_KW):
            continue
        if not any(g in lt for g in GOOD_KW):
            continue
        found.append(full_url)
    seen = {}
    for u in found:
        seen[u] = 1
    return list(seen)[:10]


def crawl_one(uid, url, depth=0):
    logger.info("Crawl [%s]: %s", depth, url[:60])
    log_msg("crawl", "Crawle: " + url[:50])
    try:
        r = requests.get(
            url,
            headers={"User-Agent": "RheingoldBot/1.0"},
            timeout=20
        )
        r.raise_for_status()
        html = r.text
        text = html.lower()
        if not any(g in text for g in GOOD_KW):
            mark_done(uid, "crawled", 0)
            return 0
        soup = BeautifulSoup(html, "html.parser")
        saved = 0
        for m in re.findall(r"[\d.,]+\s*(?:EUR|EUR|Euro|Euro|Mio|mio|EUR|eur)", html):
            try:
                raw = re.sub(r"[^\d.,]", "", m).replace(",", ".")
                amt = float(raw)
                desc = soup.get_text()[:200].replace(chr(10), " ")
                if save_finding({"beschreibung": desc, "quelle": url, "betrag": amt}):
                    saved += 1
            except:
                pass
        if depth < 3:
            links = quality_links(html, url)
            if links:
                c = db_connect()
                cur = c.cursor()
                for link in links:
                    cur.execute(
                        "INSERT INTO rheingold_crawl_queue "
                        "(url, status, depth, parent_url, added_at) "
                        "VALUES (%s, 'pending', %s, %s, NOW()) "
                        "ON CONFLICT DO NOTHING",
                        (link, depth + 1, url)
                    )
                c.commit()
                cur.close()
                c.close()
        mark_done(uid, "crawled", saved)
        log_msg("done", "Crawled: " + url[:50] + " (" + str(saved) + " qual.)")
        return saved
    except Exception as e:
        logger.error("Error: %s", e)
        mark_done(uid, "failed", 0)
        log_msg("error", "Error: " + str(e)[:60])
        return 0


def auto_refill():
    c = db_connect()
    cur = c.cursor()
    cur.execute("SELECT COUNT(*) FROM rheingold_crawl_queue WHERE status='pending'")
    cnt = cur.fetchone()[0]
    cur.close()
    c.close()
    if cnt < 5:
        logger.info("Queue low (%s) - refilling", cnt)
        seeds = [
            "https://offenedaten-koeln.de/dataset?q=foerderung",
            "https://offenedaten-koeln.de/dataset?q=zuschuss",
            "https://offenedaten-koeln.de/dataset?q=zuwendung",
            "https://fragdenstaat.de/bund/",
            "https://fragdenstaat.de/nordrhein-westfalen/",
            "https://www.demokratie-leben.de/projekte",
            "https://www.demokratie-leben.de/foerderung",
            "https://www.foerderportal.nrw.de/",
            "https://www.land.nrw/foerderung",
            "https://www.vereinsregister.de/",
        ]
        c = db_connect()
        cur = c.cursor()
        for s in seeds:
            cur.execute(
                "INSERT INTO rheingold_crawl_queue (url, status, depth, added_at) "
                "VALUES (%s, 'pending', 0, NOW()) ON CONFLICT DO NOTHING",
                (s,)
            )
        c.commit()
        cur.close()
        c.close()
        log_msg("refill", "Refilled queue with " + str(len(seeds)) + " seeds")


def main():
    logger.info("Rheingold QUALITY Crawler gestartet")
    log_msg("startup", "Quality Crawler gestartet")
    ping_t = time.time()
    while True:
        try:
            auto_refill()
            rows = get_pending()
            if not rows:
                time.sleep(60)
                continue
            for uid, url, depth, parent in rows:
                crawl_one(uid, url, depth or 0)
                time.sleep(3)
            if time.time() - ping_t > 300:
                log_msg("ping", "lebt noch")
                ping_t = time.time()
        except KeyboardInterrupt:
            log_msg("shutdown", "Gestoppt")
            break
        except Exception as e:
            logger.error("Loop error: %s", e)
            time.sleep(30)


if __name__ == "__main__":
    main()
