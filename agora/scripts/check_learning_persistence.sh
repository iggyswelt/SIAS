#!/bin/bash
# Learning Persistence Check

DB_LEARNINGS=$(sudo -u postgres psql -d demo_scraper -t -c "SELECT COUNT(*) FROM learnings WHERE created_at::date = CURRENT_DATE;" 2>/dev/null | xargs)
CURRENT_HOUR=$(date +%H)

if [ "$DB_LEARNINGS" -eq 0 ] && [ "$CURRENT_HOUR" -ge 12 ]; then
    echo "🔴 KRITISCH: Keine Learnings heute in DB (Stand $CURRENT_HOUR Uhr)"
else
    echo "✅ OK: $DB_LEARNINGS Learnings heute in DB"
fi
