#!/bin/bash
# Cronos Benchmark Script - 4 Teile

echo "=== BENCHMARK 1: VRAM Baseline ==="
nvidia-smi --query-gpu=memory.used,memory.free,temperature.gpu --format=csv,noheader

echo "=== BENCHMARK 2: NaniDAO 2B Tokens/s ==="
START=$(date +%s%N)
RESP2B=$(curl -s http://localhost:11434/api/generate -d '{
  "model": "hf.co/NaniDAO/nani-qwen-3.5-2B-gguf-q4km:latest",
  "prompt": "Check system: temp=72, load=88. Output JSON only.",
  "stream": false
}')
END=$(date +%s%N)
ELAPSED=$(( (END - START) / 1000000 ))
TPS_2B=$(echo "$RESP2B" | python3 -c "
import json,sys
r=json.load(sys.stdin)
dur=r.get('eval_duration',1)
cnt=r.get('eval_count',0)
if dur==0: dur=1
print(round(cnt/dur*1e9,1))
")
echo "2B: ${TPS_2B} tok/s (${ELAPSED}ms)"
echo "Resp: $(echo "$RESP2B" | python3 -c "import json,sys; r=json.load(sys.stdin); print(r.get('response','')[:150])")"

echo "=== VRAM nach 2B ==="
nvidia-smi --query-gpu=memory.used,memory.free --format=csv,noheader

echo "=== BENCHMARK 3: Qwen3.5 9B Tokens/s ==="
START=$(date +%s%N)
RESP9B=$(curl -s http://localhost:11434/api/generate -d '{
  "model": "hf.co/unsloth/Qwen3.5-9B-GGUF:Q5_K_M",
  "prompt": "Ein Bauer hat 17 Schafe. Alle ausser 9 sterben. Wie viele bleiben?",
  "stream": false
}')
END=$(date +%s%N)
ELAPSED=$(( (END - START) / 1000000 ))
TPS_9B=$(echo "$RESP9B" | python3 -c "
import json,sys
r=json.load(sys.stdin)
dur=r.get('eval_duration',1)
cnt=r.get('eval_count',0)
if dur==0: dur=1
print(round(cnt/dur*1e9,1))
")
echo "9B: ${TPS_9B} tok/s (${ELAPSED}ms)"
echo "Resp: $(echo "$RESP9B" | python3 -c "import json,sys; r=json.load(sys.stdin); print(r.get('response','')[:200])")"

echo "=== VRAM nach 9B ==="
nvidia-smi --query-gpu=memory.used,memory.free --format=csv,noheader

echo "=== BENCHMARK 4: Parallel ==="
curl -s http://localhost:11434/api/generate -d '{"model":"hf.co/NaniDAO/nani-qwen-3.5-2B-gguf-q4km:latest","prompt":"Say OK","stream":false}' > /tmp/bench_2b.json &
PID2=$!
curl -s http://localhost:11434/api/generate -d '{"model":"hf.co/unsloth/Qwen3.5-9B-GGUF:Q5_K_M","prompt":"List 3 programming languages.","stream":false}' > /tmp/bench_9b.json &
PID9=$!
wait $PID2 $PID9

echo "--- Parallel Results ---"
python3 -c "
import json
for f,n in [('/tmp/bench_2b.json','2B'),('/tmp/bench_9b.json','9B')]:
 r=json.load(open(f))
 dur=r.get('eval_duration',1)
 if dur==0: dur=1
 tps=round(r.get('eval_count',0)/dur*1e9,1)
 txt=r.get('response','')[:80]
 print(f'{n}: {tps} tok/s — {txt}')
"

echo "=== FINALE VRAM ==="
nvidia-smi --query-gpu=memory.used,memory.free,temperature.gpu --format=csv,noheader
