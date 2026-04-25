# V5 UI-AUDIT — Fix-Auftraege
**Mission:** ARTH-2026-0416-007
**Datum:** 2026-04-16
**Status:** Analyse fertig, KEIN GREENLIGHT — nur Fix-Auftraege

---

### P-01: Token Usage zeigt 0 (Landing Page)

**Ursache:** Falscher Spaltenname in SQL-Query. Die Tabelle `token_usage` hat eine Spalte `timestamp` (nicht `created_at`). Die Route `/api/dashboard-stats` (Zeile 228-230 in `app.py`) verwendet `created_at`:

```python
# app.py Zeile 228-230 — FALSCH:
'token_today': query_db("SELECT COUNT(*) FROM token_usage WHERE created_at >= CURRENT_DATE"),
'token_week': query_db("SELECT COUNT(*) FROM token_usage WHERE created_at >= CURRENT_DATE - INTERVAL '7 days'"),
'token_total': query_db("SELECT COUNT(*) FROM token_usage"),
```

API-Response zeigt: `token_today: ""` und `token_week: ""` (leer = SQL-Fehler wird geschluckt), `token_total: "2170"` (kein WHERE = funktioniert). `query_db()` fängt Exceptions und gibt `""` zurueck — Frontend zeigt `d.token_today||"—"` was `—` rendert.

**Fix fuer Apollon:**
Datei: `/home/iggy/SIAS/dashboard/app.py`, Zeile 228-230

```python
# ERSETZE created_at durch timestamp:
'token_today': query_db("SELECT COUNT(*) FROM token_usage WHERE timestamp >= CURRENT_DATE"),
'token_week': query_db("SELECT COUNT(*) FROM token_usage WHERE timestamp >= CURRENT_DATE - INTERVAL '7 days'"),
'token_total': query_db("SELECT COUNT(*) FROM token_usage"),
```

**Aufwand:** Niedrig (1 Zeile auf 2 Zeilen aendern)

---

### P-02: Demo-Tab leer — kein Demo-Kalender

**Ursache:** Die `demos.html` ist eine statische Showcase-Seite mit 6 fixen Demo-Karten (Multi-Agent Chat, Dashboard V3, etc.). Sie zeigt KEINE echten Demo-Daten aus der DB. Die API `/api/demos` liefert 47 Events mit Status/Validierung — aber `demos.html` hat keinen Fetch-Aufruf und keine Kalender-/Tabellen-Logik.

**Fix fuer Apollon:**
Datei: `/home/iggy/SIAS/dashboard/templates/demos.html`

1. Bestehende Demo-Karten behalten (als "Showcase" oben).
2. Darunter einen neuen `<div>` einfuegen mit:
   - Fetch von `/api/demos` beim Laden
   - Tabelle mit: Datum | Titel | Location | Status | Validierung | Quelle
   - Farb-Badges fuer `validation_status` (valid=gruen, pending=gelb, invalid=rot)
   - Filter nach `category` (demo/info) und `validation_status`
   - Sortierung nach `event_date`

**Aufwand:** Mittel (neuer JS-Block + Tabellen-HTML, ~80 Zeilen)

---

### P-03: YouTube Community-Subtab fehlt

**Ursache:** `youtube.html` hat keine Tab-Struktur. Es gibt nur eine flache Liste der letzten Videos aus `agent_knowledge`. Die API-Routen existieren bereits in `app.py`:
- `/api/youtube/community/top100/comments` (Zeile 2343) → laeuft, `yt_community` hat 1011 Eintraege
- `/api/youtube/community/top100/loyalty` (Zeile 2361)

Aber `youtube.html` hat weder Tabs noch einen Fetch auf diese Endpoints. `/api/youtube/community/elite` gibt `{"members":[],"status":"success"}` zurueck — dieser Route-Name existiert nicht als separater Endpoint.

**Fix fuer Apollon:**
Datei: `/home/iggy/SIAS/dashboard/templates/youtube.html`

1. Tab-System hinzufuegen: "Videos" | "Community Top100"
2. Tab "Videos" = aktuelle Video-Liste
3. Tab "Community" = Fetch `/api/youtube/community/top100/comments` + Tabelle mit: Username | Comments | Last Seen | Badge-Level
4. Zweiten Subtab "Loyalitaet" der `/api/youtube/community/top100/loyalty` fetcht

**Aufwand:** Mittel (Tab-System + 2 Fetch-Blöcke + Tabellen, ~100 Zeilen)

---

### P-04: Agents nicht klickbar

**Ursache:** `agents.html` besteht aus 9 statischen `agent-card` Divs ohne jegliche Interaktivitaet. Kein `onclick`, kein `href`, kein `data-id`, kein Modal-Target. Die Karten sind rein deklarativ.

**Fix fuer Apollon:**
Datei: `/home/iggy/SIAS/dashboard/templates/agents.html`

1. Jeder `agent-card` bekommt `onclick="showAgentDetail('metamaus')"` etc.
2. Neues Modal `#agent-modal` (hidden by default):
   - Fetch `/api/stats/agents` fuer Task-Count
   - Letzte 5 Tasks: `/api/tasks?agent=<name>&limit=5` (falls Route existent, sonst ICA-Log-Filter)
   - Tokens-Info
   - Status (Online/Offline)
3. CSS fuer `.agent-card:hover` mit Cursor-Pointer + leichter Highlight
4. JS `showAgentDetail(name)` Funktion die Modal oeffnet und Daten laedt

**Aufwand:** Mittel (Modal-HTML + JS-Funktion + Hover-CSS, ~80 Zeilen)

---

### P-05: Tasks — kein Detail-Modal bei Klick

**Ursache:** `tasks.html` rendert eine Filterbar + Tabelle mit Server-Side-Rendering (Jinja `{% for t in tasks %}`). Die `<tr>` Elemente haben keine Click-Handler, keine `data-id` Attribute, kein Modal. Reiner statischer HTML-Output.

**Fix fuer Apollon:**
Datei: `/home/iggy/SIAS/dashboard/templates/tasks.html`

1. Jede Tabellenzeile bekommt: `<tr class="task-row" data-id="{{t[0]}}" onclick="showTaskDetail({{t[0]}})">`
2. Neues Modal `#task-modal`:
   - Task-ID, Agent, Beschreibung (vollstaendig, nicht abgeschnitten)
   - Status, Prioritaet, Created-Date
   - Payload/Error-Info falls in DB vorhanden
3. JS `showTaskDetail(id)`:
   - Fetch `/api/tasks/<id>` (falls Route existent) ODER
   - Alternativ: Zeilen-Daten per `data-*` Attributen im TR speichern und im Modal anzeigen
4. CSS: `.task-row:hover` mit Cursor-Pointer + Highlight

**Aufwand:** Mittel (Modal + Click-Handler + ~60 Zeilen JS)

---

### P-06: Mail-Seite fehlt komplett

**Ursache:** 
- **Kein Frontend-Route:** Es gibt keinen `@app.route('/mail')` in `app.py`. 
- **Kein Template:** `/home/iggy/SIAS/dashboard/templates/mail.html` existiert nicht.
- **Kein Nav-Link:** `base.html` Sidebar (Zeile 47-52) hat keinen Mail-Eintrag.
- **APIs existieren:** `/api/mails/himalaya` (GET, Zeile 2596), `/api/mails/himalaya/read` (POST, Zeile 2627), `/api/rheingold/mail/send/<id>` (POST, Zeile 2670) — alle vorhanden und funktional.

**Fix fuer Apollon:**

1. **Neue Datei:** `/home/iggy/SIAS/dashboard/templates/mail.html`
   - Ordner-Tabs: Inbox | Sent | Drafts
   - Fetch `/api/mails/himalaya?folder=inbox&limit=50`
   - Tabelle: Absender | Betreff | Datum | Gelesen-Status
   - Klick auf Mail → Fetch `/api/mails/himalaya/read` (POST) → Modal mit Body
   - Rheingold Mails-Section: Fetch `/api/rheingold/mail/list` (falls Route fehlt: neuen API-Endpoint dafuer bauen)

2. **app.py:** Neuen Route hinzufuegen:
   ```python
   @app.route('/mail')
   def mail():
       return render_template('mail.html', active='mail')
   ```

3. **base.html Zeile 52 (vor Settings):** Neuen Nav-Link:
   ```html
   <a href="/mail" class="{{'active' if active=='mail'}}"><span>📧 Mail</span></a>
   ```

**Aufwand:** Hoch (neues Template ~150 Zeilen + Route + Nav-Link + evtl. zusaetzliche API-Route)

---

## Zusammenfassung

| Problem | Ursache | Aufwand |
|---------|---------|---------|
| P-01 Token Usage 0 | SQL-Spalte `created_at` → muss `timestamp` heissen | Niedrig |
| P-02 Demo-Tab leer | Statisches HTML, kein API-Fetch | Mittel |
| P-03 YT Community fehlt | Keine Tab-Struktur, keine API-Anbindung | Mittel |
| P-04 Agents nicht klickbar | Keine Click-Handler/Modal | Mittel |
| P-05 Tasks kein Detail | Keine Click-Handler/Modal | Mittel |
| P-06 Mail-Seite fehlt | Template + Route + Nav-Link fehlen komplett | Hoch |
