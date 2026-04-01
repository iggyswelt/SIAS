# Zerberus — Heartbeat
Interval: 15m (kürzestes Interval im Team)
Check: ping alle 4 Server + Port-Check 5000, 5432, 8080
Status OK: Alle Services up
Status WARN: Ein Service nicht erreichbar
Status CRITICAL: Gateway oder DB down → Telegram sofort
Telegram: 737961726
