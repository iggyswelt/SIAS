#!/bin/bash
# HSM Setup Script - Run as user (not sudo)

echo "=== Nitrokey HSM Setup ==="
echo "1. Checking for HSM..."
pkcs11-tool --module /usr/lib/x86_64-linux-gnu/pkcs11/opensc-pkcs11.so --list-slots

echo ""
echo "2. If you see 'No slots', run this first:"
echo "   sudo usermod -a -G scard $USER"
echo "   logout and login again"

echo ""
echo "3. List existing keys (enter PIN when asked):"
echo "   pkcs11-tool --module /usr/lib/x86_64-linux-gnu/pkcs11/opensc-pkcs11.so --login --list-objects"

echo ""
echo "4. Generate Ed25519 keypair:"
echo "   pkcs11-tool --module /usr/lib/x86_64-linux-gnu/pkcs11/opensc-pkcs11.so --login --pin 123456 --keypairgen --key-type EC:prime256v1 --label 'binance-trading' --id 01"

echo ""
echo "5. Export public key:"
echo "   pkcs11-tool --read-object --type pubkey --label 'binance-trading' | openssl pkey -pubin -outform PEM > ~/binance_public.pem"
