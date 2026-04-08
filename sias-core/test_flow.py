"""
Test: Athene findet Arbitrage → Event → Hermes validiert
"""
from event_bus import SIASEventBus, CHANNELS
import time

bus = SIASEventBus()

print("🏛 Athene: Arbitrage Signal senden...")
bus.publish(
    CHANNELS["arbitrage"],
    "arbitrage_found",
    {
        "pair": "D/USDT",
        "spread": 0.48,
        "binance_price": 67400,
        "gateio_price": 67650,
        "volume_binance": 36400000,
        "volume_gateio": 2000000
    },
    agent="athene"
)
print("✅ Event gesendet — Hermes sollte reagieren")
