# SIAS Architektur — v2.1

*Letzte Aktualisierung: 2026-03-19*

---

## Überblick

**SIAS (Self-Initiating Autonomous System)** ist ein persistentes Gedächtnis- und Lern-Framework für OpenClaw AI Agents. Es ermöglicht kontinuierliche Selbstverbesserung durch strukturiertes Fehler-Logging, PostgreSQL-gestütztes Gedächtnis und autonome Agenten-Teams.

```
┌──────────────────────────────────────────────────────────────┐
│                     USER (Iggy)                              │
│              Telegram / YouTube / Terminal                   │
└──────────────────────┬───────────────────────────────────────┘
                       │ steuert
                       ▼
┌──────────────────────────────────────────────────────────────┐
│              OPENCLAW GATEWAY (192.168.23.170)                │
│         Modell: minimax-direct / MiniMax-M2.5-highspeed      │
│         Channels: Telegram, Webhook, Exec                    │
└──────────────────────┬───────────────────────────────────────┘
                       │ delegiert
          ┌────────────┼────────────┐
          ▼            ▼            ▼
   ┌───────────┐ ┌───────────┐ ┌───────────┐
   │  metamaus │ │  apollon  │ │ rheingold │
   │  (TL+Arch)│ │  (Code)   │ │(Recherche)│
   └───────────┘ └───────────┘ └───────────┘
          │            │            │
          └────────────┼────────────┘
                       │ PostgreSQL
                       ▼
┌──────────────────────────────────────────────────────────────┐
│                    PostgreSQL (metamaus DB)                   │
│  learnings │ memory │ rheingold_* │ athena_* │ vault         │
└──────────────────────────────────────────────────────────────┘
```

---

## Die drei Schichten

```
┌─────────────────────────────────────────────────────┐
│  SCHICHT 3 — TEAMLEADER                            │
│  metamaus (🐭) — Koordiniert, delegiert, lernt    │
├─────────────────────────────────────────────────────┤
│  SCHICHT 2 — AGENTS (8 Spezialisten)              │
│  Apollon 🛠️ · Athena 📈 · Hermes 📡 · Rheingold 🦅│
│  Zerberus 🛡️ · Hestia 💬 · Orpheus 🎵 · Pythia 👁️│
├─────────────────────────────────────────────────────┤
│  SCHICHT 1 — DATEN-INFRASTRUKTUR                   │
│  PostgreSQL · WAL-Log · Vault · NAS-Backups        │
└─────────────────────────────────────────────────────┘
```

---

## Komponenten

### 3.1 OpenClaw Gateway
- **Host:** 192.168.23.170
- **Channels:** Telegram (737961726), Exec, Webhook
- **Model:** MiniMax-M2.5-highspeed (primary)
- **Config:** `/etc/openclaw/openclaw.json` (READ-ONLY)

### 3.2 metamaus — Teamleader 🐭
| Property | Value |
|----------|-------|
| Agent | metamaus |
| Verantwortung | Koordination, Delegation, Architektur |
| Workspace | `/home/iggy/.openclaw/agents/metamaus/` |
| Modelle | minimax-direct, alicloud |
| DB User | scraper |
| DB | metamaus |

### 3.3 Apollon — Code & Scripts 🛠️
| Property | Value |
|----------|-------|
| Verantwortung | Dashboard (Flask), Scripts, Code-Review |
| Server | metamaus |
| Ports | 5000 (PROD), 5001 (DEV) |
| Technologien | Flask, PostgreSQL, Playwright |

### 3.4 Athena — Trading & Hyperopt 📈
| Property | Value |
|----------|-------|
| Verantwortung | Trading, Backtest, Hyperopt Marathon |
| Server | Cronos (192.168.23.80) |
| Hardware | 50 Cores, 22TB HDD (/mnt/bigdata) |
| Parallel Jobs | 40 |
| Tabellen | athena_hyperopt_queue, athena_trades |

### 3.5 Hermes — Demo-Scraper & Crawling 📡
| Property | Value |
|----------|-------|
| Verantwortung | Web-Scraping, Crawling, Demo-Daten |
| Server | metamaus |
| Tools | Playwright (JS-heavy sites), httpx |
| Tabellen | rheingold_crawl_queue |

### 3.6 Rheingold — IFG & Recherche 🦅
| Property | Value |
|----------|-------|
| Verantwortung | IFG-Anfragen, Förder-Recherche, NGO-Daten |
| Server | metamaus |
| Tabellen | rheingold_findings, rheingold_crawl_queue |
| Zielprojekt | Fördermittel-Transparenz |

### 3.7 Zerberus — Security & Netzwerk 🛡️
| Property | Value |
|----------|-------|
| Verantwortung | Netzwerk-Monitoring, Security Audits |
| Server | metamaus |
| Tabellen | network_assets, zerberus_tasks |
| Sensoren | Prometheus-Exporter |

### 3.8 Hestia — YouTube & Comments 💬
| Property | Value |
|----------|-------|
| Verantwortung | YouTube-Kommentare, Community |
| Server | metamaus |
| Kanal | @iggyswelt |
| Tabellen | hestia_comments |

### 3.9 Orpheus — Backups & Vault 🎵
| Property | Value |
|----------|-------|
| Verantwortung | Backups, PKI, Vault, SIAS Releases |
| Server | metamaus + NAS (192.168.23.104) |
| Backup-Ziel | NAS |
| Tabellen | vault |

### 3.10 Pythia — Vision & Bildanalyse 👁️
| Property | Value |
|----------|-------|
| Verantwortung | Bildanalyse, Screenshots, Vision Stack |
| Server | RedQueen (192.168.23.101, DEPRECATED) |
| Modelle | LM Studio local (qwen-vl via alicloud) |
| Alternativ | z.ai Vision |

---

## Server-Infrastruktur

```
┌──────────────┬────────────────┬──────────────────────────────────────┐
│ Server       │ IP             │ Funktion                             │
├──────────────┼────────────────┼──────────────────────────────────────┤
│ metamaus     │ 192.168.23.170 │ Gateway, Dashboard, PostgreSQL       │
│ Cronos       │ 192.168.23.80  │ 50 Cores, 22TB, Hyperopt             │
│ RedQueen     │ 192.168.23.101 │ LM Studio (DEPRECATED — nicht nutzen!)│
│ NAS          │ 192.168.23.104 │ Backups, Milestones                  │
│ DEMETER      │ 192.168.23.81  │ Home Assistant                       │
└──────────────┴────────────────┴──────────────────────────────────────┘
```

---

## Datenfluss

### WAL-Protokoll (Write-Ahead-Log)
```
User Input → Agent erkennt Learning → SOFORT schreiben → DANN antworten
                                    ↓
                            .learnings/*.md
                                    ↓
                          PostgreSQL learnings
                                    ↓
                     promotion_level >= 3 → memory (permanent)
```

### Cross-Agent Collaboration Flow
```
Rheingold findet URL → Pythia analysiert Screenshot/Bild
Athena braucht Daten → Hermes scraped
Dashboard-Fehler    → Apollon fixed
NAS-Alert          → Zerberus alarmiert + Orpheus triggert Backup
Iffy fragt Recherche → metamaus delegiert an Rheingold
```

### Memory Promotion Flow
```
1. Agent lernt etwas          →  learnings (temporär)
2. Heartbeat / regelmäßig     →  promotion_level++
3. promotion_level >= 3       →  memory (permanent)
4. promotion_level >= 5       →  SOUL.md / AGENTS.md (höchste Priorität)
```

### Self-Feeding Loop (neu in 2.1)
```
Browser-Crawler findet Seite
        ↓
Hermes scraped Inhalt
        ↓
Agent generiert eigene Tasks aus Ergebnissen
        ↓
Neue Tasks werden ausgeführt
        ↓
Ergebnisse → PostgreSQL → Dashboard
```

---

## PostgreSQL Schema

### Core Tables
```sql
-- Learnings (temporär)
CREATE TABLE learnings (
    id SERIAL PRIMARY KEY,
    agent TEXT NOT NULL,
    category TEXT,          -- 'ERR'|'LRN'|'COR'|'FEAT'
    content TEXT,
    promotion_level INT DEFAULT 0,
    status TEXT DEFAULT 'active',
    trigger_text TEXT,
    action_text TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Memory (permanent)
CREATE TABLE memory (
    id SERIAL PRIMARY KEY,
    key TEXT UNIQUE NOT NULL,
    value TEXT,
    category TEXT,
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Session State
CREATE TABLE session_state (
    id SERIAL PRIMARY KEY,
    session_id TEXT UNIQUE,
    context TEXT,
    updated_at TIMESTAMP DEFAULT NOW()
);
```

### Agent-spezifische Tables
```sql
-- Rheingold
rheingold_findings   -- Recherche-Ergebnisse
rheingold_crawl_queue -- Crawl-Warteschlange

-- Athena
athena_hyperopt_queue -- Hyperopt-Jobs
athena_trades         -- Trade-Log

-- Hestia
hestia_comments      -- YouTube-Kommentare

-- Zerberus
zerberus_tasks       -- Security-Tasks
network_assets       -- Netzwerk-Assets

-- Orpheus
vault                -- Secrets-Storage (verschlüsselt)

-- Dashboard
dashboard_logs       -- Gefilterte Logs
```

---

## Dashboard

| Port | Umgebung | URL |
|------|----------|-----|
| 5000 | PROD | http://192.168.23.170:5000 |
| 5001 | DEV | http://192.168.23.170:5001 |

### Dashboard R4 Features
- Logs gefiltert nach Agent
- Rheingold Live Widget
- 2-Spalten-Layout
- Echtzeit-Updates

---

## Installation

### 1. Voraussetzungen
```bash
# System
sudo apt update && sudo apt install -y python3 python3-pip postgresql git

# Python
pip3 install flask psycopg2-binary playwright
playwright install chromium
```

### 2. PostgreSQL
```bash
sudo -u postgres psql
CREATE DATABASE metamaus;
CREATE USER scraper WITH PASSWORD 'scraper';
GRANT ALL PRIVILEGES ON DATABASE metamaus TO scraper;
\c metamaus
\i schema.sql
```

### 3. SIAS installieren
```bash
git clone https://github.com/iggyswelt/SIAS
cd SIAS
```

### 4. SIAS-Dateien kopieren
```bash
cp SIAS/templates/SOUL.md ~/.openclaw/workspace/SOUL.md
cp SIAS/schema.sql ~/.openclaw/SIAS/schema.sql
```

### 5. Dashboard starten
```bash
cd /opt/dashboard
pip install -r requirements.txt
python3 app.py
# Oder als Service:
sudo systemctl restart metamaus-dashboard
```

### 6. Agent-Workspaces einrichten
```bash
mkdir -p ~/.openclaw/agents/{metamaus,apollon,athena,hermes,rheingold,zerberus,hestia,orpheus,pythia}
```

---

## Sicherheit

| Regel | Beschreibung |
|-------|-------------|
| **Secrets Policy** | NIEMALS Keys/Passwörter im Chat — immer in Vault/DB |
| **ADM-Workflow** | API-Keys nur über `adm-xchange.txt` Workflow |
| **RedQueen** | DEPRECATED — nicht mehr nutzen |
| **Backup** | Täglich auf NAS (192.168.23.104) |
| **WAL-Protokoll** | Änderungen werden VOR Ausführung geloggt |
| **openclaw.json** | READ-ONLY — Änderungen nur durch Iggy |

---

## Deployment

### GitHub
```
https://github.com/iggyswelt/SIAS
```

### Backup (Orpheus)
```bash
# Tägliches Backup auf NAS
rsync -avz /home/iggy/.openclaw/agents/ 192.168.23.104:/backups/agents/
# PostgreSQL Backup
pg_dump metamaus | gzip > /mnt/bigdata/backups/metamaus_$(date +%Y%m%d).sql.gz
```

---

## Version History

| Version | Datum | Beschreibung |
|---------|-------|-------------|
| 1.0.0 | 2026-02-18 | Initial Release — WAL-Protokoll, Markdown-Files |
| 2.0.0 | 2026-03-12 | B.A.S.E, PostgreSQL, 9 Agents |
| 2.1.0 | 2026-03-19 | Vision Stack, Browser Crawler, 9 Agents |
