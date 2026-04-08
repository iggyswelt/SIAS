# metamaus — Heartbeat (alle 11 Min)

## Prüfe:
1. Laufende Agent-Missionen — Fortschritt?
2. Zombie Tasks (>15 Min running)?
3. IFG Fristen (<7 Tage)?
4. Gateway CPU (>80% = Problem)?
5. Offene Punkte die bei Inaktivität gelöst werden können
6. SIAS Protocol Anwendung bei ALLEN tasks
7. Audit-Status: Hat Pythia verified_by in agent_knowledge oder agent_tasks gesetzt?
8. Alert bei Timeouts (> 60min) via Telegram.

## Reagiere:
- Agent hängt → nachsetzen oder killen (Erlaubnis es selbst auszuführen wenn andere Agenten keine Antwort geben)
- IFG Frist naht → Iggy via Telegram alertieren
- Gateway Problem → restart, 10sec vor ersten Versuch warten, erneut prüfen, wenn dann noch down -> Iggy informieren

## NICHT im Chat posten:
- "Alles OK"
- "Clean"
- "Keine Zombies"
- Heartbeat-Ergebnisse wenn alles normal ist
