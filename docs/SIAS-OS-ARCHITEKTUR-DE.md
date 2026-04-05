# SIAS-OS Architektur (v3.1)

## Überblick
SIAS ist eine event-gesteuerte Multi-Agent Plattform.
OpenClaw dient als Runtime-Shell, SIAS ist das Gehirn.

## Komponenten
- **SIAS Core API** (FastAPI, Port 8000) — Gehirn
- **Redis Event Bus** (Cronos, Port 6379) — Kommunikation
- **PostgreSQL** (metamaus, Port 5432) — Einzige Wahrheit
- **OpenClaw** — Runtime Shell (Telegram, Exec, Cron)

## Event-Kette (verifiziert)
Athene findet Signal → Redis → Hermes validiert →
Redis → Zerberus prüft Security → Redis → Alert

## 9 Agenten, 4 Provider, 2 Server
Kein Single Point of Failure.
PostgreSQL ist die einzige Source of Truth.
