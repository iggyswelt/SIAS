# B.A.S.E — Backup Agent Semantic Environment
*Part of SIAS v2.0 | March 12, 2026*

## What is B.A.S.E?

B.A.S.E is the backup layer of SIAS v2.0.
One central backup script. TPM2 encryption. Automatic monitoring.

## The 3 Rules

1. One backup script — only encrypt-backup.sh runs pg_dump
2. TPM2 encryption — every backup double-encrypted (.clevis + .backup)
3. 7-day retention — automatic via cron

## Directory Structure
```
~/backups/
├── orpheus/       # SQL dumps hourly
│   └── db/       # TPM2 encrypted
├── dashboard/     # On deploy
├── freqtrade/    # Trading config
└── openclaw_memory/
```

## Orpheus Monitor Checks
- Backup count (~24/day)
- Empty files (0 byte → delete)
- Stray backups (outside ~/backups/)
- Large old files (>50MB, >7 days)
- GitHub backup age (>2 days)
- Hardware: SoloKey + TPM2 + NitroKey HSM
- PKI certificates

## Lessons Learned

> "backup_demo_scraper.sh did pg_dump on a DB that no longer existed — unnoticed for weeks."
— Zombie Script Cleanup, 11.03.2026

> "Hermes ran double: System Crontab + OpenClaw Cron + internal pg_dump = 59 backups in one day."
— Hermes Cron Bug, 11.03.2026

## Roadmap
- [ ] TPM2 + SoloKey two-factor
- [ ] NAS sync via rclone
- [ ] Orpheus signs backups via PKI
- [ ] Cronos Server integration

---

*Documented by Orpheus*
*SIAS v2.0 | github.com/iggyswelt/SIAS*
