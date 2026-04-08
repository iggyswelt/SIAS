# Orpheus — Heartbeat
Interval: 360m (Alle 6 Stunden)

## Routine-Check:
1. Prüfe: Ist das letzte Agent-Backup jünger als 24h?
2. Prüfe: Ist die Backup-Partition auf dem NAS ([SERVER_IP_NAS]) erreichbar?
3. Status-Meldung:
 - OK: Backups aktuell, GitHub synchron.
 - WARN: Backup > 24h alt oder NAS-Verbindung instabil.
 - CRITICAL: Backup-Partition voll oder Schreibfehler -> Telegram [TELEGRAM_ID].
