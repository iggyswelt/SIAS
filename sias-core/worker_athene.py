"""
Athene Worker — lauscht auf Task Events,
führt Arbitrage Scans aus
"""
from event_bus import SIASEventBus, CHANNELS
import json

if __name__ == "__main__":
    bus = SIASEventBus()
    bus.subscribe([CHANNELS["tasks"], CHANNELS["alerts"]])
    print("🏛 Athene Worker gestartet")

    for channel, event in bus.listen():
        if event.get("type") == "task_created":
            data = event.get("data", {})
            if data.get("agent") != "athene":
                continue
            print(f"📋 Athene: Task #{data.get('task_id')} empfangen")
            print(f"   {data.get('task', '?')}")
            # Hier kommt die Athene-Logik rein

        elif event.get("type") == "trade_opportunity":
            data = event.get("data", {})
            print(f"🔔 Athene: Trade Opportunity! {data.get('pair')}")
            print(f"   Spread: {data.get('spread')}%")
            print(f"   Security: APPROVED")
            # Hier würde Athene den Trade planen
