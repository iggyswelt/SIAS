#!/usr/bin/env python3
"""
PDF Reindexierung v2 — Batch-orientiert, memory-effizient.
Verarbeitet PDFs in Chunks von 20.
"""
import subprocess, json, re, os, sys

def load_pdf_list():
    with open("/tmp/pdf_list.txt") as f:
        return [l.strip() for l in f if l.strip()]

def extract_text_fast(path):
    """Quick text extraction via pdftotext."""
    try:
        r = subprocess.run(['pdftotext', '-layout', '-l', '5', path, '-'],
                         capture_output=True, text=True, timeout=15)
        return r.stdout[:8000]  # first 5 pages max, 8000 chars
    except:
        return ""

def get_page_count(path):
    try:
        import subprocess
        r = subprocess.run(['pdfinfo', path], capture_output=True, text=True, timeout=5)
        for line in r.stdout.split('\n'):
            if line.startswith('Pages:'):
                return int(line.split(':')[1].strip())
    except:
        pass
    return 0

URL_RE = re.compile(r'https?://[^\s<>"\'\)\\,]{5,250}')
EMAIL_RE = re.compile(r'[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}')

ORG_LIST = [
    "AWO", "Arbeiterwohlfahrt", "Diakonie", "Caritas", "DRK", "Deutsches Rotes Kreuz",
    "SKM", "Terre des Hommes", "Gustav-Stresemann-Institut", "GSI", "IN-VIA",
    "Horizont e.V.", "Ombudsstelle", "Asienhaus", "Stiftung Asienhaus",
    "BMFSFJ", "Bundesministerium für Familie", "Stadt Köln", "Köln",
    "Landeshauptstadt Düsseldorf", "Düsseldorf", "NRW",
    "Demokratie leben", "EFL", "Evangelische Frauenarbeit", "HSU",
    "GWOe", "Bundesprogramm", "Ginko",
]

CAT_KEYWORDS = {
    "Haushalt": ["haushalt", "haushaltsplan", "ergebnisplan", "finanzplan", "hpl",
                 "investition", "vorbericht", "veränderungsnachweis",
                 "haushaltsrede", "kämm", "gesamtergebnis"],
    "Jahresbericht": ["jahresbericht", "jahresabschluss", "tätigkeitsbericht", "geschäftsbericht",
                       "jahresrechnung", "netzh"],
    "IFG": ["ifg", "informationsfreiheitsgesetz", "anfrage", "auskunft"],
    "Förderung": ["förderrichtlinie", "zuwendung", "förd", "zuschuss", "bewilligung",
                   "bescheid", "demokratie leben"],
    "Behörde": ["landeshauptstadt", "stadt köln", "oberbürgermeister",
                 "amt für", "dezernat", "stadtkämmerin"],
    "Organigramm": ["organigramm", "orgstruktur", "satzung", "governance"],
    "Migration": ["migration", "migrant", "geflüchtet", "asyl", "integration"],
    "Klima": ["klima", "klimaschutz", "umwelt"],
    "Drogen": ["drogen", "drogenhilfe", "streetwork", "sucht", "ginko"],
    "Entwicklung": ["entwicklung", "eine-welt", "städtepartnerschaft"],
    "Bundestag": ["btd", "bundestagsdrucksache", "afd", "kleine anfrage"],
}

def categorize(fname, text):
    fl = fname.lower()
    scores = {}
    for cat, kws in CAT_KEYWORDS.items():
        s = 0
        for kw in kws:
            if kw.lower() in fl:
                s += 3
            if kw.lower() in text[:500].lower():
                s += 1
        if s > 0:
            scores[cat] = s
    return max(scores, key=scores.get) if scores else "Sonstiges"

def extract_metadata(path, text, fname):
    links = list(set(u.rstrip('.,;)') for u in URL_RE.findall(text) if len(u) > 10))[:20]
    text_upper = text.upper()
    orgs = list(set(o for o in ORG_LIST if o.upper() in text_upper))
    emails = list(set(EMAIL_RE.findall(text)))
    
    # Find fristen
    fristen = []
    for line in text.split('\n'):
        if re.search(r'(?i)(frist|widerspruchsfrist|klagefrist|binnen|innerhalb)', line[:200]):
            fristen.append(line.strip()[:200])
    
    # Find dates
    dates = re.findall(r'\b(\d{1,2}[.]\d{1,2}[.]\d{2,4}|\d{4}-\d{2}-\d{2})', text)[:10]
    
    # Find Aktenzeichen
    az = re.findall(r'(\d{3,4}/\d{2,4}[\-\w/]*)', text)[:3]
    
    # Summary
    summary = ""
    for line in text.split('\n'):
        line = line.strip()
        if 50 < len(line) < 400 and not line.isupper():
            summary = line[:300]
            break
    
    # Contacts
    contacts = []
    phones = re.findall(r'(?i)(?:Tel|Telefon|Fax)[:\s]*([+\d\s\-/()]{8,20})', text)
    contacts.extend([f"Tel: {p.strip()}" for p in phones[:3]])
    contacts.extend([f"E-Mail: {e}" for e in emails[:3]])
    
    pages = 0
    try:
        r = subprocess.run(['pdfinfo', path], capture_output=True, text=True, timeout=5)
        for line in r.stdout.split('\n'):
            if line.startswith('Pages:'):
                pages = int(line.split(':')[1].strip())
    except:
        pass
    
    return {
        "datei": path,
        "dateiname": fname,
        "typ": categorize(fname, text),
        "seiten": pages,
        "zusammenfassung": summary,
        "links_gefunden": links,
        "organisationen": orgs,
        "fristen": fristen[:5],
        "emails": emails,
        "kontakte": contacts[:10],
        "seeds_neu": links[:15],
        "tools_used": ["pdftotext", "pdfinfo"],
        "pdf_pages": pages,
    }

def make_key(path):
    fname = os.path.basename(path)
    n = re.sub(r'[^\w\s]', '_', fname).lower()
    n = re.sub(r'_+', '_', n)[:100]
    return f"pdf_{n}"

def sql_insert(key, data):
    k = key.replace("'", "''")
    v = json.dumps(data, ensure_ascii=False).replace("'", "''")
    c = data.get("typ", "Sonstiges").replace("'", "''")
    return f"INSERT INTO agent_knowledge (key, value, category, learned_at) VALUES ('{k}', '{v}', '{c}', NOW()) ON CONFLICT (key) DO UPDATE SET value=EXCLUDED.value, category=EXCLUDED.category, updated_at=NOW();"

def sql_seed(url, source_pdf, org):
    u = url.replace("'", "''")
    s = source_pdf.replace("'", "''")
    o = org.replace("'", "''")
    return f"INSERT INTO osint_seeds_from_pdfs (url, source_pdf, organisation) VALUES ('{u}', '{s}', '{o}') ON CONFLICT (url) DO NOTHING;"

def main():
    pdfs = load_pdf_list()
    total = len(pdfs)
    print(f"🦅 Rheingold PDF Reindexierung v2 — {total} PDFs")
    
    cat_counts = {}
    records = []
    
    # Create seeds table first
    subprocess.run(['psql', '-h', '127.0.0.1', '-U', 'scraper', '-d', 'metamaus',
        '-c', 'CREATE TABLE IF NOT EXISTS osint_seeds_from_pdfs (id SERIAL PRIMARY KEY, url TEXT UNIQUE, source_pdf TEXT, organisation TEXT, discovered_at TIMESTAMP DEFAULT NOW());'],
        capture_output=True)
    
    for i, path in enumerate(pdfs):
        fname = os.path.basename(path)
        if (i+1) % 20 == 0:
            print(f"  [{i+1}/{total}] ...")
        
        text = extract_text_fast(path)
        if not text.strip():
            print(f"  SKIP (no text): {fname[:60]}")
            continue
        
        data = extract_metadata(path, text, fname)
        key = make_key(path)
        cat = data["typ"]
        cat_counts[cat] = cat_counts.get(cat, 0) + 1
        records.append((key, data))
    
    print(f"\n✅ {len(records)} PDFs erfolgreich verarbeitet")
    print("\nKategorien:")
    for c, n in sorted(cat_counts.items(), key=lambda x: -x[1]):
        print(f"  {c}: {n}")
    
    # Write SQL
    sql_parts = []
    seeds_sql = []
    total_links = 0
    total_orgs = set()
    
    for key, data in records:
        sql_parts.append(sql_insert(key, data))
        total_links += len(data.get("links_gefunden", []))
        total_orgs.update(data.get("organisationen", []))
        
        for url in data.get("seeds_neu", [])[:10]:
            org = data.get("organisationen", [""])[0] if data.get("organisationen") else ""
            seeds_sql.append(sql_seed(url, data["dateiname"], org))
    
    # Write and execute agent_knowledge inserts
    if sql_parts:
        sql_file = "/tmp/rheingold_pdf_knowledge.sql"
        with open(sql_file, 'w') as f:
            f.write("BEGIN;\n" + "\n".join(sql_parts) + "\nCOMMIT;\n")
        
        r = subprocess.run(['psql', '-h', '127.0.0.1', '-U', 'scraper', '-d', 'metamaus',
                          '-f', sql_file], capture_output=True, text=True, timeout=60)
        if r.returncode == 0:
            print(f"\n✅ {len(sql_parts)} records in agent_knowledge")
        else:
            print(f"\n⚠️ SQL error: {r.stderr[:300]}")
    
    # Write and execute seed inserts
    if seeds_sql:
        seed_file = "/tmp/rheingold_pdf_seeds.sql"
        with open(seed_file, 'w') as f:
            f.write("BEGIN;\n" + "\n".join(seeds_sql) + "\nCOMMIT;\n")
        
        r = subprocess.run(['psql', '-h', '127.0.0.1', '-U', 'scraper', '-d', 'metamaus',
                          '-f', seed_file], capture_output=True, text=True, timeout=60)
        if r.returncode == 0:
            print(f"✅ {len(seeds_sql)} seeds in osint_seeds_from_pdfs")
    
    # Step F: News Sources
    print("\nStep F: News Sources...")
    r = subprocess.run(['psql', '-h', '127.0.0.1', '-U', 'scraper', '-d', 'metamaus', '-c',
        "INSERT INTO news_sources (name, url, category) VALUES ('KotakuInAction', 'https://www.reddit.com/r/KotakuInAction/', 'gaming'), ('ThatParkPlace', 'https://thatparkplace.com/', 'gaming'), ('FandomPulse', 'https://fandompulse.substack.com/', 'gaming'), ('IGN DE', 'https://de.ign.com', 'gaming'), ('Insider Gaming', 'https://insider-gaming.com', 'gaming') ON CONFLICT DO NOTHING;"],
        capture_output=True, text=True, timeout=10)
    print("  ✅ News sources inserted/verified")
    
    # Final stats
    print(f"\n{'='*60}")
    print("📊 ERGEBNISSE")
    print(f"  PDFs verarbeitet: {len(records)}")
    print(f"  Links extrahiert: {total_links}")
    print(f"  Organisationen: {len(total_orgs)}")
    for org in sorted(total_orgs):
        print(f"    - {org}")
    
    # DB counts
    r = subprocess.run(['psql', '-h', '127.0.0.1', '-U', 'scraper', '-d', 'metamaus', '-t',
        '-c', "SELECT COUNT(*) FROM agent_knowledge WHERE key LIKE 'pdf_%';"],
        capture_output=True, text=True)
    print(f"\n  DB agent_knowledge (pdf_*): {r.stdout.strip()}")
    
    r = subprocess.run(['psql', '-h', '127.0.0.1', '-U', 'scraper', '-d', 'metamaus', '-t',
        '-c', "SELECT COUNT(*) FROM osint_seeds_from_pdfs;"],
        capture_output=True, text=True)
    print(f"  DB osint_seeds_from_pdfs: {r.stdout.strip()}")

if __name__ == "__main__":
    main()
