#!/usr/bin/env python3
"""Dashboard API Test Script - 自动测试 + Telegram Alert"""
import requests
import sys
import os

BASE = "http://192.168.23.170:5000"
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "8378639787:AAE_GhJn8psSznW4R3V8ovZ1ue7-0XRx9zI")
CHAT_ID = "737961726"
TESTS = []

def test(name, url, expect_json=True):
    try:
        r = requests.get(f"{BASE}{url}", timeout=5)
        if r.status_code == 200:
            if expect_json:
                data = r.json()
                if data.get("status") == "success":
                    TESTS.append(f"✅ {name}")
                    return True
            TESTS.append(f"⚠️ {name} (200 but no JSON)")
            return False
        else:
            TESTS.append(f"❌ {name} -> {r.status_code}")
            return False
    except Exception as e:
        TESTS.append(f"❌ {name} -> {str(e)[:30]}")
        return False

def send_telegram(msg):
    if not TELEGRAM_TOKEN: return
    try:
        requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
                     data={"chat_id": CHAT_ID, "text": msg}, timeout=10)
    except: pass

print("=" * 40)
print("🧪 Dashboard API Test")
print("=" * 40)

test("Tasks", "/api/tasks")
test("Demos", "/api/demos/all")
test("Stats OpenClaw", "/api/stats/openclaw")
test("Stats Dashboard", "/api/stats/dashboard")

print("\n" + "=" * 40)
for t in TESTS: print(t)

failed = sum(1 for t in TESTS if t.startswith("❌"))
print("=" * 40)
print(f"Result: {len(TESTS) - failed}/{len(TESTS)} passed")

if failed > 0:
    msg = f"⚠️ Dashboard Test FAILED!\n{chr(10).join(TESTS)}"
    print(msg)
    send_telegram(msg)
    sys.exit(1)
else:
    print("✅ ALL PASSED")
    sys.exit(0)
