# SIAS Agents

## Overview

SIAS consists of 10 specialized agents, each with a distinct role. All agents run on OpenClaw and communicate via the Redis Event Bus.

---

## Agent Roster

### metamaus 🐭 — Commander
- **Role:** Team Leader & Strategist
- **Tasks:** Coordination, task distribution, decision-making
- **Interface:** Telegram (primary), GitHub

### apollon 🏛️ — Code
- **Role:** Developer & CI/CD Engineer
- **Tasks:** Code development, deployment scripts, automation
- **Tools:** Python, Bash, Node.js

### athene 🦉 — Trading
- **Role:** Market Analyst
- **Tasks:** Portfolio strategy, market research, risk assessment
- **Data:** Yahoo Finance, market APIs

### rheingold 💎 — OSINT
- **Role:** Open Source Intelligence
- **Tasks:** Deep research, IFG requests, NGO analysis
- **Standalone:** Can run independently with own DB

### pythia 🔮 — Audit
- **Role:** Data Integrity & Compliance
- **Tasks:** Validates agent outputs, audit trails, anomaly detection
- **Validates:** All agent data flows

### hermes ✉️ — Scraping
- **Role:** Web Crawler & Data Extractor
- **Tasks:** Website scraping, data pipeline, content extraction
- **Worker:** `worker_hermes.py`

### hestia 🏠 — YouTube
- **Role:** Video Intelligence
- **Tasks:** Transcription, content analysis, channel monitoring
- **Worker:** `worker_hestia.py`

### orpheus 🎭 — Backup & Docs
- **Role:** Data Safety & Documentation
- **Tasks:** Backups, GitHub releases, NAS sync, documentation
- **Rule:** Never delete without 3x confirmation

### zerberus 🐕 — Security
- **Role:** Infrastructure Security
- **Tasks:** Firewall monitoring, SSH hardening, intrusion detection
- **Partner:** Works closely with orpheus

### arthemis 🏹 — Architect
- **Role:** QA & System Design
- **Tasks:** Architecture review, QA testing, dreaming mode
- **Added:** v3.2

---

## Communication Matrix

| From → To | Channel | Event Type |
|-----------|---------|------------|
| metamaus → all | Redis | `task.assign` |
| rheingold → pythia | Redis | `task.complete` |
| pythia → orpheus | Redis | `audit.log` |
| zerberus → metamaus | Redis | `alert` |
| arthemis → all | Redis | `qa.report` |
