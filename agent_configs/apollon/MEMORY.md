# Apollon — Permanente Regeln & Wissen

## Systeme
- metamaus Server: [SERVER_IP_METAMAUS] (PostgreSQL, Flask Dashboard, OpenClaw)
- Cronos: [SERVER_IP_CRONOS] (Freqtrade, Hyperopt, 50 Cores)
- RedQueen: [SERVER_IP_REDQUEEN] (RTX 2080 Ti, LM Studio)
- SSH Cronos: ssh -i [SSH_KEY_PATH] iggy@[SERVER_IP_CRONOS]
- DB: psql -h 127.0.0.1 -U scraper -d metamaus

## Regeln & SIAS V3
- KEINE LOKALEN MD-FILES FÜR WISSEN: "Lessons Learned" gehen als JSONB in die PostgreSQL Tabelle agent_knowledge.
- openclaw.json ist READ-ONLY — NIEMALS editieren
- MiniMax-M2.1 ist VERBOTEN
- Immer Backup vor Änderungen
- PROD (Port 5000) nie direkt patchen — immer DEV (5001) zuerst
- Scripts ablegen unter: /home/iggy/.openclaw/agora/scripts/
