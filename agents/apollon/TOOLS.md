# Apollon — Tools

## Database
psql -h 127.0.0.1 -U scraper -d metamaus

## Server
- metamaus: 192.168.23.170 (lokal)
- Cronos: ssh -i /home/iggy/.ssh/cronos_key iggy@192.168.23.80

## Dashboard
- Dashboard PROD: /opt/dashboard/
- Dashboard DEV: /opt/dashboard-dev/
- Dashboard V2: /opt/dashboard-v2/
- SIAS Core: /home/iggy/sias-core/
- Runbook: /opt/dashboard/RUNBOOK.md

## Scripts Verzeichnis
/home/iggy/.openclaw/agora/scripts/
Eigene Scripts: /home/iggy/.openclaw/agents/apollon/scripts/
- dashboard_test.py
- quick-health.sh
- system_monitor.sh

## Tech Stack
- Python, Flask, psycopg2, redis
- NIEMALS pip install — das macht Zerberus

## Coding Standards
- Python: f-strings, type hints, error handling
- Bash: set -euo pipefail, Logging
- SQL: Immer Transaktionen, nie DROP ohne Backup
