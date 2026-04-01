# Apollon — Permanente Regeln & Wissen

## Systeme
- metamaus Server: 192.168.23.170 (PostgreSQL, Flask Dashboard, OpenClaw)
- Cronos: 192.168.23.80 (Freqtrade, Hyperopt, 50 Cores)
- RedQueen: 192.168.23.101 (RTX 2080 Ti, LM Studio)
- SSH Cronos: ssh -i /home/iggy/.ssh/cronos_key iggy@192.168.23.80
- DB: psql -h 127.0.0.1 -U scraper -d metamaus

## Regeln
- openclaw.json ist READ-ONLY — NIEMALS editieren
- MiniMax-M2.1 ist VERBOTEN
- Immer Backup vor Änderungen
- PROD (Port 5000) nie direkt patchen — immer DEV (5001) zuerst
- Scripts ablegen unter: /home/iggy/.openclaw/agora/scripts/
