#!/bin/bash
set -euo pipefail

MODELS=(
  "deepseek-v3.2"
  "deepseek-v3.2-nvidia"
  "glm-4.7-flash"
  "llama-3.2-1b-instruct"
)

echo "🔍 OpenClaw Health Check $(date '+%Y-%m-%d %H:%M:%S')"
echo "========================================"

for model in "${MODELS[@]}"; do
  echo -n "→ $model ... "
  START=$(date +%s.%N)
  RESULT=$(openclaw chat --model "$model" --one-shot "ping" 2>&1 || echo "CLI_ERROR")
  END=$(date +%s.%N)
  LAT=$(echo "($END - $START)*1000" | bc | cut -d. -f1)
  
  if echo "$RESULT" | grep -qi "pong\|ok\|ping"; then
    echo "✅ OK (${LAT}ms)"
  elif echo "$RESULT" | grep -qi "rate_limit\|429\|cooldown"; then
    echo "❌ RATE LIMIT / COOLDOWN"
  elif [ "$LAT" -gt 7000 ]; then
    echo "❌ TIMEOUT (${LAT}ms)"
  else
    echo "❌ FAILED (${LAT}ms)"
  fi
done