#!/bin/bash
# Rate-Limit Tracker
# Speichert API-Calls und bremst bei Annäherung ans Limit

COUNTER_FILE="/tmp/nvidia_api_calls.json"
MAX_CALLS_PER_HOUR=50  # Konservativ starten
RESET_INTERVAL=3600      # 1 Stunde in Sekunden

# Initialisiere Counter falls nicht vorhanden
if [ ! -f "$COUNTER_FILE" ]; then
    echo '{"calls": 0, "reset_at": '$(date -d "+1 hour" +%s)'}' > "$COUNTER_FILE"
fi

# Lese aktuellen Stand
CALLS=$(python3 -c "import json; d=json.load(open('$COUNTER_FILE')); print(d['calls'])")
RESET_AT=$(python3 -c "import json; d=json.load(open('$COUNTER_FILE')); print(d['reset_at'])")
NOW=$(date +%s)

# Reset wenn Stunde abgelaufen
if [ $NOW -gt $RESET_AT ]; then
    echo '{"calls": 0, "reset_at": '$(($NOW + $RESET_INTERVAL))'}' > "$COUNTER_FILE"
    CALLS=0
fi

# Check ob Limit erreicht
if [ $CALLS -ge $MAX_CALLS_PER_HOUR ]; then
    echo "⚠️ RATE LIMIT BREMSE: $CALLS/$MAX_CALLS_PER_HOUR calls dieser Stunde!"
    echo "Warte bis: $(date -d @$RESET_AT)"
    exit 1
fi

# Erhöhe Counter
python3 -c "
import json
d = json.load(open('$COUNTER_FILE'))
d['calls'] += 1
json.dump(d, open('$COUNTER_FILE', 'w'))
print(f'✓ API Call {d[\"calls\"]}/$MAX_CALLS_PER_HOUR')
"
