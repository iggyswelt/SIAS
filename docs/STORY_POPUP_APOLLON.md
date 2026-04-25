# APOLLON-AUFTRAG: Story-Ideen Popup + Video-Ready Format

**ARTH-2026-0421-001** | Status: BLOCKED — Fixes erforderlich
**Quelle:** Arthemis Review | Ziel: Rheingold Standalone (Port 5004)
**Aufwand:** Mittel-Hoch

---

## ANLAGE A — ARTHEMIS-BEFUNDE

### A1 DB Schema `story_ideen` — AKTUELL

```
 id         | integer                  | PK
 titel      | text                     | not null
 these      | text                     |
 punkte     | jsonb                    | default '[]'
 links      | jsonb                    | default '[]'
 entities   | jsonb                    | default '[]'
 status     | text                     | default 'neu'
 source     | text                     | default 'manuell'
 created_at | timestamp with time zone | default now()
 updated_at | timestamp with time zone | default now()
```

**FEHLT:**
- `video_text TEXT` — vorlesbarer Fließtext für Video/Audio-Generierung
- `mini_graph JSONB DEFAULT '[]'` — Nodes+Edges für Mini-Netzwerk-Karte

**ANMERKUNG:** Die Spalte `entities` ist bei allen 4 bestehenden Stories `[]` (leer). Die Entity-Verknüpfung muss entweder:
(a) manuell gepflegt werden, oder
(b) dynamisch aus `rheingold_entities` + `rheingold_relations` abgeleitet werden.

### A2 findings.html — AKTUELL

- `.story-card` hat **keinen `onclick`-Handler**. Keine Detail-Ansicht möglich.
- Story-Actions (In Arbeit / Fertig / Archiv) sind direkt auf der Karte sichtbar.
- Es gibt ein Modal für **Neue Story-Idee** (`modal-add`) und ein **Finding-Modal** (`finding-modal`), aber **KEIN Story-Detail-Modal**.
- `renderStoryCard()` gibt nur Titel, These, Punkte, Links, Status-Buttons aus. Kein Graph. Kein Video-Text.

### A3 API — AKTUELL

- `GET /api/story-ideen` → Liste aller Stories ✅
- `GET /api/story-ideen?id=X` → Einzelstory ✅ (vermutlich, zu prüfen)
- `POST /api/story-ideen` → Neue Story ✅
- `PATCH /api/story-ideen/<id>` → Status-Update ✅
- **FEHLT:** `GET /api/story-ideen/<id>/graph` → Mini-Graph + echte DB-Relationen

### A4 Entity-Namen in DB (Abweichungen)

Die im vorgeschlagenen `mini_graph` verwendeten Entity-Namen existieren teilweise NICHT exakt so in `rheingold_entities`:

| Vorgeschlagen | In DB vorhanden |
|---------------|-----------------|
| Alfred Landecker Foundation | ❌ Nicht exakt. Stattdessen: `Alfred Landecker` (person), `Landecker Digital Memory Lab` (hub), `Alfred Landecker Professur für Werte und Public Policy (Uni Oxford)` (bildung) |
| HateAid gGmbH | ✅ `HateAid gGmbH` (hub) und `HateAid` (hub) |
| Campact e.V. | ✅ `Campact e.V.` (hub), `Campact` (hub), `Verein Campact` (ngo), `Demokratie-Stiftung Campact` (stiftung) |
| Fearless Democracy e.V. | ❌ Nicht in Top-10 — muss geprüft werden |
| Anna-Lena von Hodenberg | ❌ Nicht gefunden — muss geprüft werden |

**EMPFEHLUNG:** Apollon soll beim Befüllen von `mini_graph` die exakten `rheingold_entities.name` verwenden, damit die Graph-API später echte Relations auflösen kann. Alternativ: `mini_graph` speichert `entity_id` statt `label`.

---

## ÄNDERUNG 1 — DB ERWEITERN

```sql
ALTER TABLE story_ideen
ADD COLUMN IF NOT EXISTS video_text TEXT,
ADD COLUMN IF NOT EXISTS mini_graph JSONB DEFAULT '[]';
```

### Migration bestehender Story: Alfred Landecker

**WICHTIG:** Die Entity-Namen im `mini_graph` müssen an die tatsächlichen DB-Namen angeglichen werden, ODER es wird ein Mapping verwendet. Arthemis empfiehlt: `entity_id` statt `label` in `mini_graph` speichern, wenn möglich.

Falls `label` beibehalten wird (einfacher für Frontend):

```sql
UPDATE story_ideen SET
  video_text = 'Die Reimann-Familie ist bekannt als Eigentümer der JAB Holding — das Unternehmen hinter Reckitt Benckiser. Was weniger bekannt ist: Die Familie hat eine dokumentierte NS-Vergangenheit. Zwangsarbeiter wurden in ihren Fabriken eingesetzt. Als Reaktion darauf gründeten sie 2019 die Alfred Landecker Foundation — mit einer Zustiftung von 260 Millionen Euro. Klingt nach Sühne. Aber wohin fließt das Geld? Unter anderem an HateAid — 1,4 Millionen Euro im Jahr 2024, jetzt belegt durch den Jahresbericht. HateAid wiederum gehört zu 33 Prozent Campact — jener Organisation, die seit 2019 keine Gemeinnützigkeit mehr hat, weil das Finanzamt sie als überwiegend politisch eingestuft hat. Die Geschäftsführerin von HateAid, Anna-Lena von Hodenberg, war vorher Campaignerin bei Campact. Der Beirat von HateAid liest sich wie ein Who is Who: Renate Künast von den Grünen, Brigitte Zypries von der SPD, Nadine Schön von der CDU. Parteiübergreifend abgesichert. Und im Dezember 2025 wurde den HateAid-Gründerinnen die Einreise in die USA verweigert.',

  mini_graph = '[
    {"id": "alf", "label": "Alfred Landecker\\nFoundation", "type": "stiftung", "color": "#ef4444"},
    {"id": "hateaid", "label": "HateAid\\ngGmbH", "type": "hub", "color": "#f97316"},
    {"id": "campact", "label": "Campact\\ne.V.", "type": "hub", "color": "#f97316"},
    {"id": "fearless", "label": "Fearless\\nDemocracy", "type": "verein", "color": "#eab308"},
    {"id": "hodenberg", "label": "Anna-Lena\\nv. Hodenberg", "type": "person", "color": "#3b82f6"},
    {"id": "reimann", "label": "Reimann-Familie\\n(JAB Holding)", "type": "firma", "color": "#6b7280"},
    {"id": "kuenast", "label": "Renate\\nKünast", "type": "politiker_bund", "color": "#22c55e"},
    {"id": "zypries", "label": "Brigitte\\nZypries", "type": "politiker_bund", "color": "#22c55e"},
    {"id": "schoen", "label": "Nadine\\nSchön", "type": "politiker_bund", "color": "#22c55e"}
  ]'::jsonb,

  links = '[
    {"label": "ALF Jahresbericht 2024", "url": "https://www.alfredlandecker.org/de/ueber-uns/berichte"},
    {"label": "HateAid Einnahmen Wikipedia", "url": "https://de.wikipedia.org/wiki/HateAid"},
    {"label": "Campact Gemeinnützigkeit (Spiegel)", "url": "https://www.spiegel.de/politik/deutschland/campact-verliert-gemeinnuetzigkeit-a-1294321.html"},
    {"label": "US-Einreiseverbot HateAid (Netzpolitik)", "url": "https://netzpolitik.org/2025/hateaid"},
    {"label": "Reimann NS-Geschichte (Spiegel)", "url": "https://www.spiegel.de/wirtschaft/unternehmen/reckitt-benckiser-reimann-familie-und-die-ns-vergangenheit-a-1258733.html"},
    {"label": "Handelsregister HateAid", "url": "https://www.northdata.de/HateAid+gGmbH,+Berlin/HRB+196656+B"}
  ]'::jsonb

WHERE titel LIKE '%Sühne%' OR titel LIKE '%Landecker%';
```

---

## ÄNDERUNG 2 — POPUP/DETAIL-ANSICHT IN FINDINGS.HTML

### Ziel: Story-Card wird klickbar → Detail-Modal öffnet sich

**Layout-Entwurf:**

```
┌─────────────────────────────────────────────────────────────┐
│ 🎯 [TITEL]                                        [×]        │
├───────────────────────────┬─────────────────────────────────┤
│ MINI-NETZWERK-KARTE       │ VIDEO-TEXT                      │
│ (SVG D3 Force-Graph)      │ (vorlesbarer Fließtext)         │
│ Nodes: Entities           │ Schriftgröße groß               │
│ Edges: Verbindungen       │ Gut lesbar                      │
│                           │                                 │
│                           ├─────────────────────────────────┤
│                           │ LINKS (klickbar, echter Artikel)│
│                           │ → [Label] öffnet in neuem Tab   │
├───────────────────────────┴─────────────────────────────────┤
│ [In Arbeit] [Fertig] [Archiv]    Status: NEU                │
└─────────────────────────────────────────────────────────────┘
```

### Frontend-Implementierung

**Schritt 2a: Story-Card klickbar machen**

In `renderStoryCard()`:
- `onclick="openStoryModal(${s.id})"` auf `.story-card` hinzufügen
- `cursor:pointer` im CSS für `.story-card`
- `event.stopPropagation()` bei den Status-Buttons beibehalten

**Schritt 2b: Story-Detail-Modal erstellen**

Neues Modal `#story-modal` (analog `finding-modal`):
- Overlay + Card-Container
- Header: Titel + Close-Button
- Body: Zwei-Spalten-Layout (Grid oder Flex)
  - Links: Mini-Netzwerk-Graph (400x300px Container)
  - Rechts oben: Video-Text (große Schrift, lesbar)
  - Rechts unten: Links-Liste (klickbar)
- Footer: Status-Buttons + aktueller Status

**Schritt 2c: D3.js Force-Graph einbinden**

Voraussetzung: D3.js wird geladen (CDN oder lokal).

```html
<script src="https://d3js.org/d3.v7.min.js"></script>
```

Mini-Graph-Funktion:
```javascript
function renderMiniGraph(containerId, nodes, edges) {
  const width = 400, height = 300;
  const svg = d3.select(`#${containerId}`)
    .append("svg")
    .attr("viewBox", [0, 0, width, height])
    .attr("width", "100%")
    .attr("height", "100%");

  const simulation = d3.forceSimulation(nodes)
    .force("link", d3.forceLink(edges).id(d => d.id).distance(60))
    .force("charge", d3.forceManyBody().strength(-200))
    .force("center", d3.forceCenter(width / 2, height / 2));

  const link = svg.append("g")
    .selectAll("line")
    .data(edges)
    .join("line")
    .attr("stroke", "#888")
    .attr("stroke-width", 1.5);

  const node = svg.append("g")
    .selectAll("g")
    .data(nodes)
    .join("g")
    .call(d3.drag()
      .on("start", dragstarted)
      .on("drag", dragged)
      .on("end", dragended));

  node.append("circle")
    .attr("r", d => d.type === 'person' ? 12 : 18)
    .attr("fill", d => d.color || "#999")
    .attr("stroke", "#fff")
    .attr("stroke-width", 1.5);

  node.append("text")
    .text(d => d.label)
    .attr("x", 0)
    .attr("y", d => d.type === 'person' ? 22 : 28)
    .attr("text-anchor", "middle")
    .attr("font-size", "10px")
    .attr("fill", "var(--text)");

  simulation.on("tick", () => {
    link
      .attr("x1", d => d.source.x)
      .attr("y1", d => d.source.y)
      .attr("x2", d => d.target.x)
      .attr("y2", d => d.target.y);
    node.attr("transform", d => `translate(${d.x},${d.y})`);
  });

  function dragstarted(event, d) { if (!event.active) simulation.alphaTarget(0.3).restart(); d.fx = d.x; d.fy = d.y; }
  function dragged(event, d) { d.fx = event.x; d.fy = event.y; }
  function dragended(event, d) { if (!event.active) simulation.alphaTarget(0); d.fx = null; d.fy = null; }
}
```

**Schritt 2d: `openStoryModal(id)` implementieren**

```javascript
async function openStoryModal(id) {
  try {
    const [storyRes, graphRes] = await Promise.all([
      fetch(`/api/story-ideen?id=${id}`),  // oder /api/story-ideen/<id>
      fetch(`/api/story-ideen/${id}/graph`)
    ]);
    const story = await storyRes.json();
    const graphData = await graphRes.json();

    // Modal befüllen
    document.getElementById('story-modal-title').textContent = story.titel;
    document.getElementById('story-modal-text').textContent = story.video_text || '(Kein Video-Text vorhanden)';

    // Links
    const links = Array.isArray(story.links) ? story.links : [];
    document.getElementById('story-modal-links').innerHTML = links.map(l =>
      `<a href="${escapeHtml(l.url || '#')}" target="_blank" rel="noopener" style="color:var(--accent);display:block;margin:4px 0">${escapeHtml(l.label || l)} ↗</a>`
    ).join('');

    // Graph
    document.getElementById('story-modal-graph').innerHTML = '';
    if (graphData.nodes && graphData.nodes.length) {
      renderMiniGraph('story-modal-graph', graphData.nodes, graphData.edges || []);
    } else {
      document.getElementById('story-modal-graph').innerHTML = '<p style="color:var(--muted)">Kein Graph verfügbar</p>';
    }

    // Status
    document.getElementById('story-modal-status').textContent = STATUS_LABELS[story.status] || story.status;

    // Modal anzeigen
    document.getElementById('story-modal-overlay').style.display = 'flex';
  } catch(e) {
    alert('Fehler beim Laden: ' + e.message);
  }
}
```

**HINWEIS:** Falls `/api/story-ideen?id=X` nicht existiert, muss eine Einzel-Story-Route angelegt werden (z.B. `GET /api/story-ideen/<id>`).

---

## ÄNDERUNG 3 — NEUE API ROUTE

### `GET /api/story-ideen/<id>/graph`

**Response-Format:**

```json
{
  "story_id": 1,
  "nodes": [
    {"id": "alf", "label": "Alfred Landecker\nFoundation", "type": "stiftung", "color": "#ef4444"},
    {"id": "hateaid", "label": "HateAid\ngGmbH", "type": "hub", "color": "#f97316"}
  ],
  "edges": [
    {"source": "alf", "target": "hateaid", "label": "fördert"},
    {"source": "hateaid", "target": "campact", "label": "Gesellschafter"}
  ]
}
```

**Implementierungslogik (Flask/Python):**

```python
@app.route('/api/story-ideen/<int:story_id>/graph')
def get_story_graph(story_id):
    # 1. Mini-Graph aus story_ideen laden
    story = StoryIdee.query.get_or_404(story_id)
    mini_graph = story.mini_graph or []

    nodes = [{
        "id": n.get("id"),
        "label": n.get("label"),
        "type": n.get("type"),
        "color": n.get("color")
    } for n in mini_graph]

    node_ids = [n["id"] for n in nodes]

    # 2. Echte Relationen aus rheingold_relations laden
    #    Dafür müssen die mini_graph IDs mit rheingold_entities verknüpft werden.
    #    AM BESTEN: mini_graph speichert entity_id statt generischer id.
    #    FALLBACK: Über name/label matchen (unscharf).

    # Beispiel mit entity_id (empfohlen):
    entity_ids = [n.get("entity_id") for n in mini_graph if n.get("entity_id")]
    if entity_ids:
        relations = db.session.query(RheingoldRelation, e1, e2).\
            join(e1, RheingoldRelation.entity1_id == e1.id).\
            join(e2, RheingoldRelation.entity2_id == e2.id).\
            filter(RheingoldRelation.entity1_id.in_(entity_ids) | RheingoldRelation.entity2_id.in_(entity_ids)).\
            all()

        # ... edges aus relations aufbauen

    return jsonify({"story_id": story_id, "nodes": nodes, "edges": edges})
```

**ANMERKUNG:** Die aktuelle `mini_graph` Struktur im Auftrag verwendet generische `id` (z.B. `"alf"`). Für echte DB-Relationen ist es besser, `entity_id` (die numerische ID aus `rheingold_entities`) zu speichern. Arthemis empfiehlt:

```json
{"id": "alf", "entity_id": 123, "label": "Alfred Landecker Foundation", "type": "stiftung", "color": "#ef4444"}
```

Dann kann die API echte `rheingold_relations` abfragen.

---

## ÄNDERUNG 4 — STORY-FORMULAR ERWEITERN (Optional, aber empfohlen)

Das Modal `modal-add` für neue Story-Ideen sollte um Felder erweitert werden:

- `video_text` — Textarea (mehrzeilig)
- `mini_graph` — JSON-Textarea ODER Entity-Auswahl-Widget

Falls der User Story-Ideen manuell anlegt, muss er `video_text` und `mini_graph` pflegen können.

---

## CHECKLISTE FÜR APOLLON

### DB
- [ ] `ALTER TABLE` für `video_text` + `mini_graph`
- [ ] Migration der Alfred-Landecker-Story mit `video_text` + `mini_graph`
- [ ] Prüfen: Entity-Namen in `mini_graph` auf DB-Namen abstimmen ODER `entity_id` hinzufügen

### API
- [ ] `GET /api/story-ideen/<id>` sicherstellen (Einzelabfrage)
- [ ] `GET /api/story-ideen/<id>/graph` implementieren
- [ ] `POST /api/story-ideen` ggf. um `video_text` + `mini_graph` erweitern
- [ ] `PATCH /api/story-ideen/<id>` ggf. um `video_text` + `mini_graph` erweitern

### Frontend (findings.html)
- [ ] Story-Card klickbar machen (`onclick="openStoryModal(id)"`)
- [ ] Story-Detail-Modal HTML/CSS erstellen (Zwei-Spalten-Layout)
- [ ] D3.js einbinden (CDN)
- [ ] `renderMiniGraph()` implementieren
- [ ] `openStoryModal()` + `closeStoryModal()` implementieren
- [ ] Video-Text im Modal anzeigen (große, lesbare Schrift)
- [ ] Links im Modal als klickbare Liste anzeigen (neuer Tab)
- [ ] Status-Buttons im Modal beibehalten

### Formular (modal-add)
- [ ] Felder `video_text` + `mini_graph` hinzufügen (optional)

---

## AUFWANDSSCHÄTZUNG

| Teil | Aufwand | Risiko |
|------|---------|--------|
| DB Migration | niedrig | gering |
| API Route /graph | niedrig | mittel (Entity-Matching) |
| API Erweiterung POST/PATCH | niedrig | gering |
| Frontend Modal HTML/CSS | mittel | gering |
| D3.js Force-Graph | mittel | mittel (Dependency, Mobile) |
| Story-Card onclick + Integration | niedrig | gering |
| Entity-Matching (DB-Graph ↔ mini_graph) | mittel | hoch |
| **GESAMT** | **Mittel-Hoch** | **mittel** |

---

## ARTHEMIS-ENTSCHEIDUNG

**BLOCKED**

Gründe:
1. `video_text` + `mini_graph` Spalten fehlen in `story_ideen`
2. Kein Story-Detail-Modal vorhanden
3. `/api/story-ideen/<id>/graph` existiert nicht
4. `entities` Spalte ist leer — Entity-Verknüpfung muss geklärt werden
5. Entity-Namen in Vorschlag vs. DB divergieren

---

@Apollon: Bitte obige Checkliste abarbeiten. Bei Fragen zu Entity-Matching oder D3-Integration → Rückfrage an Arthemis vor Implementierung.

**Nach Fertigstellung:** Arthemis Review erforderlich bevor Deploy.
