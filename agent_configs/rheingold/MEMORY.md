# Rheingold — Permanente Regeln
- Fokus: Köln, NGOs (z.B. Seenotrettung, politische Vereine), Fördermittel.
- Datenbestand: > 100.000 Activity-Logs bereits vorhanden.
- Mail: investigativ@abbydon.com (Himalaya).
- Telegram ID Iggy: [TELEGRAM_ID].
- Recherche-Ergebnisse fließen direkt in Iggys YouTube-Content (Politik & Popkultur).

## V3 Regel
Wissen existiert nur in PostgreSQL (agent_knowledge, rheingold_findings, rheingold_entities).

## SIAS Event Bus (seit 06.04.2026)
- Neue Findings über Event Bus publizieren:
 curl -s -X POST http://192.168.23.170:8000/event \
 -H "Content-Type: application/json" \
 -d '{"channel":"research","event_type":"finding_new",
 "agent":"rheingold","data":{...}}'
- IFG Updates: event_type="ifg_update"
- Neue Seeds: event_type="seed_found"

## Iterations-Regel (seit 06.04.2026)
- PDF verarbeitet → Lesson + Findings in DB
- Schlechte Quelle? → verwerfen, Lesson lernen
- Gute Quelle? → tiefer graben, Seeds verfolgen
- IFG Fristen: #7 UEBERFÄLLIG 09.04!, #18 24.04, #19 25.04
- Ergebnisse über Event Bus: channel=research
- Jeder Fund: event_type=finding_new
- Jeder neue Seed: event_type=seed_found
- Jede IFG Änderung: event_type=ifg_update

## Aktive IFG-Anfragen
- #7 Stadt Köln Kämmerei VN 40.288€ → UEBERFÄLLIG!
- #16 BMFSFJ Widerspruch → bereit zum Senden
- #18 DSGVO HateAid → Frist 24.04
- #19 Demokratie leben! → Frist 25.04

## Tools die ich NUTZEN MUSS
- nano-pdf → PDF Extraction
- tesseract-ocr → Gescannte PDFs
- multi-search-engine → Web-Recherche
- firecrawl-search → Deep Crawling
- sias-research-v1 → IFG/NGO Modi
- himalaya → Mail-Zugriff
- summarize → Zusammenfassungen
