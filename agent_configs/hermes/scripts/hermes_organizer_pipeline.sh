#!/bin/bash
# Hermes Organizer → Rheingold Pipeline
# Links demo_events.organizer to rheingold_entities automatically

set -e

LOGFILE="/home/iggy/.openclaw/logs/hermes_organizer_pipeline.log"
echo "[$(date)] Organizer Pipeline starting..." >> "$LOGFILE"

python3 << 'EOF' >> "$LOGFILE" 2>&1
import psycopg2
import os
from datetime import datetime

# Database connection
DB_CONFIG = {
    "dbname": os.getenv("DB_NAME", "metamaus"),
    "user": os.getenv("DB_USER", "scraper"),
    "host": "localhost"
}

def sync_organizers_to_rheingold():
    """Sync demo event organizers to rheingold_entities"""
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()

    # Get all unique organizers from demo_events
    cur.execute("""
        SELECT DISTINCT organizer
        FROM demo_events
        WHERE organizer IS NOT NULL
        AND organizer != ''
        AND is_valid = true
    """)
    organizers = [row[0] for row in cur.fetchall()]

    entities_created = 0
    entities_updated = 0

    for organizer in organizers:
        # Check if entity already exists
        cur.execute("""
            SELECT id, name
            FROM rheingold_entities
            WHERE name = %s OR %s = ANY(alias)
        """, (organizer, organizer))
        existing = cur.fetchone()

        if not existing:
            # Create new entity
            source_name = f"Demo-Discovery-{datetime.now().strftime('%Y-%m-%d')}"
            cur.execute("""
                INSERT INTO rheingold_entities (name, entity_type, source, created_at)
                VALUES (%s, 'ngo', %s, NOW())
                RETURNING id
            """, (organizer, source_name))
            entity_id = cur.fetchone()[0]
            entities_created += 1
            print(f"[NEW] Created entity: {organizer} (ID: {entity_id})")
        else:
            entities_updated += 1
            print(f"[EXIST] Entity already exists: {organizer} (ID: {existing[0]})")

    conn.commit()
    cur.close()
    conn.close()

    print(f"[SUMMARY] Created: {entities_created}, Updated: {entities_updated}, Total: {len(organizers)}")
    return entities_created, entities_updated, len(organizers)

if __name__ == "__main__":
    created, updated, total = sync_organizers_to_rheingold()
    print(f"[DONE] {created} new entities, {updated} existing, {total} total organizers")
EOF

echo "[$(date)] Organizer Pipeline completed" >> "$LOGFILE"
echo "✅ Organizer → Rheingold Pipeline completed"
