# B.A.S.E — Backup Agent Semantic Environment
*Teil von SIAS v2.0 | 12.03.2026*

## Was ist B.A.S.E?

B.A.S.E ist der Backup-Layer von SIAS v2.0.
Ein zentrales Backup-Script. TPM2-Verschlüsselung. Automatische Überwachung.

## Die 3 Regeln

1. Ein Backup-Script — nur encrypt-backup.sh macht pg_dump
2. TPM2-Verschlüsselung — jedes Backup doppelt (.clevis + .backup)
3. 7-Tage-Retention — automatisch via cron

## Verzeichnisstruktur
```
~/backups/
├── orpheus/       # SQL-Dumps stündlich
│   └── db/       # TPM2-verschlüsselt
├── dashboard/     # Bei Deploy
├── freqtrade/    # Trading Config
└── openclaw_memory/
```

## Orpheus Monitor Checks
- Backup-Count (~24/Tag)
- Leere Files (0 Byte → löschen)
- Stray Backups (außerhalb ~/backups/)
- Große alte Files (>50MB, >7 Tage)
- GitHub Backup Alter (>2 Tage)
- Hardware: SoloKey + TPM2 + NitroKey HSM
- PKI Zertifikate

## Lessons Learned

> "backup_demo_scraper.sh machte pg_dump auf eine DB die nicht mehr existierte — seit Wochen unbemerkt."
— Zombie-Script Cleanup, 11.03.2026

> "Hermes lief doppelt: System Crontab + OpenClaw Cron + internes pg_dump im Script = 59 Backups an einem Tag."
— Hermes Cron-Bug, 11.03.2026

## Roadmap
- [ ] TPM2 + SoloKey Zwei-Faktor
- [ ] NAS-Sync via rclone
- [ ] Orpheus signiert Backups via PKI
- [ ] Cronos Server Integration

---

*Dokumentiert von Orpheus*
*SIAS v2.0 | github.com/iggyswelt/SIAS*
