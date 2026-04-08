#!/bin/bash
# Dashboard Backup Script
BACKUP_DIR="$HOME/backups/dashboard"
DATE=$(date +%Y%m%d_%H%M)

# Create backup
tar -czf "$BACKUP_DIR/dashboard_$DATE.tar.gz" /opt/dashboard/ 2>/dev/null

# Keep only 7 days
find "$BACKUP_DIR" -name "dashboard_*.tar.gz" -mtime +7 -delete

echo "Dashboard backup: $BACKUP_DIR/dashboard_$DATE.tar.gz"
