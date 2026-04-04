# SIAS Architecture v2.1

## Overview
Self-Improving Agent System mit 8 spezialisierten Agents.

## System Architecture

```
┌─────────────────────────────────────────────┐
│           metamaus (Teamleader)           │
│         [SERVER_IP_METAMAUS] (Server)          │
└─────────────┬───────────────────────────────┘
              │
    ┌────────┼────────┬────────┬────────┐
    ▼        ▼        ▼        ▼        ▼
┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐
│Apollo│ │Athena│ │Hermes│ │Rheing│ │Zerber│
│ Code │ │Trade │ │Scrap │ │ IFG  │ │ Sec  │
└──────┘ └──────┘ └──────┘ └──────┘ └──────┘
    │        │        │        │        │
    ▼        ▼        ▼        ▼        ▼
┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐
│ Hestia│ │Orphus│ │Pythia│ │      │ │      │
│  YT   │ │Backp │ │Vision│ │      │ │      │
└──────┘ └──────┘ └──────┘ └──────┘ └──────┘
```

## Infrastructure

### Servers
| Server | IP | Hardware | Role |
|--------|-----|----------|------|
| metamaus | [SERVER_IP_METAMAUS] | 8GB RAM | Dashboard, DB, Gateway |
| Cronos | [SERVER_IP_CRONOS] | 50 Cores, 22TB | Hyperopt, Ollama |
| RedQueen | [SERVER_IP_REDQUEEN] | RTX 2080 Ti | LM Studio, Pythia |

### Database
- PostgreSQL 15
- Tables: learnings, memory, rheingold_*, athena_*, agent_*, agent_templates

### Model Providers
| Provider | Endpoint | Modelle |
|----------|-----------|----------|
| minimax-direct | api.minimax.chat | M2.5, M2.5-highspeed |
| openrouter | openrouter.ai | qwen3-coder:free |
| alicloud | dashscope.aliyuncs.com | qwen3-max |
| cronos-ollama | [SERVER_IP_CRONOS]:11434 | qwen3.5:2b |
| redqueen | [SERVER_IP_REDQUEEN]:1234 | LM Studio |

## Agent Responsibilities

| Agent | Focus | Tools |
|-------|-------|-------|
| metamaus | Coordination | Delegation |
| Apollon | Code | Python, Bash, SQL |
| Athena | Trading | Freqtrade, Backtest |
| Hermes | Scraping | Crawl4AI |
| Rheingold | IFG | Recherche, DB |
| Zerberus | Security | Firewall, SSH |
| Hestia | YouTube | Comments, Analytics |
| Orpheus | Backup | Vault, PKI |
| Pythia | Vision | LM Studio, OCR |

## Workflow

1. User sends task to metamaus
2. metamaus analyzes and delegates to appropriate agent
3. Agent executes and reports back
4. Results stored in PostgreSQL
5. metamaus summarizes for user
