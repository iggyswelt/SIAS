#!/bin/bash
set -e

SSH_CMD="[SSH_COMMAND_REDACTED]"

echo "=== Ollama Version VOR Update ==="
$SSH_CMD "ollama --version 2>&1 || echo 'nicht installiert'"

echo ""
echo "=== Ollama Update ==="
$SSH_CMD "curl -fsSL https://ollama.com/install.sh | sh"
$SSH_CMD "systemctl restart ollama"
sleep 5
$SSH_CMD "ollama --version"

echo ""
echo "=== 9B Test nach Update ==="
RESULT=$($SSH_CMD "curl -s --max-time 120 http://localhost:11434/api/generate \
  -d '{\"model\":\"hf.co/unsloth/Qwen3.5-9B-GGUF:Q5_K_M\",\"prompt\":\"17 Schafe, alle außer 9 sterben, wieviele bleiben?\",\"stream\":false}' \
  -o /tmp/r9b.json && cat /tmp/r9b.json")
echo "$RESULT"

echo ""
echo "=== VRAM ==="
$SSH_CMD "nvidia-smi --query-gpu=memory.used,memory.free --format=csv,noheader"
