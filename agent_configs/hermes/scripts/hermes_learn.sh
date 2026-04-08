#!/bin/bash
# hermes_learn.sh - Feedback-Verarbeitung für Hermes Demo-Scraper
# Liest invalide/bad markierte Einträge und extrahiert bad_keywords

set -e

DB_NAME="metamaus"
DB_USER="scraper"

LOG_FILE="/home/iggy/.openclaw/logs/hermes_learn.log"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

log "=== Hermes Learn Cycle gestartet ==="

# 1. Feedback aus DB lesen (invalide/bad markierte Einträge)
log "Suche nach Feedback-Einträgen..."

FEEDBACK_COUNT=$(psql -h localhost -U "$DB_USER" -d "$DB_NAME" -t -c "
    SELECT COUNT(*) FROM rheingold_findings 
    WHERE status IN ('invalid', 'bad', 'false_positive')
    AND created_at > NOW() - INTERVAL '7 days';
" 2>/dev/null || echo "0")

FEEDBACK_COUNT=$(echo "$FEEDBACK_COUNT" | xargs)

if [ "$FEEDBACK_COUNT" = "0" ] || [ -z "$FEEDBACK_COUNT" ]; then
    log "Kein Feedback gefunden (keine invaliden/bad Einträge)"
    exit 0
fi

log "Gefunden: $FEEDBACK_COUNT Feedback-Einträge"

# 2. Keywords extrahieren die zu false positives führen
log "Extrahiere bad keywords..."

# extraction via pattern analysis
psql -h localhost -U "$DB_USER" -d "$DB_NAME" -c "
    INSERT INTO hermes_bad_keywords (keyword, source, created_at)
    SELECT 
        LOWER(TRIM(BOTH FROM word)) as keyword,
        'feedback_learn' as source,
        NOW() as created_at
    FROM (
        SELECT DISTINCT regexp_split_to_table(LOWER(title), '\s+') as word
        FROM rheingold_findings 
        WHERE status IN ('invalid', 'bad', 'false_positive')
        AND created_at > NOW() - INTERVAL '7 days'
        AND title IS NOT NULL
    ) words
    WHERE word NOT IN (
        SELECT keyword FROM hermes_bad_keywords
    )
    AND LENGTH(word) > 3
    AND word !~ '^[0-9]+$'
    ON CONFLICT (keyword) DO NOTHING;
" 2>/dev/null

INSERTED=$(psql -h localhost -U "$DB_USER" -d "$DB_NAME" -t -c "
    SELECT COUNT(*) FROM hermes_bad_keywords 
    WHERE source = 'feedback_learn'
    AND created_at > NOW() - INTERVAL '24 hours';
" 2>/dev/null | xargs)

log "Neue bad_keywords eingefügt: $INSERTED"

# 3. Summary
TOTAL_BAD=$(psql -h localhost -U "$DB_USER" -d "$DB_NAME" -t -c "
    SELECT COUNT(*) FROM hermes_bad_keywords;
" 2>/dev/null | xargs)

log "Gesamt bad_keywords in DB: $TOTAL_BAD"
log "=== Hermes Learn Cycle abgeschlossen ==="
