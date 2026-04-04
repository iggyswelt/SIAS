# SIAS Changelog

## v2.1 - "The Multi-Agent Update"
**Released:** 2026-03-17

### New Features

#### Multi-Agent System (8 Agents)
- **metamaus** - Teamleader & Architekt
- **Apollon** - Code & Scripts
- **Athena** - Trading & Backtest
- **Hermes** - Demo-Scraper & Crawling
- **Rheingold** - IFG & Transparenz-Recherche
- **Zerberus** - Security & Netzwerk
- **Hestia** - YouTube & Comments
- **Orpheus** - Backups & Vault

#### Dashboard v1.0
- 8 Tabs: Overview, Trading, Demos, Rheingold, Network, Backtest, Agents, Portfolio
- Real-time stats
- Agent management

#### Rheingold IFG-System
- Mail-Integration via Himalaya
- IFG-Anfragen in DB
- Widerspruchs-Workflow
- Automatischer Versand

#### Pythia Vision
- LM Studio Integration
- Bildanalyse via Qwen3-VL
- Workstation-basiert (RedQueen)

#### Hyperopt Marathon
- 478 Strategien geladen
- DutchAlgoTrading Top-50 Referenz
- Auto-Queue System

#### Mail-Versand
- SMTP via mail.abydon.com
- Dashboard Integration
- Tracking in DB

### Improvements
- PostgreSQL-only Memory (keine .md Files mehr)
- api-swap.txt Workflow für Credentials
- Agent-Templates in DB
- Auto-Sync Dashboard mit openclaw.json

### Bug Fixes
- Demo-Scraper Ghost-Trigger eliminiert
- Mail-API (echter Versand statt nur DB-Update)
- Dashboard Port-Konflikt behoben

---

## v2.0 - "The Foundation"
**Released:** 2026-02

### Features
- OpenClaw Integration
- Grundlegende Agent-Struktur
- Dashboard Beta
