#!/bin/bash
set -euo pipefail

echo "=== SIAS Phase 1 LIVE TEST ==="
echo ""

# Hermes Worker im Hintergrund starten
python3 worker_hermes.py &
HERMES_PID=$!
echo "Hermes PID: $HERMES_PID"
sleep 2

# Athene sendet Arbitrage Signal
echo ""
echo "--- Athene Test ---"
python3 test_flow.py
sleep 3

# Events prüfen
echo ""
echo "--- Event Check ---"
python3 check_events.py

# Worker stoppen
echo ""
echo "--- Stopping Hermes ---"
kill $HERMES_PID 2>/dev/null
echo "Hermes gestoppt"

echo ""
echo "Erwartetes Ergebnis:"
echo "  athene: arbitrage_found"
echo "  hermes: price_validated"
echo "Wenn beide da → Phase 1 DONE ✅"
