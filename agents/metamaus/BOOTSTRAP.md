# metamaus — Bootstrap

## Servers
- metamaus: [SERVER_IP_METAMAUS] (Gateway, PostgreSQL, Dashboard)
- Cronos: [SERVER_IP_CRONOS] (RTX 3060, Freqtrade)
- RedQueen: [SERVER_IP_REDQUEEN] (RTX 2080 Ti)

## DB & Knowledge
psql -h 127.0.0.1-U scraper -d metamaus
Jede Lektion wird in agent_knowledge gespeichert.

## Bei jedem Session-Start:
1. DB Status: psql -h 127.0.0.1 -U scraper -d metamaus -c "SELECT COUNT(*) FROM agent_tasks WHERE status='pending';"
2. Laufende Missionen: psql -h 127.0.0.1 -U scraper -d metamaus -c "SELECT * FROM agent_tasks WHERE status='running';"
3. Letzte Fehler: psql -h 127.0.0.1 -U scraper -d metamaus -c "SELECT * FROM agent_knowledge WHERE category='error' ORDER BY learned_at DESC LIMIT 5;"
4. Gateway Health: openclaw status 2>&1 | head -5
5. SIAS API: curl -s http://localhost:8000/status | head -3

## Nicht beim Start:
- Keine "alles OK" Meldung
- Nur melden wenn etwas KAPUTT ist

## Task Dispatcher (KRITISCH)
1. Pending Tasks laden:
   SELECT id, agent, task, priority FROM agent_tasks WHERE status='pending' ORDER BY priority DESC, created_at ASC LIMIT 5;
2. Spawn: sessions_spawn [agent] mit Task-Text.
3. REGEL: Max. 2 Agents parallel. Jeder Task benötigt Pythia-Audit für 'done'.

## ADM-XCHANGE PROTOKOLL
/home/iggy/.openclaw/adm/adm-xchange.txt
LESEN -> SPEICHERN -> SOFORT LEEREN -> BESTÄTIGEN.
