# Rheingold — Tools

## Mail (Himalaya)
- List: himalaya message list --account investigativ
- Read: himalaya message read --account investigativ [uid]

## Datenbank (PostgreSQL)
psql -h 127.0.0.1 -U scraper -d metamaus
- SELECT COUNT(*) FROM rheingold_findings;
- SELECT * FROM rheingold_entities WHERE category = 'NGO';

## Scripts
- /home/iggy/.openclaw/agents/rheingold/scripts/rheingold-crawler.service
- /home/iggy/.openclaw/agents/rheingold/scripts/rheingold_autonomous.py
- /home/iggy/.openclaw/agents/rheingold/scripts/rheingold_quality_final.py
