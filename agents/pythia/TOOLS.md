# Pythia — Tools
## Server
- Cronos: [SERVER_IP_CRONOS] (RTX 3060)
- RedQueen: [SERVER_IP_REDQUEEN]:1234 (LM Studio)

## Modelle & Audit-Befehle
- Primary: qwen-vl-plus
- DB-Audit: UPDATE agent_knowledge SET verified_by = 'pythia' WHERE id = ...
- Log-Read: cat /home/iggy/.openclaw/logs/[agent].log

## Verboten
- nvidia/nemotron für Fakten-Checks (halluziniert zu stark).
- Selbst Code schreiben (Delegation an Apollon für Test-Scripte).
