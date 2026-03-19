# SIAS v2.1 — Semantic Intelligence Agent System
*Meilenstein-Dokumentation | Stand: 19.03.2026*

---

## Was ist SIAS?

SIAS ist das native Memory-Framework für OpenClaw-Agenten. Es kombiniert:

- **PostgreSQL** als zentrale Wissensdatenbank
- **8 spezialisierte Agents** mit autonomer Operation
- **Self-Feeding Loops** — Agents generieren eigene Tasks
- **Promoted Memory** — temporäres Wissen → dauerhaftes Wissen
- **WAL-Protokoll** — strukturierte Fehlerprotokollierung
- **Cross-Agent Collaboration** — Agents helfen sich gegenseitig

---

## 🇩🇪 Deutsch

### Die 3 Schichten

```
┌─────────────────────────────────────────┐
│  METAMAUS — Teamleader & Architekt     │  ← Koordiniert alle Agents
├─────────────────────────────────────────┤
│  APOLLON  ATHENA  HERMES  RHEINGOLD   │  ← Spezialisten
│  ZERBERUS HESTIA  ORPHEUS  PYTHIA     │
├─────────────────────────────────────────┤
│  PostgreSQL — Zentrale Datenbank         │  ← ALLES hier
│  metamaus DB, scraper User              │
└─────────────────────────────────────────┘
```

### PostgreSQL Schema

```sql
-- Learnings (temporär)
CREATE TABLE learnings (
    id SERIAL PRIMARY KEY,
    agent TEXT,
    category TEXT,
    content TEXT,
    promotion_level INT DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Memory (permanent)
CREATE TABLE memory (
    id SERIAL PRIMARY KEY,
    key TEXT UNIQUE,
    value TEXT,
    category TEXT,
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Agent-spezifische Tabellen
rheingold_findings, rheingold_crawl_queue
athena_hyperopt_queue, athena_trades
hestia_comments, zerberus_tasks
network_assets, vault
```

---

## 🏗️ Architektur

### Agents

| Agent | Emoji | Verantwortung | Server |
|-------|-------|--------------|--------|
| **Apollon** | 🛠️ | Code, Scripts, Dashboard | metamaus |
| **Athena** | 📈 | Trading, Hyperopt Marathon | Cronos |
| **Hermes** | 📡 | Demo-Scraper, Crawling | metamaus |
| **Rheingold** | 🦅 | IFG-Anfragen, Förder-Recherche | metamaus |
| **Zerberus** | 🛡️ | Security, Netzwerk-Monitoring | metamaus |
| **Hestia** | 💬 | YouTube, Comments | metamaus |
| **Orpheus** | 🎵 | Backups, PKI, Vault | metamaus/NAS |
| **Pythia** | 👁️ | Vision, Bildanalyse | metamaus |
| **metamaus** | 🐭 | Teamleader & Architekt | metamaus |

### Server

| Server | IP | Funktion |
|--------|-----|---------|
| **metamaus** | 192.168.23.170 | Dashboard, PostgreSQL, Flask |
| **Cronos** | 192.168.23.80 | 50 Cores, 22TB, Hyperopt |
| **RedQueen** | 192.168.23.101 | LM Studio (DEPRECATED) |
| **NAS** | 192.168.23.104 | Backups, Milestones |
| **DEMETER** | 192.168.23.81 | Home Assistant (neu!) |

---

## ⚡ Features 2.1

### Neu in 2.1

- ✅ **Browser-Crawler** mit Playwright (JS-heavy Seiten)
- ✅ **Self-Feeding Loop** — Crawler generiert eigene Tasks
- ✅ **Dashboard R4** — Logs gefiltert, 2-Spalten, Rheingold Live Widget
- ✅ **Hyperopt Marathon** auf 22TB HDD (/mnt/bigdata), 40 parallel jobs
- ✅ **Vision Stack** — z.ai Vision + alicloud/qwen-vl
- ✅ **DEMETER** — Home Assistant Server integriert
- ✅ **Team Mindset** — proaktiv, keine Leerlauf-Phasen
- ✅ **ADM-Workflow** — API-Key-Austausch permanentisiert

### Memory Promotion Flow

```
1. Agent lernt etwas → learnings (temporär)
2. Heartbeat-Check → promotion_level++
3. Ab level 3 → memory (permanent)
4. Ab level 5 → SOUL.md oder AGENTS.md
```

### Cross-Agent Collaboration

```
Rheingold findet Seite → Pythia analysiert Screenshot
Athena braucht Daten → Hermes crawled
Dashboard kaputt → Apollon fixed
NAS voll → Zerberus alarmiert
```

---

## 🚀 Installation

### 1. PostgreSQL Setup

```sql
CREATE DATABASE metamaus;
CREATE USER scraper WITH PASSWORD 'scraper';
GRANT ALL PRIVILEGES ON DATABASE metamaus TO scraper;
```

### 2. Dashboard starten

```bash
cd /opt/dashboard
pip install -r requirements.txt
python3 app.py
# PROD: sudo systemctl restart metamaus-dashboard
```

---

## 📊 Dashboard

| Port | Umgebung | URL |
|------|----------|-----|
| 5000 | PROD | http://192.168.23.170:5000 |
| 5001 | DEV | http://192.168.23.170:5001 |

---

## 🔑 Sicherheit

- **Secrets** NIEMALS im Chat — immer in Vault/DB
- **API-Keys** nur über `adm-xchange.txt` Workflow
- **Backup** täglich auf NAS
- **RedQueen** — NIE MEHR NUTZEN!

---

## 📁 File-Struktur

```
~/.openclaw/
├── agents/
│   ├── metamaus/     # Teamleader
│   ├── apollon/      # Code & Dashboard
│   ├── athena/       # Trading
│   ├── hermes/       # Crawling
│   ├── rheingold/    # IFG
│   ├── zerberus/     # Security
│   ├── hestia/       # YouTube
│   ├── orpheus/      # Backups
│   └── pythia/       # Vision
├── rheingold_data/   # Crawler-Scripts
└── dashboard/        # Flask Dashboard
```

---

## 🔗 Links

- **GitHub:** https://github.com/iggyswelt/SIAS
- **YouTube:** https://youtube.com/@iggyswelt
- **OpenClaw:** https://openclaw.dev
- **Dashboard:** http://192.168.23.170:5000
