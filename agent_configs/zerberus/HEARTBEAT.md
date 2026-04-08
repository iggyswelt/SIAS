# Zerberus — Heartbeat
Interval: 15m (Kritische Überwachung)

## Routine-Check:
1. Ping & Port-Check (5000, 5432, 8080) für:
 - metamaus (170), Cronos (80), RedQueen (101), NAS (104).
2. APT Check:
 grep "upgrade\|install" /var/log/dpkg.log | tail -3
3. Security Intelligence:
 bash /home/iggy/.openclaw/agents/zerberus/scripts/threat_feed.sh
4. Alert-Level:
 - OK: Alles erreichbar.
 - CRITICAL: Gateway oder DB down -> SOFORT TELEGRAM [TELEGRAM_ID].
