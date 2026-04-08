"""
Hermes Worker — lauscht auf Arbitrage-Signale von Athene
und validiert Preise
"""
from event_bus import SIASEventBus, CHANNELS
import json

def handle_arbitrage_signal(event):
    """Wenn Athene ein Arbitrage-Signal findet"""
    data = event.get("data", {})
    pair = data.get("pair", "?")
    spread = data.get("spread", 0)
    print(f"📡 Hermes: Arbitrage Signal empfangen!")
    print(f"   Pair: {pair}, Spread: {spread}%")

    # Hier würde Hermes den Preis validieren
    # Für jetzt: simpler Check
    if spread > 0.2:
        print(f"   ✅ Spread > 0.2% — VALID")
        return {"valid": True, "pair": pair, "spread": spread}
    else:
        print(f"   ❌ Spread zu klein — SKIP")
        return {"valid": False, "reason": "spread_too_small"}

if __name__ == "__main__":
    bus = SIASEventBus()
    bus.subscribe(CHANNELS["arbitrage"])
    print("🔍 Hermes Worker gestartet — lauscht auf Arbitrage...")

    for channel, event in bus.listen():
        if event.get("type") == "arbitrage_found":
            result = handle_arbitrage_signal(event)
            # Ergebnis zurück publizieren
            bus.publish(
                CHANNELS["security"],
                "price_validated" if result["valid"] else "price_rejected",
                result,
                agent="hermes"
            )
