# V5 UI — 4 Verbesserungen für Apollon
**ARTH-2026-0417-009 | Arthemis Review — nur Fix-Auftrag, KEIN GREENLIGHT**

---

## P-01: AGENTS — MODEL IN KACHEL + FALLBACKS IM POPUP

### ISSUE
Agent-Karten (agents.html, Zeilen 14-22) zeigen nur Emoji + Name + Rolle. Kein Model, kein Provider, keine Fallback-Info.

Die API `/api/stats/agents` liefert nur `{agent_id, task_count, tokens}` — kein Model-Feld.

Die `/api/openclaw/stats` enthält `"model": "MiniMax-M2.5-highspeed"` (app.py:593), ist aber im Popup nicht abgefragt.

### FIX
**1. Backend — `app.py` Route `/api/stats/agents` erweitern (Zeile ~434):**
- Neues Feld `model` aus dem OpenClaw Session-Tracking lesen (analog `get_openclaw_agent_stats()` in app.py:2846)
- Neues Feld `fallbacks` — Array von Fallback-Providern falls primärer Provider down
- Neues Feld `provider` — aktueller Provider-Name
- Neues Feld `status` — 'running' | 'error' | 'unknown'

**2. Frontend — `agents.html` Kacheln erweitern:**
- Unter Rolle eine zweite Zeile mit Model-Name (z.B. "MiniMax-M2.5") und Provider-Badge
- Kleine farbige Indikator-Dots: grün=OK, gelb=Fallback aktiv, rot=error

**3. Frontend — Popup (`showAgentDetail()`) erweitern:**
- Grid-Zeile "Model" mit Primary + Fallback-Liste
- Farbcodierung: primärer Provider grün, Fallbacks in gelb
- Wenn Fallback aktiv: Banner "⚠️ Fallback aktiv — [Provider X]"

### AUFWAND: Mittel

---

## P-02: YOUTUBE KOMMENTARE — ANTWORTEN MIT 2 VORSCHLÄGEN

### ISSUE
Die `/api/hestia/comments` API existiert bereits und liefert `{recent: [...], vip_pending: [...], stats: {...}}`.

Aber:
1. Es gibt KEINE Reply-Vorschlags-Funktion — kein Feld `reply_suggestions` in den Comment-Objekten
2. Es gibt KEINE API-Route `POST /api/hestia/comments/:id/reply` zum Absenden
3. Das YouTube-UI (youtube.html, Zeilen 167-179) zeigt nur Kommentare — keine Reply-Buttons

### FIX
**1. Backend — `app.py`:**
- Neue Route `GET /api/hestia/comments/:id/suggestions` — ruft Hestia auf, generiert 2 Reply-Vorschläge per LLM, speichert in DB
- Neue Route `POST /api/hestia/comments/:id/reply` — sendet gewählte Antwort per Hestia-YouTube-API, updated `reply_status` auf 'replied'
- Response von `GET /api/hestia/comments` erweitern: pro Comment ein Feld `has_suggestions: bool` und `suggestions: [string, string]`

**2. Frontend — `youtube.html` Kommentar-Tabelle erweitern:**
- Jede Zeile bekommt eine neue Spalte "Aktion"
- Reply-Button (💬) öffnet kleines Inline-Dropdown mit den 2 Vorschlägen
- User klickt auf Vorschlag → POST an `/api/hestia/comments/:id/reply` → Status-Update
- Wenn keine Suggestions vorhanden: "Generieren"-Button (Zauberstab-Icon)

### AUFWAND: Mittel

---

## P-03: MAIL — OUTLOOK-LAYOUT (ZWEI SPALTEN)

### ISSUE
`mail.html` (Zeilen 1-60): Single-Column mit Folder-Tabs + Tabelle. Kein Preview-Pane, kein Folder-Baum.

Outlook-Layout erwartet:
- Linke Spalte: Folder-Tree (Inbox, Sent, Drafts, Spam, etc.) + Folder-Stats
- Mitte: E-Mail-Liste (Absender, Betreff, Datum)
- Optional rechte Spalte oder Modal: E-Mail-Body Preview beim Klick

### FIX
**1. Frontend — `mail.html` komplett neu strukturieren:**

```html
<!-- Zwei-Spalten-Layout -->
<div style="display:flex;gap:1rem;height:calc(100vh - 200px)">
  <!-- Linke Spalte: Folder-Tree (20%) -->
  <div style="width:20%;min-width:150px">
    <div class="card" style="height:100%;padding:1rem">
      <div class="mail-folder-item active" onclick="switchMailFolder('inbox')">
        📥 Inbox <span class="badge">12</span>
      </div>
      <div class="mail-folder-item" onclick="switchMailFolder('sent')">📤 Sent</div>
      <div class="mail-folder-item" onclick="switchMailFolder('drafts')">📝 Drafts</div>
      <div class="mail-folder-item" onclick="switchMailFolder('spam')">🚫 Spam</div>
    </div>
  </div>

  <!-- Rechte Spalte: Email-Liste + Preview (80%) -->
  <div style="flex:1;display:flex;flex-direction:column;gap:1rem">
    <!-- Email-Liste -->
    <div class="card" style="flex:1;overflow:hidden">
      <table>...</table>
    </div>
    <!-- Preview-Pane (ersetzt Modal) -->
    <div id="mail-preview" class="card" style="height:200px;display:none;overflow-y:auto">
      ...
    </div>
  </div>
</div>
```

**2. CSS:**
- `.mail-folder-item` mit Hover-Effekt und active-State (linke Border in Accent-Farbe)
- `#mail-preview` ersetzt das existierende `#mail-modal`

**3. JS:**
- `openMailPreview(email)` ersetzt `openMailModal()` — zeigt Email-Body im Preview-Pane statt Modal
- Folder-Klick updated die aktive Klasse im Tree

### AUFWAND: Niedrig

---

## P-04: DEMOS — SORTIERUNG + GRUPPIERUNG

### ISSUE
`demos.html` (Zeilen 128-130):
```javascript
allEvents = (data.events||[]).sort((a,b) => (a.event_date||'').localeCompare(b.event_date||''));
```
Sortiert nur nach Datum. Keine Gruppierung nach Monat/Kategorie, keine Vergangen/G Zukünftig-Trennung.

API liefert 45 Events mit `category`-Feld (demo, info, kundgebung, streik, sport, kultur) und `event_date`.

### FIX
**1. Frontend — `demos.html` JS erweitern:**

```javascript
// Sortierung: Zuerst nach Validierung (valid > pending > invalid),
// dann nach Kategorie (demo > kundgebung > streik > info > sport > kultur),
// dann nach Datum
const CATEGORY_ORDER = {demo:0, kundgebung:1, streik:2, info:3, sport:4, kultur:5};

function sortAndGroup(events) {
  const now = new Date();
  const today = now.toISOString().substring(0,10);

  // Trenne vergangene / zukünftige
  const past = events.filter(e => e.event_date < today)
    .sort((a,b) => CATEGORY_ORDER[a.category] - CATEGORY_ORDER[b.category]
              || (a.event_date||'').localeCompare(b.event_date||''));
  const future = events.filter(e => e.event_date >= today)
    .sort((a,b) => CATEGORY_ORDER[a.category] - CATEGORY_ORDER[b.category]
              || (a.event_date||'').localeCompare(b.event_date||''));

  return {future, past};
}
```

**2. Render mit Gruppen-Headers:**
```javascript
function render(events) {
  const {future, past} = sortAndGroup(events);
  tbody.innerHTML = '';

  // Header: "ZUKÜNFTIGE EVENTS"
  if (future.length) {
    appendGroupHeader('ZUKÜNFTIGE EVENTS (' + future.length + ')');
    future.forEach(e => appendRow(e));
  }

  // Header: "VERGANGENE EVENTS"
  if (past.length) {
    appendGroupHeader('VERGANGENE EVENTS (' + past.length + ')');
    past.forEach(e => appendRow(e));
  }
}
```

**3. CSS:**
```css
.group-header { background:var(--accent); color:#fff; font-weight:600;
  padding:.3rem .5rem; border-radius:4px; margin-top:.5rem; }
```

**4. Stats:** "Diese Woche"-Stat um Validierungs-Donut oder Badges pro Kategorie erweitern.

### AUFWAND: Niedrig

---

## METADATEN
- Erstellt: 2026-04-17 23:xx
- Review-ID: ARTH-2026-0417-009
- Reviewer: Arthemis
- Ziel: Apollon
- Status: BLOCKED (Waiting for Iggy GREENLIGHT)
