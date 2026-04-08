# Apollon — Bootstrap

## System-Zugriff
- **Zentrale:** metamaus Gateway ([SERVER_IP_METAMAUS])
- **Rechenkraft:** Cronos ([SERVER_IP_CRONOS]) — via SSH Key.
- **Datenbank:** PostgreSQL `metamaus` (Vollzugriff auf alle Tabellen).

## Arbeitsbereiche
- **Scripts:** `/home/iggy/.openclaw/agora/scripts/`
- **Agent-Data:** `/home/iggy/.openclaw/agents/apollon/`
- **Dashboard:** `/opt/dashboard/` (PROD, Port 5000) & `/opt/dashboard-dev/` (DEV, Port:5001).

## ADM-XCHANGE PROTOKOLL
Ich bin der Hauptnutzer des ADM-XCHANGE Kanals. Wenn ich Passwörter oder API-Keys benötige:
1. Lesen von `/home/iggy/.openclaw/adm/adm-xchange.txt`.
2. Sofortiges Leeren der Datei nach dem Einlesen.
3. Niemals Keys im Chat oder in Logs im Klartext speichern.

## ABSOLUTE VERBOTE
- `openclaw.json` editieren (Nur Iggy darf das).
- Ohne Backup-Check an PROD-Systemen arbeiten.
- Strategische Aufgaben ohne metamaus-Zuweisung starten.