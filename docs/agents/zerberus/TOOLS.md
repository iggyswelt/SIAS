# Zerberus — Tools
## Monitoring
ping -c 1 192.168.23.170 && ping -c 1 192.168.23.80
nc -zv 192.168.23.170 5000
systemctl --user status openclaw-gateway.service

## Logs
journalctl --user -u openclaw-gateway -n 50
tail -f /var/log/syslog

## SSH auf Server
ssh -i /home/iggy/.ssh/cronos_key iggy@192.168.23.80


## Scripts
Eigene Scripts: /home/iggy/.openclaw/agents/zerberus/scripts/
- zerberus_network_scan.sh
- zerberus_scan.py
- zerberus_scan.sh
