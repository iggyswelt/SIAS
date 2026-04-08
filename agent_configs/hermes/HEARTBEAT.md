# Hermes — Heartbeat
Interval: 180m

## Routine:
1. QC-Check: Prüfe alle 6 Core-Tabs der Plattform auf Erreichbarkeit.
2. Crawl-Queue: Gibt es neue Ziele in hermes_scrape_queue?
3. Status-Report:
 - OK: Scraper laufen, Vision-Modul bereit.
 - WARN: Rate-Limits bei Zielseiten erreicht.
 - CRITICAL: DB-Connection für Scrapes verloren.
