#!/bin/bash
# Freqtrade Backup Script
BACKUP_DIR="$HOME/backups/freqtrade"
DATE=$(date +%Y%m%d_%H%M)

# Create backup (only user_data, not the whole .freqtrade)
tar -czf "$BACKUP_DIR/freqtrade_$DATE.tar.gz" ~/.freqtrade/user_data/ 2>/dev/null

# Keep only 7 days
find "$BACKUP_DIR" -name "freqtrade_*.tar.gz" -mtime +7 -delete

echo "Freqtrade backup: $BACKUP_DIR/freqtrade_$DATE.tar.gz"
