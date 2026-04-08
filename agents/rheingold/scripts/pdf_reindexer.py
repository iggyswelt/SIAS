#!/usr/bin/env python3
"""PDF Reindexierung für Rheingold — extrahiert Metadaten, Links, Orgs aus PDFs."""

import subprocess
import json
import re
import os
import sys
import hashlib
from pathlib import Path

import pdfplumber

PDF_DIRS = [
    "/home/iggy/.openclaw/rheingold_data/",
]

# Regex patterns
URL_RE = re.compile(r'https?://[^\s<>"\'\)\\,]{5,250}')
EMAIL_RE = re.compile(r'[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}')
DATE_RE = re.compile(r'\b(\d{1,2}[.]\d{1,2}[.]\d{2,4}|\d{4}-\d{2}-\d{2}|\d{1,2}\.\s*(?:Januar|Februar|März|April|Mai|Juni|Juli|August|September|Oktober|November|Dezember)\s+\d{4})\b')
AKTENZEICHEN_RE = re.compile(r'(?:Az\.|Aktenzeichen|Geschäftszeichen|GZ|Ref|Bearbeitungsnummer)[:\s]*([A-Z0-9\-/.\s]{5,50})', re.IGNORECASE)
FRIST_RE = re.compile(r'(?:Frist|innerhalb|binnen|bis zum|Widerspruchsfrist|Klagefrist|Klagerfrist)[:\s]*(.*?)(?:\n|\.|,)', re.IGNORECASE)

# Known organizations (for detection in text)
ORG_LIST = [
    "AWO", "Arbeiterwohlfahrt", "Diakonie", "Caritas", "DRK", "Deutsches Rotes Kreuz",
    "SKM", "Sozialdienst katholischer Männer", "Terre des Hommes",
    "Gustav-Stresemann-Institut", "GSI", "IN-VIA", "Horizont e.V.",
    "Ombudsstelle", "Asienhaus", "Stiftung Asienhaus", "DTK", "DITIB",
    "BMFSFJ", "Bundesministerium für Familie", "Stadt Köln", "Köln",
    "Landeshauptstadt Düsseldorf", "Düsseldorf", "NRW", "Geflüchtete",
    "Demokratie leben", "EFL", "Evangelische Frauenarbeit", "HSU",
    "GWOe", "Rheinland", "Netzwerk", "Bundesprogramm",
    "Verein für Geschichte und Naturkunde", "DFD",
]

CATEGORY_KEYWORDS = {
    "Haushalt": ["haushalt", "haushaltsplan", "ergebnisplan", "finanzplan", "hpl",
                 "einzelplan", "produktbereich", "investition", "vorbericht",
                 "veränderungsnachweis", "gesamtergebnisplan", "band_1", "band_2", "band_3",
                 "haushaltsrede", "beschluss", "rat der stadt", "kämmen"],
    "Jahresbericht": ["jahresbericht", "jahresabschluss", "tätigkeitsbericht", "geschäftsbericht",
                       "jährlich", "jahresrechnung"],
    "IFG": ["ifg", "informationsfreiheitsgesetz", "anfrage", "auskunft", "behörd",
             "informationszugang"],
    "Förderung": ["förderrichtlinie", "zuwendung", "förd", "zuschuss", "förderung",
                   "bewilligungsbescheid", "bescheid", "demokratie leben"],
    "Behörde": ["landeshauptstadt", "stadt köln", "oberbürgermeister", "städtisch",
                 "amt für", "dezernat", "stadtkämmerin"],
    "Organigramm": ["organigramm", "orgstruktur", "satzung", "governance", "organis"],
    "Migration": ["migration", "migrant", "geflüchtet", "asyl", "einwanderung", "integration"],
    "Klima": ["klima", "klimaschutz", "umwelt", "nachhaltigkeit"],
    "Drogen": ["drogen", "drogenhilfe", "streetwork", "sucht", "ginko"],
    "Entwicklung": ["entwicklung", "eine-welt", "städtepartnerschaft"],
    "Bundestag": ["btd", "bundestagsdrucksache", "afd", "anfrage", "kleine anfrage"],
}


def find_pdfs():
    pdfs = []
    for d in PDF_DIRS:
        for root, dirs, files in os.walk(d):
            for f in files:
                if f.lower().endswith('.pdf'):
                    full = os.path.join(root, f)
                    pdfs.append(full)
    return sorted(pdfs)


def extract_text_pdfplumber(path):
    """Extract text using pdfplumber."""
    try:
        with pdfplumber.open(path) as pdf:
            pages = []
            for page in pdf.pages:
                text = page.extract_text() or ""
                pages.append(text)
            return "\n".join(pages), len(pdf.pages)
    except Exception as e:
        return "", 0


def extract_text_pdftotext(path):
    """Fallback using pdftotext."""
    try:
        result = subprocess.run(['pdftotext', '-layout', path, '-'], capture_output=True, text=True, timeout=30)
        return result.stdout
    except Exception:
        return ""


def get_pdfinfo(path):
    """Get PDF metadata."""
    try:
        result = subprocess.run(['pdfinfo', path], capture_output=True, text=True, timeout=10)
        info = {}
        for line in result.stdout.split('\n'):
            if ':' in line:
                key, val = line.split(':', 1)
                info[key.strip()] = val.strip()
        return info
    except Exception:
        return {}


def find_links(text):
    urls = list(set(URL_RE.findall(text)))
    # Clean up URLs
    clean = []
    for u in urls:
        u = u.rstrip('.,;)')
        if len(u) > 10 and not u.endswith('.pdf.'):
            clean.append(u)
    return list(set(clean))


def find_orgs(text):
    found = []
    text_upper = text.upper()
    for org in ORG_LIST:
        if org.upper() in text_upper:
            found.append(org)
    return list(set(found))


def find_emails(text):
    return list(set(EMAIL_RE.findall(text)))


def find_dates(text):
    return list(set(DATE_RE.findall(text)))[:10]


def find_fristen(text):
    results = []
    for line in text.split('\n'):
        if re.search(r'(?i)(frist|widerspruchsfrist|klagefrist|binnen|innerhalb|bis zum)', line):
            results.append(line.strip()[:200])
    return results[:5]


def find_aktenzeichen(text):
    results = []
    for m in AKTENZEICHEN_RE.finditer(text):
        results.append(m.group(1).strip()[:50])
    # Also look for common patterns
    for m in re.finditer(r'(\d{1,4}/\d{1,4}[\-\w/]*)', text):
        val = m.group(1)
        if 5 < len(val) < 30 and not val.startswith('http'):
            results.append(val)
    return list(set(results))[:5]


def categorize(filename, text):
    """Determine document category."""
    fname_lower = filename.lower()
    scores = {}
    for cat, keywords in CATEGORY_KEYWORDS.items():
        score = 0
        for kw in keywords:
            if kw.lower() in fname_lower:
                score += 3
            if kw.lower() in text[:500].lower():
                score += 1
        if score > 0:
            scores[cat] = score
    if not scores:
        return "Sonstiges"
    return max(scores, key=scores.get)


def find_contacts(text):
    """Find contact names and info."""
    contacts = []
    # Look for patterns like "Name, Titel" or phone numbers
    phone_re = re.compile(r'(?:Tel|Telefon|Fax|Tel\.)[:\s]*([+\d\s\-/()]{8,25})')
    for m in phone_re.finditer(text):
        contacts.append(f"Telefon: {m.group(1).strip()}")

    # Email as contact
    emails = find_emails(text)
    for e in emails:
        contacts.append(f"E-Mail: {e}")

    # Known official titles
    title_patterns = [
        r'([A-Z][a-zäöüß]+\s+[A-Z][a-zäöüß]+),\s*(?:Referat|Abteilung|Amt|Dezernat)',
        r'(?:Herr|Frau)\s+([A-Z][a-zäöüß]+[\s\-][A-Z][a-zäöüß]+)',
    ]
    for pat in title_patterns:
        for m in re.finditer(pat, text[:3000]):
            name = m.group(1).strip()
            if len(name) > 4 and len(name) < 40:
                contacts.append(name)

    return list(set(contacts))[:10]


def make_key(path):
    """Create DB key from filename."""
    fname = os.path.basename(path)
    # Normalize: remove special chars
    normalized = re.sub(r'[^\w\s]', '_', fname)
    normalized = re.sub(r'__+', '_', normalized).lower()[:100]
    return f"pdf_{normalized}"


def process_pdf(path):
    """Process single PDF and return record."""
    fname = os.path.basename(path)
    print(f"  processing: {fname[:80]}")

    # Extract text
    text, page_count = extract_text_pdfplumber(path)
    if len(text.strip()) < 50:
        text2 = extract_text_pdftotext(path)
        if len(text2.strip()) > len(text):
            text = text2

    pdfinfo = get_pdfinfo(path)
    text_sample = text[:5000]  # For analysis, keep manageable

    category = categorize(fname, text)
    links = find_links(text_sample)
    orgs = find_orgs(text)
    emails = find_emails(text)
    dates = find_dates(text_sample)
    fristen = find_fristen(text_sample)
    aktenzeichen = find_aktenzeichen(text_sample)
    contacts = find_contacts(text)

    # Summary (first meaningful paragraph)
    summary = ""
    for line in text[:3000].split('\n'):
        line = line.strip()
        if len(line) > 50 and not line.isupper():
            summary = line[:300]
            break

    key = make_key(path)

    record = {
        "key": key,
        "category": category,
        "value": json.dumps({
            "datei": path,
            "dateiname": fname,
            "typ": category,
            "seiten": page_count,
            "absender": pdfinfo.get("Author", "") or pdfinfo.get("Creator", ""),
            "datum": pdfinfo.get("CreationDate", ""),
            "aktenzeichen": aktenzeichen,
            "zusammenfassung": summary,
            "links_gefunden": links[:20],
            "organisationen": orgs,
            "fristen": fristen,
            "emails": emails,
            "kontakte": contacts,
            "seeds_neu": links[:20],
            "tools_used": ["pdfplumber", "pdftotext", "pdfinfo"],
            "pdf_pages": page_count,
            "text_length": len(text),
        }, ensure_ascii=False),
    }

    return record


def generate_sql_insert(record):
    """Generate SQL INSERT statement."""
    key_esc = record["key"].replace("'", "''")
    val_esc = record["value"].replace("'", "''")
    cat_esc = record["category"].replace("'", "''")

    return f"""INSERT INTO agent_knowledge (key, value, category, learned_at)
VALUES ('{key_esc}', '{val_esc}', '{cat_esc}', NOW())
ON CONFLICT (key) DO UPDATE SET value=EXCLUDED.value, category=EXCLUDED.category, updated_at=NOW();"""


def generate_seed_sql(record):
    """Generate SQL for osint_seeds_from_pdfs."""
    data = json.loads(record["value"])
    fname = data.get("dateiname", "")
    sql = ""
    for url in data.get("links_gefunden", [])[:10]:
        url_esc = url.replace("'", "''")
        fname_esc = fname.replace("'", "''")
        orgs = data.get("organisationen", [])
        org_str = orgs[0] if orgs else ""
        org_esc = org_str.replace("'", "''")
        sql += f"INSERT INTO osint_seeds_from_pdfs (url, source_pdf, organisation) VALUES ('{url_esc}', '{fname_esc}', '{org_esc}') ON CONFLICT (url) DO NOTHING;\n"
    return sql


def main():
    print("🦅 Rheingold PDF Reindexierung V3")
    print("=" * 60)

    # Create seeds table
    print("\nStep E: Creating osint_seeds_from_pdfs table...")
    subprocess.run([
        'psql', '-h', '127.0.0.1', '-U', 'scraper', '-d', 'metamaus',
        '-c', """
        CREATE TABLE IF NOT EXISTS osint_seeds_from_pdfs (
            id SERIAL PRIMARY KEY,
            url TEXT UNIQUE,
            source_pdf TEXT,
            organisation TEXT,
            discovered_at TIMESTAMP DEFAULT NOW()
        );
        """
    ], capture_output=True)

    # Find all PDFs
    pdfs = find_pdfs()
    print(f"\nStep A: Found {len(pdfs)} PDFs")

    # Process all PDFs
    print("\nStep B-C: Processing PDFs...")
    records = []
    category_counts = {}

    for i, pdf_path in enumerate(pdfs):
        try:
            record = process_pdf(pdf_path)
            records.append(record)
            cat = record["category"]
            category_counts[cat] = category_counts.get(cat, 0) + 1
        except Exception as e:
            print(f"  ERROR: {os.path.basename(pdf_path)[:60]}: {e}")

    print(f"\nProcessed {len(records)}/{len(pdfs)} PDFs")
    print("\nCategories:")
    for cat, count in sorted(category_counts.items(), key=lambda x: -x[1]):
        print(f"  {cat}: {count}")

    # Step D: Insert into DB
    print(f"\nStep D: Inserting {len(records)} records into agent_knowledge...")

    # Write SQL to file and run it
    sql_file = "/tmp/pdf_reindex_insert.sql"
    with open(sql_file, 'w') as f:
        for r in records:
            f.write(generate_sql_insert(r) + "\n")

    result = subprocess.run(
        ['psql', '-h', '127.0.0.1', '-U', 'scraper', '-d', 'metamaus', '-f', sql_file],
        capture_output=True, text=True, timeout=60
    )
    if result.returncode != 0:
        print(f"  SQL errors: {result.stderr[:500]}")
    else:
        print("  ✅ All records inserted successfully")

    # Step E: Insert seeds
    print("\nStep E: Inserting seeds into osint_seeds_from_pdfs...")
    seeds_file = "/tmp/pdf_reindex_seeds.sql"
    seed_count = 0
    with open(seeds_file, 'w') as f:
        for r in records:
            sql = generate_seed_sql(r)
            f.write(sql)
            seed_count += sql.count("INSERT")

    result = subprocess.run(
        ['psql', '-h', '127.0.0.1', '-U', 'scraper', '-d', 'metamaus', '-f', seeds_file],
        capture_output=True, text=True, timeout=60
    )
    if result.returncode != 0:
        print(f"  SQL errors: {result.stderr[:500]}")
    else:
        print(f"  ✅ Seeds inserted")

    # Final stats
    print("\n" + "=" * 60)
    print("📊 ERGEBNISSE")
    print(f"  PDFs verarbeitet: {len(records)}")

    # Count links
    total_links = sum(len(json.loads(r["value"]).get("links_gefunden", [])) for r in records)
    print(f"  Links extrahiert: {total_links}")

    # Count orgs
    all_orgs = set()
    for r in records:
        all_orgs.update(json.loads(r["value"]).get("organisationen", []))
    print(f"  Organisationen identifiziert: {len(all_orgs)}")
    for org in sorted(all_orgs):
        print(f"    - {org}")

    # DB counts
    result = subprocess.run(
        ['psql', '-h', '127.0.0.1', '-U', 'scraper', '-d', 'metamaus',
         '-t', '-c', 'SELECT COUNT(*) FROM agent_knowledge WHERE key LIKE \'pdf_%\';'],
        capture_output=True, text=True
    )
    print(f"\n  DB agent_knowledge (pdf_*): {result.stdout.strip()}")

    result = subprocess.run(
        ['psql', '-h', '127.0.0.1', '-U', 'scraper', '-d', 'metamaus',
         '-t', '-c', 'SELECT COUNT(*) FROM osint_seeds_from_pdfs;'],
        capture_output=True, text=True
    )
    print(f"  DB osint_seeds_from_pdfs: {result.stdout.strip()}")


if __name__ == "__main__":
    main()
