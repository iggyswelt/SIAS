# Pythia — Tools

## Server
- Cronos: 192.168.23.80 (RTX 3060)
- RedQueen: [SERVER_IP_REDQUEEN]:1234 (LM Studio)

## Database (KRITISCH!)
- PostgreSQL: psql -h 127.0.0.1 -U scraper -d metamaus
- User IMMER: scraper (NICHT metamaus, NICHT postgres)

## Modelle & Audit-Befehle
- Primary: qwen-vl-plus
- DB-Audit: UPDATE agent_knowledge SET verified_by = 'pythia', verified_at = NOW() WHERE id = ...
- Log-Read: cat /home/iggy/.openclaw/logs/[agent].log

## Verboten
- nvidia/nemotron für Fakten-Checks (halluziniert zu stark).
- Selbst Code schreiben (Delegation an Apollon für Test-Scripte).
