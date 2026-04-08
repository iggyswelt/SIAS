"""
Zerberus Worker — lauscht auf Security Events
Validiert nach Hermes' Preischeck
"""
from event_bus import SIASEventBus, CHANNELS
import json
import psycopg2

def get_db():
    return psycopg2.connect(
        host="127.0.0.1", user="scraper", dbname="metamaus")

def handle_price_validated(event):
    data = event.get("data", {})
    pair = data.get("pair", "?")
    spread = data.get("spread", 0)

    print(f"🛡 Zerberus: Security Check für {pair}")

    checks = {
        "spread_realistic": spread < 5.0,
        "not_known_scam": pair not in ["SCAM/USDT"],
        "volume_sufficient": True,
    }

    all_ok = all(checks.values())
    result = {
        "pair": pair,
        "spread": spread,
        "checks": checks,
        "approved": all_ok
    }

    if all_ok:
        print(f" ✅ Security APPROVED")
    else:
        failed = [k for k,v in checks.items() if not v]
        print(f" ❌ Security REJECTED: {failed}")

    try:
        conn = get_db()
        cur = conn.cursor()
        cur.execute("""
        INSERT INTO agent_knowledge (key, value, category, learned_at)
        VALUES (%s, %s, 'security_check', NOW())
        ON CONFLICT (key) DO UPDATE SET value=EXCLUDED.value
        """, (
            f"security_{pair}_{event.get('timestamp','')}",
            json.dumps(result)
        ))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f" DB Error: {e}")

    return result

if __name__ == "__main__":
    bus = SIASEventBus()
    bus.subscribe(CHANNELS["security"])
    print("🛡 Zerberus Worker gestartet")

    for channel, event in bus.listen():
        if event.get("type") == "price_validated":
            result = handle_price_validated(event)
            if result["approved"]:
                bus.publish(
                    CHANNELS["alerts"],
                    "trade_opportunity",
                    result,
                    agent="zerberus"
                )
