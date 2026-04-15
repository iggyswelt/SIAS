# MetaMouse MiniMax Token Plan MCP Integration Plan

> **Für Hermes:** Mit subagent-driven-development skill umsetzen, Task für Task.
> **DEV-ONLY:** Nicht auf PROD-Ports (5000/5002/5010) deployen.

**Goal:** MiniMax Token Plan MCP Server (`minimax-coding-plan-mcp`) in Hermes Agent einbinden — damit Hermes `web_search` und `understand_image` als native Tools nutzen kann.

**Architecture:**
- hermes-agent hat bereits einen nativen MCP-Client in `tools/mcp_tool.py` (2200 Zeilen)
- Konfiguration in `~/.hermes/config.yaml` unter `mcp_servers`
- Server läuft via stdio transport (uvx subprocess)
- Zwei neue Tools für Hermes: `web_search` und `understand_image`
- Tools werden automatisch in die Tool-Registry eingetragen

**Tech Stack:** hermes-agent MCP Client, uvx, MiniMax Token Plan MCP

---

## Task 1: Config in config.yaml eintragen

**Objective:** MiniMax Token Plan MCP Server in hermes-agent config einbinden

**Files:**
- Modify: `/home/iggy/.hermes/config.yaml`

**Step 1: Bestehendes mcp_servers finden**

```bash
grep -n "^mcp_servers" /home/iggy/.hermes/config.yaml
```

Expected: "not found" → Section muss neu angelegt werden

**Step 2: YAML-Block hinzufügen**

Füge am Ende der config.yaml (nach allen anderen Sektionen) ein:

```yaml
mcp_servers:
  minimax_token_plan:
    command: "/home/iggy/.local/bin/uvx"
    args:
      - "minimax-coding-plan-mcp"
      - "-y"
    env:
      MINIMAX_API_KEY: "${MINIMAX_API_KEY}"
      MINIMAX_API_HOST: "https://api.minimax.io"
    timeout: 60        # per-tool-call timeout
    connect_timeout: 30
```

**Step 3: Verify Config Syntax**

```bash
python3 -c "import yaml; yaml.safe_load(open('/home/iggy/.hermes/config.yaml')); print('Config valid')"
```

Expected: "Config valid"

---

## Task 2: Hermes Agent neustarten

**Objective:** Hermes Agent neu starten damit MCP Server verbunden wird

**Files:**
- Keine Datei-Änderung — nur Prozess-Management

**Step 1: Prozess finden**

```bash
ps aux | grep "hermes.*agent\|hermes_agent" | grep -v grep | head -5
```

**Step 2: Graceful Restart**

```bash
# via hermes CLI
hermes restart

# ODER direkt
pkill -f "hermes-agent" && sleep 2 && hermes &
```

**Step 3: Verify MCP Server gestartet**

```bash
hermes tools --list 2>/dev/null | grep -i "web_search\|understand\|minimax"
```

Expected: `web_search` und `understand_image` in der Tool-Liste

---

## Task 3: Testen der neuen Tools

**Objective:** Die neuen MCP-Tools funktionieren korrekt

**Step 1: web_search testen**

Starte Hermes und frage:
```
Suche nach "Amadeu Antonio Stiftung Bundesförderung 2024"
```

Expected: Live-Suchergebnisse von MiniMax (nicht von static scrapers)

**Step 2: understand_image testen**

Lade ein Screenshot/Image hoch und frage:
```
Was ist auf diesem Bild zu sehen?
```

Expected: Vision-Analyse des Bildes

**Step 3: Token-Verbrauch prüfen**

Nach dem Test:
```
Wie viele Tokens habe ich heute verbraucht?
```

Expected: Zeigt echte Zahlen aus der MiniMax API

---

## Task 4: Token Plan Dashboard Integration (Bonus)

**Objective:** Die Token-Verbrauchsdaten auch im Dashboard anzeigen

**Files:**
- Modify: `/home/iggy/SIAS/dashboard_prod/app.py` (DEV: dashboard_dev)
- Modify: `/home/iggy/SIAS/dashboard_prod/index.html`

**Step 1: API-Endpoint einbauen**

In `app.py`, neuer Endpoint:

```python
@app.route("/api/token_plan")
def get_token_plan():
    """Holt Token Plan Guthaben von MiniMax API (5-Minuten Cache)."""
    import time as _time

    cache_key = "minimax_token_plan"
    now = datetime.now()

    # Cache prüfen
    if hasattr(app, '_billing_cache'):
        cached_time, cached_data = app._billing_cache.get(cache_key, (None, None))
        if cached_time and (now - cached_time).total_seconds() < 300:
            return jsonify(cached_data)

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

        result = {
            "source": "minimax_api",
            "timestamp": now.isoformat(),
            "tokens_remaining": None,
            "tokens_total": None,
            "tokens_used": None,
            "raw": api_data
        }

        if isinstance(api_data, dict):
            d = api_data.get("data", api_data)
            result["tokens_remaining"] = d.get("remaining_tokens") or d.get("remaining") or d.get("left")
            result["tokens_total"] = d.get("total_tokens") or d.get("total")
            result["tokens_used"] = d.get("used_tokens") or d.get("used")

        if not hasattr(app, '_billing_cache'):
            app._billing_cache = {}
        app._billing_cache[cache_key] = (now, result)

        return jsonify(result)

    except requests.exceptions.Timeout:
        return jsonify({"error": "API timeout"}), 504
    except Exception as e:
        return jsonify({"error": str(e)}), 500
```

**Step 2: HTML Panel einbauen**

Suche im index.html nach der Gateway-Stats-Box (ca. Zeile 876) und füge danach ein:

```html
                    <!-- Token Plan Box -->
                    <div style="background: rgba(0,255,136,0.05); border: 1px solid rgba(0,255,136,0.2); padding: 15px; border-radius: 8px;">
                        <div style="color: #888; font-size: 12px; margin-bottom: 5px;">Token Plan</div>
                        <div style="font-size: 24px; font-weight: bold; color: #00ff88;" id="tp-remaining">-</div>
                        <div style="color: #888; font-size: 12px;">von <span id="tp-total">-</span> verbleibend</div>
                    </div>
```

**Step 3: JavaScript Fetch-Logik**

Suche nach dem `fetch('/api/gateway_status')` Block (ca. Zeile 1330) und füge danach ein:

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

---

## Verify Both Integrations

**Step 1: MCP Tools testen**

```bash
hermes tools --list 2>/dev/null | grep -E "minimax|web_search|understand_image"
```

**Step 2: API-Endpoint testen**

```bash
curl -s http://127.0.0.1:5003/api/token_plan  # DEV Port
```

**Step 3: Dashboard UI testen**

Browser öffnen → Token Plan Box muss erscheinen

---

## Architektur-Entscheidungen

| Entscheidung | Begründung |
|---|---|
| uvx mit absolutem Pfad | `/home/iggy/.local/bin/uvx` explizit, nicht `uvx` (PATH-Variation vermeiden) |
| MINIMAX_API_KEY via env config | MCP client filtered standard env vars aus Sicherheitsgründen |
| 5-Minuten-Cache für Dashboard | MiniMax API hat Rate-Limits; Dashboard refreshed ~10s |
| KEIN neues DB-Schema | Read-only; kein Persistenzbedarf |

## Bekannte Risiken

1. **MCP Server startet nicht:** UVX muss im PATH des hermes-agent Prozesses sein (ist es: `/home/iggy/.local/bin`)
2. **API Key nicht in config.yaml:** `${MINIMAX_API_KEY}` wird aus `~/.hermes/.env` interpoliert (load_config liest .env)
3. **Tools nicht in Liste:** Nach Neustart prüfen; manchmal braucht es 2 Restart-Versuche
