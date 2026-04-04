# SIAS V3 — Smart Infrastructure & Agent System

## 🏗️ Architecture Overview / Architektur-Übersicht

SIAS V3 is a multi-agent system running on OpenClaw, coordinated via PostgreSQL and Telegram.
SIAS V3 ist ein Multi-Agenten-System auf OpenClaw-Basis, koordiniert über PostgreSQL und Telegram.

### Agent Hierarchy / Agenten-Hierarchie

| Agent | Role / Rolle | Server | Description |
|-------|-------------|--------|-------------|
| **metamaus** | Team Leader & Strategy | [SERVER_IP_METAMAUS] | Gateway, PostgreSQL, coordination, heartbeat master |
| **pythia** | Data Audit & Quality | [SERVER_IP_METAMAUS] | Validates data integrity, PostgreSQL audits, compliance |
| **orpheus** | Backup & GitHub | [SERVER_IP_METAMAUS] | NAS sync, milestones, version control, vault management |
| **apollon** | Development & Code | [SERVER_IP_METAMAUS] | Script authoring, code review, deployment automation |
| **hermes** | Research & Web | [SERVER_IP_METAMAUS] | Web scraping, research, demo/funding scouting (NRW) |
| **hestia** | Content & Social | [SERVER_IP_METAMAUS] | YouTube, social media, content pipeline |
| **zerberus** | Security & Infrastructure | [SERVER_IP_METAMAUS] | Network monitoring, security scans, health checks |
| **athene** | Trading & Finance | [SERVER_IP_METAMAUS] | Autonomous trading, arbitrage, market analysis |

### Communication Flow / Kommunikationsfluss

```
metamaus (Task Assignment)
    → Agent (Execution)
        → pythia (Audit & Validation)
            → metamaus (Completion Report)
                → Telegram (User Notification)
```

## 💓 Heartbeat System

Every agent runs a periodic heartbeat check:
- Gateway status verification
- PostgreSQL connectivity test
- Service health (Freqtrade, Ollama, etc.)
- Results logged to PostgreSQL `agent_heartbeat` table
- Failures trigger immediate Telegram alerts

## 🗄️ PostgreSQL Schema Overview

Key tables:
- `agent_heartbeat` — Agent health status & timestamps
- `agent_knowledge` — Shared knowledge base between agents
- `agent_tasks` — Task tracking & delegation
- `session_logs` — Communication audit trail

## 🚀 Setup Guide / Einrichtung

### Prerequisites / Voraussetzungen
- Node.js v22+
- PostgreSQL 16+
- OpenClaw CLI (`npm install -g openclaw`)
- Telegram Bot Token

### Installation
```bash
# Clone repository
git clone <repo-url> ~/.openclaw
cd ~/.openclaw

# Configure environment
cp .env.example .env
# Edit .env with your values (DB credentials, API keys, etc.)

# Initialize database
psql -U postgres -f agora/scripts/init_db.sql

# Start gateway
openclaw gateway start
```

### Agent Configuration
Each agent lives in `agents/<name>/` with:
- `SOUL.md` — Personality & behavior rules
- `IDENTITY.md` — Role definition
- `TOOLS.md` — Available tools & scripts
- `USER.md` — User context
- `AGENTS.md` — Team relationships

## 🔒 Security Notes

- **Never commit** API keys, passwords, or SSH credentials
- Sensitive data is replaced with placeholders: `[REDACTED]`, `[API_KEY_PLACEHOLDER]`, `[TELEGRAM_ID]`
- Server IPs are obfuscated: `[SERVER_IP_METAMAUS]`, `[SERVER_IP_CRONOS]`, etc.
- See `.gitignore` for excluded paths

---

*SIAS V3 — Built with OpenClaw | Last updated: 2026-04-05*
