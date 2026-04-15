# MetaMouse Token Plan Integration Plan

> **Für Hermes:** Mit subagent-driven-development skill umsetzen, Task für Task.

**Goal:** MiniMax Token Plan Guthaben (API `/coding_plan/remains`) in MetaMouse Dashboard anzeigen — live, automatisch, ohne manuelles CSV-Einpflegen.

**Architecture:**
- Neuer Flask-Endpoint `/api/token_plan` in `dashboard_dev/app.py`
- Ruft MiniMax API direkt auf (kein Zwischenserver)
- Response gecached (5-Minuten-Cache, da API Rate-Limits hat)
- Neues UI-Panel im Dashboard-HTML für "Token Plan" Box
- Bestehende `MINIMAX_API_KEY` aus `.env` wird wiederverwendet

**Tech Stack:** Flask, requests, Python StandardLib, Bootstrap UI

---

## Task 1: API-Key aus Environment laden

**Objective:** MiniMax API Key aus `.env` lesbar machen in `app.py`

**Files:**
- Modify: `/home/iggy/SIAS/dashboard_dev/app.py` — Zeile 1-20 (Imports + ENV)
  DEV = Port 5003, NICHT 5002 (5002 = PROD)

**Step 1: Test schreiben**

```python
def test_minimax_api_key_loaded():
    import os
    key = os.environ.get("MINIMAX_API_KEY", "")
    assert key != "", "MINIMAX_API_KEY must be set"
    assert key.startswith("sk-"), "Key should start with sk-"
```

**Step 2: Sicherstellen dass ENV geladen wird**

In `app.py` nach den Imports, ca. Zeile 15:
```python
from dotenv import load_dotenv
load_dotenv(os.path.expanduser("~/.hermes/.env"))
```

**Step 3: Verify**

```bash
cd /home/iggy/SIAS/dashboard_dev && grep -n "load_dotenv\|MINIMAX_API_KEY" app.py | head -10
```

Expected: Beide finden

---

## Task 2: `/api/token_plan` Endpoint erstellen

**Objective:** Flask-Endpoint der MiniMax API aufruft und Guthaben returned

**Files:**
- Modify: `/home/iggy/SIAS/dashboard_dev/app.py` — nach bestehenden `@app.route` Blöcken (ca. Zeile 1790)

**Step 1: Test schreiben**

```python
def test_token_plan_endpoint_returns_data(client):
    resp = client.get("/api/token_plan")
    assert resp.status_code == 200
    data = resp.get_json()
    assert "tokens_remaining" in data or "error" in data
```

**Step 2: Implementierung**

```python
@app.route("/api/token_plan")
def get_token_plan():
    """Holt Token Plan Guthaben von MiniMax API (5-Minuten Cache)."""
    import time as _time

    # Cache-Key
    cache_key = "minimax_token_plan"
    now = datetime.now()

    # Cache prüfen
    if hasattr(app, '_billing_cache'):
        cached_time, cached_data = app._billing_cache.get(cache_key, (None, None))
        if cached_time and (now - cached_time).total_seconds() < 300:
            return jsonify(cached_data)

    # API Call
    api_key = os.environ.get("MINIMAX_API_KEY", "")
    if not api_key:
        return jsonify({"error": "MINIMAX_API_KEY not configured"}), 500

    try:
        resp = requests.get(
            "https://www.minimax.io/v1/api/openplatform/coding_plan/remains",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            },
            timeout=15
        )
        if resp.status_code != 200:
            return jsonify({"error": f"API returned {resp.status_code}"}), resp.status_code

        api_data = resp.json()

        # Normalisiere Antwort (未知es Format parsen)
        # MiniMax gibt je nach Plan unterschiedlich zurück
        # Typisches Format: {"total": 1000000, "used": 450000, "remaining": 550000}
        # Oder: {"data": {"total_tokens": ..., "used_tokens": ...}}
        result = {
            "source": "minimax_api",
            "timestamp": now.isoformat(),
            "tokens_remaining": None,
            "tokens_total": None,
            "tokens_used": None,
            "raw": api_data
        }

        # Versuche verschiedene Feldnamen
        if isinstance(api_data, dict):
            if "data" in api_data:
                d = api_data["data"]
            else:
                d = api_data
            result["tokens_remaining"] = d.get("remaining_tokens") or d.get("remaining") or d.get("left")
            result["tokens_total"] = d.get("total_tokens") or d.get("total")
            result["tokens_used"] = d.get("used_tokens") or d.get("used")

        # Cache setzen
        if not hasattr(app, '_billing_cache'):
            app._billing_cache = {}
        app._billing_cache[cache_key] = (now, result)

        return jsonify(result)

    except requests.exceptions.Timeout:
        return jsonify({"error": "API timeout"}), 504
    except Exception as e:
        return jsonify({"error": str(e)}), 500
```

**Step 3: Verify**

```bash
cd /home/iggy/SIAS/dashboard_dev
curl -s http://127.0.0.1:5003/api/token_plan | python3 -m json.tool
```

Expected: JSON mit `tokens_remaining` oder `error`

---

## Task 3: UI Panel in Dashboard HTML einbauen

**Objective:** Token Plan Box im Dashboard sichtbar machen

**Files:**
- Modify: `/home/iggy/SIAS/dashboard_dev/index.html`

**Step 1: Test schreiben**

```python
def test_token_plan_html_exists():
    with open("/home/iggy/SIAS/dashboard_dev/index.html") as f:
        html = f.read()
    assert "token-plan" in html or "Token Plan" in html
```

**Step 2: HTML Panel einfügen**

Suche im HTML nach einer guten Stelle — idealerweise in der Stats-Grid Sektion neben den anderen_boxes wie "Gateway Status", "Demos", etc.

Typische Stelle (suche nach `oc-tokens` oder `Gateway` Box):

Füge NACH der Gateway-Box (ca. Zeile 876-890) ein neues Panel ein:

```html
                    <!-- Token Plan Box -->
                    <div style="background: rgba(0,255,136,0.05); border: 1px solid rgba(0,255,136,0.2); padding: 15px; border-radius: 8px;">
                        <div style="color: #888; font-size: 12px; margin-bottom: 5px;">Token Plan</div>
                        <div style="font-size: 24px; font-weight: bold; color: #00ff88;" id="tp-remaining">-</div>
                        <div style="color: #888; font-size: 12px;">von <span id="tp-total">-</span> verbleibend</div>
                    </div>
```

**Step 3: JavaScript Fetch-Logik**

Suche nach dem `fetch('/api/gateway_status')` Block (ca. Zeile 1330):

Füge einen zweiten Fetch nach dem Gateway-Call ein:

```javascript
        // Token Plan abrufen
        fetch('/api/token_plan')
            .then(r => r.json())
            .then(g => {
                if (g.error) {
                    document.getElementById('tp-remaining').textContent = 'Fehler';
                    document.getElementById('tp-remaining').style.color = '#ff4444';
                } else {
                    const remaining = g.tokens_remaining;
                    const total = g.tokens_total;
                    if (remaining !== null) {
                        document.getElementById('tp-remaining').textContent =
                            remaining >= 1000000 ? (remaining/1000000).toFixed(1)+'M' :
                            remaining >= 1000 ? Math.round(remaining/1000)+'K' : remaining;
                    }
                    if (total !== null) {
                        document.getElementById('tp-total').textContent =
                            total >= 1000000 ? (total/1000000).toFixed(1)+'M' :
                            total >= 1000 ? Math.round(total/1000)+'K' : total;
                    }
                }
            })
            .catch(() => {
                document.getElementById('tp-remaining').textContent = 'Offline';
                document.getElementById('tp-remaining').style.color = '#ff4444';
            });
```

**Step 4: Verify**

Dashboard öffnen und prüfen dass "Token Plan" Box erscheint mit echten Zahlen.

---

## Task 4: Error Handling & Edge Cases

**Objective:** Robuste Fehlerbehandlung für alle Failure-Szenarien

**Step 1: Fallback wenn API nicht erreichbar**

Im JS: bereits mit `.catch()` behandelt. Im Python: Timeout + Exception Handler vorhanden.

**Step 2: Fallback wenn keys null sind**

Im JS bereits mit `if (remaining !== null)` geschützt.

**Step 3: Logging**

Im `get_token_plan()` Endpoint, bei Fehler:
```python
import logging
logging.warning(f"Token Plan API Fehler: {e}")
```

---

## Task 5: Final Review & Test

**Step 1: Restart Dashboard**

```bash
# Alten Prozess finden und neustarten
ps aux | grep "dashboard_dev.*app.py" | grep -v grep
# Kill + restart
cd /home/iggy/SIAS/dashboard_dev && source venv/bin/activate && python app.py &
```

**Step 2: API Test**

```bash
curl -s http://127.0.0.1:5002/api/token_plan
```

**Step 3: UI Test**

Dashboard öffnen → "Token Plan" Box muss erscheinen mit Guthaben-Zahl.

---

## Architektur-Entscheidungen

| Entscheidung | Begründung |
|---|---|
| 5-Minuten-Cache | MiniMax API hat Rate-Limits; Dashboard wird alle ~10s refreshed |
| Cache in `app._billing_cache` (Memory) | Keine External DB/Redis nötig; einfach, restart-reset ist OK |
| Token Plan als separates Panel | Trennung von Session-Tokens (flüchtig) vs. Plan-Guthaben (persistiert) |
| MiniMax API Key aus `.env` | Bereits vorhanden, keine neuen Secrets nötig |
| Kein neues DB-Schema | Nicht nötig für read-only Anzeige |

## Unbekannte Variable

Das genaue Response-Format der `/coding_plan/remains` API ist unbekannt. Die Implementierung in Task 2 versucht mehrere Feldnamen (`remaining_tokens`, `remaining`, `left`). Nach dem ersten echten API-Call muss das Response geprüft und ggf. angepasst werden.
