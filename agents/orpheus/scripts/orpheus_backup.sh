#!/bin/bash
# ORPHEUS — Full DB Backup + Encrypt
# Runs daily at 02:15
# SECURITY: Unencrypted files are shredded immediately after encryption!

set -e

source /home/iggy/.openclaw/.env

CLEVIS_DIR="/home/iggy/backups/orpheus/clevis"
TIMESTAMP=$(date +%Y%m%d_%H%M)

mkdir -p "$CLEVIS_DIR"

# Fix TPM permissions
sudo chmod 666 /dev/tpmrm0 2>/dev/null || true

# Create encrypted dump directly (pipe to avoid unencrypted file)
echo "Creating encrypted backup: metamaus-${TIMESTAMP}.sql.clevis"
pg_dump -h localhost -U "$DB_USER" "$DB_NAME" | \
  sudo clevis encrypt tpm2 '{"pcr_bank":"sha256","pcr_ids":"7"}' > \
  "$CLEVIS_DIR/metamaus-${TIMESTAMP}.sql.clevis"

echo "✅ Backup complete (encrypted, no unencrypted files)"
