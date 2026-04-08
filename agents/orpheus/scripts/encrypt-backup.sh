#!/bin/bash
# Auto-encrypt SQL backups with TPM2
# Runs after orpheus backup

set -e

BACKUP_DIR="/home/iggy/backups/orpheus/db"
CLEVIS_DIR="/home/iggy/backups/orpheus/clevis"

mkdir -p "$CLEVIS_DIR"

# Fix TPM permissions on boot
sudo chmod 666 /dev/tpmrm0 2>/dev/null || true

# Encrypt new .sql files
cd "$BACKUP_DIR"
for f in *.sql; do
  [ -f "$f" ] || continue
  echo "Encrypting: $f"
  sudo clevis encrypt tpm2 '{"pcr_bank":"sha256","pcr_ids":"7"}' < "$f" > "$CLEVIS_DIR/${f}.clevis"
  rm -f "$f"
  echo "✅ $f → $CLEVIS_DIR/"
done

echo "Done: $(ls $CLEVIS_DIR/*.clevis 2>/dev/null | wc -l) encrypted files"
