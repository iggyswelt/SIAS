# SIAS — Super Intelligent Agent System

**DE:** SIAS ist ein event-gesteuertes Multi-Agent-System, gebaut auf OpenClaw. Agenten kommunizieren über einen Redis Event Bus, PostgreSQL ist die einzige Source of Truth.

**EN:** SIAS is an event-driven multi-agent platform built on top of OpenClaw. Agents communicate via a Redis Event Bus. PostgreSQL is the single source of truth.

## Architecture
```
[ OpenClaw Gateway ] → [ SIAS Core API (FastAPI :8000) ]
                        ↓
                  [ Redis Event Bus ]
                    ↓    ↓    ↓
                [Agent A] [Agent B] [Agent C]
                    ↓
                [ PostgreSQL (Source of Truth) ]
```

## Components
- **sias_core/** — FastAPI API + Worker Services + Event Bus
- **agents/example/** — Example agent configuration

## Stack
- OpenClaw 2026.4.x (Runtime Shell)
- FastAPI + Redis + PostgreSQL
- Python 3.11+

## Setup
See `sias_core/README.md` for setup instructions.
