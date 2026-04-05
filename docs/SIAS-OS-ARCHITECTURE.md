# SIAS-OS Architecture (v3.1)

## Overview
SIAS (Super Intelligent Agent System) is an event-driven multi-agent platform built on top of OpenClaw.

## Architecture
[ Telegram ] → [ OpenClaw Gateway ] → [ SIAS Core API ]
                                      ↓
                              [ Redis Event Bus ]
                              ↓        ↓        ↓
                          [Athene] [Hermes] [Zerberus]
                              ↓
                        [ PostgreSQL ]
                       (Source of Truth)

## Components
- **SIAS Core API** (FastAPI, Port 8000) — Brain
- **Redis Event Bus** (Cronos, Port 6379) — Communication
- **PostgreSQL** (metamaus, Port 5432) — Source of Truth
- **OpenClaw** — Runtime Shell (Telegram, Exec, Cron)

## Event Channels
- sias:arbitrage — Trading signals
- sias:security — Security checks
- sias:research — OSINT findings
- sias:tasks — Task management
- sias:alerts — Critical alerts

## Agents
| Agent | Role | Model |
|-------|------|-------|
| metamaus | Commander | Qwen 3.6 Plus |
| apollon | Code/Infra | Qwen 3.6 Plus |
| athene | Trading | GLM-5-Turbo |
| rheingold | OSINT/IFG | Qwen 3.6 Plus |
| hermes | Scraping | Qwen 3.5 9B (local) |
| zerberus | Security | MiniMax M2.7 |
| pythia | Audit/QA | Qwen3-VL-235B |
| hestia | YouTube | MiniMax M2.7 |
| orpheus | Backups/Docs | GLM-5-Turbo |

## Hardware
- **metamaus** (Pi/Server) — Gateway + API + DB
- **Cronos** (RTX 3060 12GB, 128GB RAM) — GPU + Redis + Docker
