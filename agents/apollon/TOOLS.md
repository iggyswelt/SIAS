# Apollon — Tools

## Database
psql -h 127.0.0.1 -U scraper -d metamaus

## Server
- metamaus: [SERVER_IP_METAMAUS] (lokal)
- Cronos: ssh -i [SSH_KEY_PATH] iggy@[SERVER_IP_CRONOS]

## Scripts Verzeichnis
/home/iggy/.openclaw/agora/scripts/

## Coding Standards
- Python: f-strings, type hints, error handling
- Bash: set -euo pipefail, Logging
- SQL: Immer Transaktionen, nie DROP ohne Backup

## Scripts
Eigene Scripts: /home/iggy/.openclaw/agents/apollon/scripts/
- dashboard_test.py
- quick-health.sh
- system_monitor.sh
