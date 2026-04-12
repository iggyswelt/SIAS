# SIAS Architecture

## Overview

SIAS follows an **event-driven microservice** pattern. All inter-agent communication flows through Redis Pub/Sub. PostgreSQL is the single source of truth for state, knowledge, and audit trails.

## Core Components

### 1. SIAS Core API (FastAPI)
- REST gateway for external integrations
- Agent registration & health checks
- Event routing & transformation
- Port: `8000` (configurable)

### 2. Redis Event Bus
- Channel-based Pub/Sub for agent communication
- Event types: `task.assign`, `task.complete`, `alert`, `heartbeat`, `audit.log`
- Persistent queues for critical events

### 3. PostgreSQL Database
- `agent_knowledge` — Agent state & learned data
- `audit_trail` — Pythia validation logs
- `task_queue` — Pending & completed tasks
- `osint_cache` — Rheingold research results

### 4. Worker Services
| Worker | Language | Purpose |
|--------|----------|---------|
| `worker_hermes.py` | Python | Web scraping pipeline |
| `worker_rheingold.py` | Python | OSINT research engine |
| `worker_hestia.py` | Python | YouTube transcription |

### 5. Inter-Agent Bridge
- Direct agent-to-agent communication layer
- Event chains: e.g., `metamaus → rheingold → pythia → orpheus`
- Dreaming mode: offline reflection & self-improvement

## Data Flow

```
[Trigger] → Redis Event → [Agent picks up] → Process → [Redis Event] → [Next Agent]
                 ↓
           [PostgreSQL] ← Audit (Pythia) ← Backup (Orpheus)
```

## Event Chain Example

1. **metamaus** assigns OSINT task → Redis `task.assign`
2. **rheingold** picks up task → researches → Redis `task.complete`
3. **pythia** validates results → Redis `audit.log`
4. **orpheus** backs up findings → PostgreSQL

## Deployment

All components run on a single Ubuntu host. Services managed via systemd. Monitoring by zerberus.
