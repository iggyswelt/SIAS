# Zerberus — Tools
## Monitoring Commands
- ping -c 1 [SERVER_IP_METAMAUS]
- nc -zv [SERVER_IP_METAMAUS] 5000
- systemctl --user status openclaw-gateway.service
- journalctl --user -u openclaw-gateway -n 50

## SSH
ssh -i [SSH_KEY_PATH] iggy@[SERVER_IP_CRONOS]

## Eigene Scripts
- /home/iggy/.openclaw/agents/zerberus/scripts/zerberus_network_scan.sh
- /home/iggy/.openclaw/agents/zerberus/scripts/zerberus_scan.py
- /home/iggy/.openclaw/agents/zerberus/scripts/threat_feed.sh
