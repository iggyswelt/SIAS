# SIAS v2.0 — Semantic Intelligence Agent System
*Meilenstein-Dokumentation | Stand: 11.03.2026*

---

## Was ist SIAS?

SIAS ist der Memory-Layer von OpenClaw — das System das einem KI-Agenten
echtes, persistentes Gedächtnis gibt.

**Kernidee:** Wissen gehört in eine Datenbank — nicht in Dateien.

---

## Die 3 Schichten von SIAS v2.0

### Schicht 1: Knowledge Layer (PostgreSQL)
```sql
INSERT INTO agent_knowledge (key, value, category, learned_at)
VALUES ('was_gelernt', 'inhalt', 'kategorie', NOW())
ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value;
```

### Schicht 2: B.A.S.E (Backup Agent Semantic Environment)
- TPM2-Verschlüsselung via Clevis
- Doppelte Absicherung: .clevis + .backup
- Retention: 7 Tage

### Schicht 3: Orpheus Monitor
Täglicher Systemwächter (06:00)

---

## B.A.S.E Struktur
```
/home/iggy/backups/
├── orpheus/       # SQL-Dumps stündlich
│   └── db/       # TPM2-verschlüsselt
├── dashboard/     # Bei Deploy
├── freqtrade/    # Trading Config
└── openclaw_memory/
```

## Orpheus Monitor Checks
- Cron-Doppelungen
- Backup-Count (~24/Tag)
- Hardware-Security (SoloKey + TPM2)
- Stray Backups
- GitHub Backup Alter
- 0.0.0.0 Bindings

---

*Mehr Info: Siehe BOOTSTRAP.md + MEMORY.md*
