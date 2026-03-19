# SIAS v2.1.0 — Release Notes

*Released: 2026-03-19*

---

## 🎉 What's New in v2.1.0

This is the biggest SIAS release yet — bringing vision capabilities, autonomous web crawling, and a fully operational multi-agent team to production.

---

### 🆕 Major New Features

#### 🌐 Browser-Crawler with Playwright
- Full JavaScript rendering support for JS-heavy websites
- Automated crawling pipelines with queue management
- Crawl results stored directly in PostgreSQL (`rheingold_crawl_queue`)

#### 🔄 Self-Feeding Loop
- Crawler generates its own tasks from results
- Agents no longer wait passively — they proactively generate work
- Zero idle phases: continuous improvement cycle

#### 👁️ Vision Stack
- **Pythia** agent: image analysis, screenshot interpretation
- Integration with `z.ai Vision` and `alicloud/qwen-vl`
- Cross-agent pipeline: Rheingold finds → Pythia analyzes

#### 📊 Dashboard R4
- Filtered log views by agent
- **Rheingold Live Widget** — real-time crawl status
- 2-column layout for better overview
- Flask-based, runs on port 5000 (PROD) / 5001 (DEV)

#### 🚀 Hyperopt Marathon
- **Cronos** server (50 cores, 22TB HDD at `/mnt/bigdata`)
- **40 parallel jobs** — full speed trading strategy optimization
- Automated job queue in `athena_hyperopt_queue` table

#### 🏠 DEMETER — Home Assistant Integration
- New server at 192.168.23.81
- Smart home monitoring via Home Assistant
- IoT data feeds into agent decision-making

#### 🔐 ADM-Workflow (API-Key Exchange)
- `adm-xchange.txt` workflow for secure API key rotation
- Permanent: API keys are no longer stored in memory or chat
- Vault table in PostgreSQL for encrypted storage

---

### 🛠️ Architecture Changes

#### 9 Agents Now Operational

| Agent | Emoji | Status | Server |
|-------|-------|--------|--------|
| metamaus | 🐭 | ✅ Active | metamaus |
| Apollon | 🛠️ | ✅ Active | metamaus |
| Athena | 📈 | ✅ Active | Cronos |
| Hermes | 📡 | ✅ Active | metamaus |
| Rheingold | 🦅 | ✅ Active | metamaus |
| Zerberus | 🛡️ | ✅ Active | metamaus |
| Hestia | 💬 | ✅ Active | metamaus |
| Orpheus | 🎵 | ✅ Active | metamaus |
| Pythia | 👁️ | ✅ Active | RedQueen/alicloud |

#### New PostgreSQL Tables
- `rheingold_crawl_queue` — crawl job queue
- `athena_hyperopt_queue` — parallel hyperopt jobs
- `vault` — encrypted secrets storage
- `network_assets` — Zerberus asset tracking
- `dashboard_logs` — filtered dashboard logs

#### ⚠️ Breaking Changes

> **RedQueen (192.168.23.101) is DEPRECATED**
>
> Do NOT use RedQueen for new tasks. Migrate to alicloud/qwen-vl or z.ai Vision. All Pythia vision tasks should use the cloud endpoints.

---

### 📊 Technical Specs

| Component | Version/Spec |
|-----------|-------------|
| OpenClaw | 2026.2.17 |
| PostgreSQL | 16 |
| Primary Model | MiniMax-M2.5-highspeed |
| Cronos | 50 cores, 22TB, 40 parallel jobs |
| Dashboard | Flask, Python 3 |
| Crawler | Playwright + httpx |
| Vision | alicloud/qwen-vl + z.ai Vision |
| Backup | NAS 192.168.23.104 |

---

### 📁 File Structure

```
SIAS/
├── ARCHITECTURE.md          ← NEW in v2.1: Full system architecture
├── CHANGELOG.md             ← Version history
├── README.md                ← Full documentation
├── RELEASE_NOTES_v2.1.0.md  ← These notes
├── SIAS_v2.1_DE.md          ← Milestone documentation (DE)
├── BASE_DE.md               ← Base template (DE)
├── BASE_EN.md               ← Base template (EN)
├── SKILLS.md                ← Agent skill definitions
├── schema.sql               ← PostgreSQL schema
└── templates/
    └── SOUL.md              ← Agent identity template
```

---

### 🔗 Links

| Resource | URL |
|----------|-----|
| GitHub Repo | https://github.com/iggyswelt/SIAS |
| YouTube | https://youtube.com/@iggyswelt |
| OpenClaw | https://openclaw.dev |
| Dashboard PROD | http://192.168.23.170:5000 |
| Dashboard DEV | http://192.168.23.170:5001 |

---

### 🗺️ Roadmap

| Version | Target | Status |
|---------|--------|--------|
| 1.0.0 | WAL-Protokoll, Markdown Memory | ✅ Done |
| 2.0.0 | PostgreSQL, 9 Agents, B.A.S.E | ✅ Done |
| **2.1.0** | **Vision, Browser Crawler, Self-Feeding** | **✅ Done** |
| 2.2 | MCP Integration | 🔜 Next |
| 3.0 | Local LLM Support (RTX 3060) | 📋 Planned |
| Plugin | Native OpenClaw SIAS Plugin | 📋 Planned |

---

## Migration from v2.0.0

```bash
# 1. Pull latest
git pull origin main

# 2. Update schema
psql -U scraper -d metamaus -f schema.sql

# 3. Restart dashboard
sudo systemctl restart metamaus-dashboard

# 4. Verify agents
openclaw agents list
```

---

## Credits

Developed by [@iggyswelt](https://youtube.com/@iggyswelt)  
Built with OpenClaw, MiniMax-M2.5, and real production workloads.

**⭐ Star the repo if SIAS helps you build better agents!**
