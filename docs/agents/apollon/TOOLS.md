# Apollon — Tools

## Database
psql -h 127.0.0.1 -U scraper -d metamaus

## Server
- metamaus: 192.168.23.170 (lokal)
- Cronos: ssh -i /home/iggy/.ssh/cronos_key iggy@192.168.23.80

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
