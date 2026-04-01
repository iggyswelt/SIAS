# Rheingold — Tools
## DB Queries
psql -h 127.0.0.1 -U scraper -d metamaus -c "SELECT COUNT(*) FROM rheingold_findings;"
psql -h 127.0.0.1 -U scraper -d metamaus -c "SELECT * FROM rheingold_findings ORDER BY created_at DESC LIMIT 10;"

## Web Recherche
- DuckDuckGo für Erstrecherche
- Pythia für Screenshot-Auswertung

## IFG
- fragdenstaat.de für IFG-Anfragen

## Mail (Himalaya)
Account: investigativ@abbydon.com
IMAP: mail.abydon.com:993 | SMTP: mail.abydon.com:465
Passwort: NUR aus DB Vault — nie im Chat zeigen!
Mails lesen:
 himalaya message list --account investigativ --folder INBOX
 himalaya message read --account investigativ [uid]
Unverarbeitete Mail-Alerts aus DB:
 SELECT key, value FROM agent_knowledge WHERE category = 'incoming_mail' AND value::jsonb->>'processed' = 'false' ORDER BY learned_at DESC;


## Scripts
Eigene Scripts: /home/iggy/.openclaw/agents/rheingold/scripts/
- rheingold_activity_logger.py
- rheingold_autonomous.py
- rheingold-crawler.service
- rheingold_quality_bot.py
- rheingold_quality_clean.py
- rheingold_quality_final.py
- rheingold_quality.py
