# Orpheus — Tools
## Backup
cp -r /home/iggy/.openclaw/agents/ /home/iggy/backups/agents_$(date +%Y%m%d_%H%M%S)/
tar -czf /home/iggy/backups/milestones/milestone_$(date +%Y%m%d).tar.gz /opt/dashboard/

## NAS
ls -la /mnt/nas/ 2>/dev/null
rsync -av /home/iggy/backups/ iggy@192.168.23.104:/backups/

## GitHub
cd /home/iggy/.openclaw && git status && git push


## Scripts
Eigene Scripts: /home/iggy/.openclaw/agents/orpheus/scripts/
- orpheus_backup.sh
- orpheus_cron_monitor.sh
- orpheus_sias_update.sh
