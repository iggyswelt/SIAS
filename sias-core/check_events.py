"""Check events in Redis for Phase 1 test verification."""
import redis
import json

r = redis.Redis(host='192.168.23.80', port=6379, decode_responses=True)

print('=== Arbitrage Events ===')
events = r.lrange('sias:events:sias:arbitrage', 0, 5)
if not events:
    print("  (keine Events)")
for e in events:
    d = json.loads(e)
    print(f"  {d['agent']}: {d['type']} — {d['data']}")

print()
print('=== Security Events (Hermes Response) ===')
events = r.lrange('sias:events:sias:security', 0, 5)
if not events:
    print("  (keine Events)")
for e in events:
    d = json.loads(e)
    print(f"  {d['agent']}: {d['type']} — {d['data']}")
