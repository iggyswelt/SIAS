# MEMORY.md - Permanentes Kern-Wissen

## User Präferenzen
- **Name**: Iggy
- **Timezone**: Europe/Berlin
- **Package Manager**: pnpm (nie npm)
- **CSS**: Vanilla + CSS Modules (kein Tailwind)
- **Bevorzugtes Model**: MiniMax-M2.5-highspeed
- **Sprache**: Deutsch

## Coding-Regeln (Critical)
- Python: Immer Type-Hints verwenden
- Python: f-strings bevorzugen
- Bash: Immer 'set -euo pipefail' am Anfang

## System-Wissen
- **Host**: metamaus (Ubuntu 24.04.4 LTS)
- **IP**: 192.168.23.170
- **PostgreSQL**: psycopg2 braucht --break-system-packages
- **Docker**: Version 29.2.1, Docker Compose Plugin v5.0.2

## Projekt-Status
- **Dashboard**: Command-Dashboard mit 5 Tabs, läuft auf Port 5000
- **Demo-Scraper**: demo_scraper_v2.py, 47 Demos in demos_new
- **Freqtrade**: Port 8080
- **Wekan**: Port 8081

## Wichtige Entscheidungen
- [2026-02-18] WAL-Protokoll als höchste Priorität etabliert
- [2026-02-18] MiniMax-M2.5-highspeed als Primary Model
- [2026-02-18] Strukturierte .learnings/ System eingeführt (Errors, Learnings, Corrections, Feature Requests)

## SOUL.md Regeln (Kurzfassung)
1. WAL-Protokoll: VOR jeder Antwort speichern, DANN antworten
2. Fehler sofort loggen in .learnings/ERRORS.md
3. SESSION-STATE.md bei Task-Start/Ende/Entscheidungen aktualisieren
4. Reflexion alle 10-15 Interaktionen
5. Kommunikation: Direkt, klar, keine Floskeln

## Aktuelle Learnings (Critical)
- [LRN-20260218-001] WAL-Protokoll etabliert (Priority: critical)
- [LRN-20260218-007] Fehler-Handling Protokoll (Priority: critical)
- [LRN-20260218-008] Compact & Session-Wechsel Protokoll (Priority: critical)
- [COR-20260218-003] Python Type-Hints + Bash set -euo pipefail (Priority: critical) - PROMOTED
- [COR-20260218-004] Python f-strings bevorzugen (Priority: critical) - PROMOTED

Letzte Aktualisierung: 2026-02-18 21:07

