# SIAS — Self Improving Agent System

[![Version](https://img.shields.io/badge/version-3.2-blue)]()
[![Architecture](https://img.shields.io/badge/arch-event--driven-green)]()
[![License](https://img.shields.io/badge/license-MIT-orange)]()

---

## 🇩🇪 Was ist SIAS?

SIAS (**S**uper **I**ntelligent **A**gent **S**ystem) ist ein event-gesteuertes Multi-Agenten-System, gebaut auf [OpenClaw](https://openclaw.ai). Agenten kommunizieren über einen Redis Event Bus, PostgreSQL dient als einzige Source of Truth. Das System automatisiert Forschung, Trading, OSINT, Scraping, Security und Dokumentation.

### Architektur

- **Event-driven** — Alle Agenten reagieren auf Redis-Pub/Sub-Events
- **FastAPI** — SIAS Core API als zentraler Gateway
- **PostgreSQL** — Persistente Datenspeicherung, Agent-Knowledge, Audit-Logs
- **Redis** — Event Bus für Inter-Agent-Kommunikation
- **3 Worker Services** — Hermes (Scraping), Rheingold (OSINT), Hestia (YouTube)

### Agenten (10)

| Agent | Rolle | Fokus |
|-------|-------|-------|
| **metamaus** | Commander | Strategie, Koordination, Team-Lead |
| **apollon** | Code | Entwicklung, CI/CD, Skripting |
| **athene** | Trading | Marktanalyse, Portfolio-Strategie |
| **rheingold** | OSINT | Open Source Intelligence, Recherche |
| **pythia** | Audit | Datenintegrität, Validierung, Compliance |
| **hermes** | Scraping | Web-Crawling, Datenextraktion |
| **hestia** | YouTube | Video-Transkription, Content-Analyse |
| **orpheus** | Backup/Docs | Datensicherung, GitHub, Versionierung |
| **zerberus** | Security | Infrastruktur-Monitoring, Firewalls |
| **arthemis** | Architect | QA, Systemdesign, Architektur-Review |

### Hardware Setup

| Komponente | Spezifikation |
|------------|--------------|
| Host | Ubuntu Server (x64) |
| RAM | 16 GB+ empfohlen |
| Storage | SSD 256 GB+ |
| Datenbank | PostgreSQL 16+ |
| Cache/Bus | Redis 7+ |
| Runtime | Node.js 22+, Python 3.11+ |

### Quick Start

```bash
# 1. Repository klonen
git clone https://github.com/YOUR_USER/SIAS.git
cd SIAS

# 2. Abhängigkeiten installieren
pip install -r requirements.txt
npm install

# 3. Umgebungsvariablen konfigurieren
cp .env.example .env
# Bearbeite .env mit deinen Credentials

# 4. Datenbank starten
sudo systemctl start postgresql redis

# 5. SIAS Core API starten
cd sias_core && uvicorn main:app --host 127.0.0.1 --port 8000

# 6. Worker starten (je nach Bedarf)
python worker_hermes.py   # Scraping
python worker_rheingold.py # OSINT
python worker_hestia.py   # YouTube
```

---

## 🇬🇧 What is SIAS?

SIAS (**S**uper **I**ntelligent **A**gent **S**ystem) is an event-driven multi-agent platform built on [OpenClaw](https://openclaw.ai). Agents communicate via a Redis Event Bus with PostgreSQL as the single source of truth. The system automates research, trading, OSINT, scraping, security, and documentation.

### Architecture

- **Event-driven** — All agents react to Redis Pub/Sub events
- **FastAPI** — SIAS Core API as central gateway
- **PostgreSQL** — Persistent storage, agent knowledge, audit logs
- **Redis** — Event bus for inter-agent communication
- **3 Worker Services** — Hermes (Scraping), Rheingold (OSINT), Hestia (YouTube)

### Agents (10)

| Agent | Role | Focus |
|-------|------|-------|
| **metamaus** | Commander | Strategy, coordination, team lead |
| **apollon** | Code | Development, CI/CD, scripting |
| **athene** | Trading | Market analysis, portfolio strategy |
| **rheingold** | OSINT | Open Source Intelligence, research |
| **pythia** | Audit | Data integrity, validation, compliance |
| **hermes** | Scraping | Web crawling, data extraction |
| **hestia** | YouTube | Video transcription, content analysis |
| **orpheus** | Backup/Docs | Data backup, GitHub, versioning |
| **zerberus** | Security | Infrastructure monitoring, firewalls |
| **arthemis** | Architect | QA, system design, architecture review |

### Hardware Setup

| Component | Specification |
|-----------|--------------|
| Host | Ubuntu Server (x64) |
| RAM | 16 GB+ recommended |
| Storage | SSD 256 GB+ |
| Database | PostgreSQL 16+ |
| Cache/Bus | Redis 7+ |
| Runtime | Node.js 22+, Python 3.11+ |

### Quick Start

```bash
# 1. Clone repository
git clone https://github.com/YOUR_USER/SIAS.git
cd SIAS

# 2. Install dependencies
pip install -r requirements.txt
npm install

# 3. Configure environment
cp .env.example .env
# Edit .env with your credentials

# 4. Start database
sudo systemctl start postgresql redis

# 5. Start SIAS Core API
cd sias_core && uvicorn main:app --host 127.0.0.1 --port 8000

# 6. Start workers (as needed)
python worker_hermes.py    # Scraping
python worker_rheingold.py # OSINT
python worker_hestia.py    # YouTube
```

---

## Dokumentation / Documentation

- [Architektur](docs/ARCHITECTURE.md) — Technische Details
- [Agenten](docs/AGENTS.md) — Alle Agenten & Rollen
- [Setup](docs/SETUP.md) — Installation & Konfiguration
- [Changelog](docs/CHANGELOG.md) — Versionshistorie

## Lizenz / License

MIT License — siehe [LICENSE](LICENSE)
