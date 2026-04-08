# metamaus — Memory

## System
- User: iggy (Home: /home/iggy/, NICHT /root/)
- Server: metamaus (192.168.23.170)
- GPU Server: Cronos (192.168.23.80, RTX 3060 12GB, 128GB RAM)
- Telegram ID Iggy: 737961726
- Dashboard PROD: 127.0.0.1:5000 | DEV: 127.0.0.1:5001 | V2: 127.0.0.1:5002
- NIEMALS host='127.0.0.1' nutzen!

## Gelerntes
- OpenClaw Memory System: 3-Tier (MEMORY.md + daily + vector)
- SIAS nutzt PostgreSQL als Source of Truth parallel
- Gateway wird langsam bei >100 Sessions → regelmäßig aufräumen
- Qwen 3.6 Plus hat preserve_thinking — reasoning: true aktivieren
- yfinance blockiert Flask Threads → nicht nutzen
- Promise.all crasht bei einem 404 → Promise.allSettled nutzen

## V3 Gesetze
- openclaw.json ist READ-ONLY.
- Wissen existiert NUR in PostgreSQL (agent_knowledge).
- Kein Task ist ohne Pythia-Audit offiziell beendet.

## Reporting System V3 (seit 05.04.2026)
- Heartbeat/Zombie/Mail-Watcher: NUR Dashboard + DB, NICHT im Chat
- Stündlicher Puls: DB category='hourly_pulse'
- 3 Briefings: 07:00, 12:15, 18:30 MESZ — kurz, max 10 Zeilen
- SOFORT melden: Fehler, Crashes, Security, Gateway Down
- NICHT melden: "alles OK", "keine Zombies", "200 OK"

## Himalaya Mail
- Account: abydon (NICHT abbydon!)
- Login: investigativ@abydon.com
- IMAP: mail.abydon.com:993 SSL
- SMTP: mail.abydon.com:465 SSL (NICHT 587!)
