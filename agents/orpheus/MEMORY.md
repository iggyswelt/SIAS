# Orpheus — Permanente Regeln
- NAS: [SERVER_IP_NAS] (Mount: /mnt/nas/)
- Backup-Zyklus: Täglich nach PROD-Deploy oder alle 24h.
- Milestone-Backup: Vor jedem größeren Umbau (wie SIAS V3 Migration).
- GitHub-Token: Muss sicher aus dem Vault/ADM-XCHANGE geladen werden.
- Telegram ID Iggy: [TELEGRAM_ID]

## V3 Regel
Wissen existiert nur in PostgreSQL (agent_knowledge). Lokale MD-Dateien dienen nur der statischen Konfiguration.
