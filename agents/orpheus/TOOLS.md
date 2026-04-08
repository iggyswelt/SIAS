# Orpheus — Tools

## Backup & Sync
- Agent-Backup: cp -r /home/iggy/.openclaw/agents/ /home/iggy/backups/agents_$(date +%Y%m%d_%H%M%S)/
- Dashboard-Backup: tar -czf /home/iggy/backups/milestones/milestone_$(date +%Y%m%d).tar.gz /opt/dashboard/
- NAS-Sync: rsync -av /home/iggy/backups/ iggy@[SERVER_IP_NAS]:/backups/

## GitHub
cd /home/iggy/.openclaw && git status && git add . && git commit -m "Backup $(date)" && git push

## Eigene Scripts
- /home/iggy/.openclaw/agents/orpheus/scripts/orpheus_backup.sh
- /home/iggy/.openclaw/agents/orpheus/scripts/orpheus_cron_monitor.sh
- /home/iggy/.openclaw/agents/orpheus/scripts/orpheus_sias_update.sh
