# SIAS v2.0 — Semantic Intelligence Agent System
*Milestone Documentation | Updated: 11.03.2026*

---

## What is SIAS?

SIAS is the memory layer of OpenClaw — the system that gives a KIAgent persistent memory instead of starting fresh every conversation.

**Core Idea:** Knowledge belongs in a database — not in files.

---

## The 3 Layers of SIAS v2.0

### Layer 1: Knowledge Layer (PostgreSQL)
```sql
INSERT INTO agent_knowledge (key, value, category, learned_at)
VALUES ('what_learned', 'content', 'category', NOW())
ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value;
```

### Layer 2: B.A.S.E (Backup Agent Semantic Environment)
- TPM2 encryption via Clevis
- Dual protection: .clevis + .backup
- Retention: 7 days

### Layer 3: Orpheus Monitor
Daily system guardian (06:00)

---

## B.A.S.E Structure
```
/home/iggy/backups/
├── orpheus/       # SQL dumps hourly
│   └── db/       # TPM2-encrypted
├── dashboard/     # On deploy
├── freqtrade/    # Trading Config
└── openclaw_memory/
```

## Orpheus Monitor Checks
- Cron duplications
- Backup count (~24/day)
- Hardware security (SoloKey + TPM2)
- Stray backups
- GitHub backup age
- 0.0.0.0 bindings

---

*More info: See BOOTSTRAP.md + MEMORY.md*
