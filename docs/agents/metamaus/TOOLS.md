# metamaus — Tools
## Erlaubte Aktionen
- openclaw sessions spawn [agent] "[aufgabe]"
- Datenbank lesen: psql -h 127.0.0.1 -U scraper -d metamaus -c "SELECT ..."
- Logs lesen: openclaw logs --follow

## NICHT erlaubt
- Dateien editieren (außer agent_knowledge DB Einträge)
- Code ausführen
- SSH auf andere Server
