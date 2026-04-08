# Zerberus — Permanente Regeln
- User: iggy (Home: /home/iggy/)
- Telegram ID Iggy: [TELEGRAM_ID]
- NAS Backups laufen nachts — keine Last-Tests währenddessen.
- Freqtrade läuft 24/7 auf Cronos.

## Bekannte Threats (Blacklist)
- plain-crypto-js (npm Attack 31.03.2026)
- claw-code Source Map Leak (31.03.2026)
- Bedrohungs-Log: /home/iggy/.openclaw/logs/zerberus_threat.log

## V3 Regel
Wissen existiert nur in PostgreSQL (agent_knowledge).

## Zombie Task Killer (seit 05.04.2026)
- Script: /home/iggy/.openclaw/agents/zerberus/scripts/zombie_killer.sh
- Cron: alle 5 Minuten
- Regel: Task > 15 Min auf 'running' → status='failed'
- Log: /home/iggy/.openclaw/logs/zerberus_zombie.log
- Zerberus hat EXEC-Berechtigung für diesen einen Job
- Kein Agent darf länger als 15 Min hängen
