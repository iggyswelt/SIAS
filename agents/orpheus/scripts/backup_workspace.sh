#!/bin/bash
# Backup-Script für Workspace
# Ziel: ~/.openclaw/backups/YYYY-MM-DD/

set -euo pipefail

DATE=$(date +%Y-%m-%d)
BACKUP_DIR=~/.openclaw/backups/$DATE
SOURCE_DIR=~/.openclaw/workspace

echo "📦 Erstelle Backup für $DATE..."

mkdir -p $BACKUP_DIR

# Nur aktive MD-Files kopieren (keine .backup Files!)
cp $SOURCE_DIR/*.md $BACKUP_DIR/ 2>/dev/null || true
cp $SOURCE_DIR/openclaw.json $BACKUP_DIR/ 2>/dev/null || true

echo "✅ Backup erstellt: $BACKUP_DIR"
echo "   Files: $(ls $BACKUP_DIR | wc -l)"

# Backups älter als 30 Tage löschen
find ~/.openclaw/backups/ -maxdepth 1 -type d -mtime +30 -exec rm -rf {} \; 2>/dev/null || true
echo "🗑️ Alte Backups (>30 Tage) gelöscht"
