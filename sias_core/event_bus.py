"""
SIAS Event Bus — Redis Pub/Sub
Source of Truth: PostgreSQL
Kommunikation: Redis
OpenClaw: nur noch Runtime Shell
"""
import redis
import json
from datetime import datetime

REDIS_HOST = "192.168.23.80"
REDIS_PORT = 6379

class SIASEventBus:
    def __init__(self):
        self.redis = redis.Redis(
            host=REDIS_HOST, port=REDIS_PORT,
            decode_responses=True
        )
        self.pubsub = self.redis.pubsub()

    def publish(self, channel, event_type, data, agent="unknown"):
        """Event publizieren"""
        event = {
            "type": event_type,
            "agent": agent,
            "data": data,
            "timestamp": datetime.now().isoformat()
        }
        self.redis.publish(channel, json.dumps(event))
        # Backup in DB-ready Format
        self.redis.lpush(
            f"sias:events:{channel}",
            json.dumps(event)
        )
        # Max 1000 Events pro Channel behalten
        self.redis.ltrim(f"sias:events:{channel}", 0, 999)
        return event

    def subscribe(self, channels):
        """Auf Channels subscriben"""
        if isinstance(channels, str):
            channels = [channels]
        self.pubsub.subscribe(*channels)
        return self.pubsub

    def listen(self):
        """Events empfangen (blocking)"""
        for message in self.pubsub.listen():
            if message["type"] == "message":
                try:
                    event = json.loads(message["data"])
                    yield message["channel"], event
                except json.JSONDecodeError:
                    continue

# Channels definieren
CHANNELS = {
    "arbitrage": "sias:arbitrage",
    "security": "sias:security",
    "research": "sias:research",
    "tasks": "sias:tasks",
    "alerts": "sias:alerts",
}

if __name__ == "__main__":
    bus = SIASEventBus()
    print("✅ SIAS Event Bus connected")
    print(f"Redis: {REDIS_HOST}:{REDIS_PORT}")

    # Test Event
    evt = bus.publish(
        CHANNELS["tasks"],
        "test",
        {"message": "SIAS Event Bus is alive"},
        agent="metamaus"
    )
    print(f"Test Event: {evt}")
