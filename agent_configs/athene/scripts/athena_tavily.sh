#!/bin/bash
# ATHENA mit Tavily research Fähigkeit

# Load Tavily Key from Vault
source ~/.openclaw/scripts/load_vault_env.sh

QUERY="${1:-DutchCryptoDad trading strategy crypto}"

echo "🔍 ATHENA researching: $QUERY"

# Check if key exists
if [ -z "$TAVILY_API_KEY" ]; then
    # Try alternate env var
    source ~/.bashrc 2>/dev/null
fi

if [ -n "$TAVILY_API_KEY" ]; then
    echo "Using key: ${TAVILY_API_KEY:0:10}..."
    # Use Tavily API v2
    curl -s -X POST "https://api.tavily.com/search" \
        -H "Content-Type: application/json" \
        -d "{\"api_key\":\"$TAVILY_API_KEY\",\"query\":\"$QUERY\",\"max_results\":5}" 2>&1 | head -20
else
    echo "⚠️ Kein Tavily API Key gefunden"
    echo "Vault keys:"
    sudo -u postgres psql -d demo_scraper -c "SELECT name FROM secrets WHERE name LIKE '%tavily%';" 2>/dev/null
fi
