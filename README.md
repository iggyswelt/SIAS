# SIAS — Self-Improving Agent System
### Version 2.1 | MetaMaus Implementation

## Was ist SIAS?
SIAS ist ein Framework für autonome, selbstverbessernde 
AI-Agenten auf eigener Hardware.

## Agent Roster
| Agent | Rolle | Status |
|-------|-------|--------|
| metamaus | Teamleader / Orchestrator | aktiv |
| athena | Trading / Freqtrade Backtest | aktiv |
| rheingold | Investigativ / IFG / NGO Research | aktiv |
| hermes | News Scraping / Demo Tracking | aktiv |
| hestia | YouTube Community Management | aktiv |
| zerberus | Netzwerk / Security / Tasks | aktiv |
| orpheus | PKI / Backup / Infrastructure | aktiv |

## Stack
- Agent Layer: OpenClaw
- Memory Layer: PostgreSQL + Daily JSONL
- Crawler Layer: crawl4ai + tavily-search
- Security Layer: Nitrokey HSM + Vault
- Dashboard: Flask

## Memory Architecture (SIAS 2.3)
Telegram/Chat → Daily Summary (23:00 Cron) → agent_logs (PostgreSQL) → MEMORY.md → OpenClaw Compaction (auto, 80k tokens) → Monthly Archive (PostgreSQL)

## Lizenz
MIT — Build on it!
