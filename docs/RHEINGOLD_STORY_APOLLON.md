# ARTHEMIS REVIEW — ARTH-2026-0420-002
# Rheingold 5004: Story-Ideen Tab + Findings Redesign
# Status: READY FOR APOLLON (wartet auf Iggy GREENLIGHT)

---

## SCHRITT 0 — CHECKPOINT (vor Änderungen)

```bash
cp /opt/rheingold-standalone/templates/findings.html \
   /opt/rheingold-standalone/templates/findings.html.bak.$(date +%Y%m%d_%H%M%S)

cp /opt/rheingold-standalone/app.py \
   /opt/rheingold-standalone/app.py.bak.$(date +%Y%m%d_%H%M%S)
```

---

## SCHRITT 1 — DB: STORY_IDEEN TABELLE

**Aufwand: Mittel**

Tabelle existiert noch nicht. Anlage:

```sql
CREATE TABLE IF NOT EXISTS story_ideen (
  id SERIAL PRIMARY KEY,
  titel TEXT NOT NULL,
  these TEXT,
  punkte JSONB DEFAULT '[]',
  links JSONB DEFAULT '[]',
  entities JSONB DEFAULT '[]',
  status TEXT DEFAULT 'neu'
    CHECK (status IN ('neu','in_arbeit','fertig','archiv')),
  source TEXT DEFAULT 'manuell',
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX ON story_ideen(status);
CREATE INDEX ON story_ideen(source);
```

**Migration bestehende Story-Ideen aus agent_knowledge:**

```sql
-- Bestehende story_ideen aus category='story_ideen'
INSERT INTO story_ideen (titel, these, punkte, links, status, source)
SELECT 
    (value->>'titel'),
    (value->>'these'),
    COALESCE((value->>'punkte')::jsonb, '[]'),
    COALESCE((value->>'links')::jsonb, '[]'),
    'neu',
    'rheingold'
FROM agent_knowledge
WHERE category = 'story_ideen'
  AND (value->>'titel') IS NOT NULL
ON CONFLICT DO NOTHING;
-- Erwartet: 1 Row inserted (story_alfred_landecker_hateaid)
```

---

## SCHRITT 2 — BACKEND ROUTES (app.py)

**Aufwand: Niedrig**

```python
# GET /api/story-ideen
# Query: ?status=neu|in_arbeit|fertig|archiv
@app.route('/api/story-ideen')
def api_story_ideen():
    status = request.args.get('status')
    query = db.session.query(StoryIdee)
    if status:
        query = query.filter_by(status=status)
    return jsonify([si.to_dict() for si in 
        query.order_by(StoryIdee.created_at.desc()).all()])

# POST /api/story-ideen
@app.route('/api/story-ideen', methods=['POST'])
def api_create_story_idee():
    data = request.get_json()
    si = StoryIdee(
        titel=data['titel'],
        these=data.get('these', ''),
        punkte=data.get('punkte', []),
        links=data.get('links', []),
        entities=data.get('entities', []),
        source='manuell'
    )
    db.session.add(si)
    db.session.commit()
    return jsonify(si.to_dict()), 201

# PATCH /api/story-ideen/<id>
@app.route('/api/story-ideen/<int:id>', methods=['PATCH'])
def api_update_story_idee(id):
    data = request.get_json()
    si = StoryIdee.query.get_or_404(id)
    for field in ('titel','these','punkte','links','entities','status'):
        if field in data:
            setattr(si, field, data[field])
    si.updated_at = func.now()
    db.session.commit()
    return jsonify(si.to_dict())

# DELETE /api/story-ideen/<id>
@app.route('/api/story-ideen/<int:id>', methods=['DELETE'])
def api_delete_story_idee(id):
    si = StoryIdee.query.get_or_404(id)
    db.session.delete(si)
    db.session.commit()
    return '', 204
```

**StoryIdee SQLAlchemy Model (neu in app.py):**

```python
class StoryIdee(db.Model):
    __tablename__ = 'story_ideen'
    id = db.Column(db.Integer, primary_key=True)
    titel = db.Column(db.Text, nullable=False)
    these = db.Column(db.Text)
    punkte = db.Column(JSONB, default=list)
    links = db.Column(JSONB, default=list)
    entities = db.Column(JSONB, default=list)
    status = db.Column(db.String, default='neu')
    source = db.Column(db.String, default='manuell')
    created_at = db.Column(db.DateTime(timezone=True), server_default=func.now())
    updated_at = db.Column(db.DateTime(timezone=True), onupdate=func.now())

    def to_dict(self):
        return {
            'id': self.id, 'titel': self.titel, 'these': self.these,
            'punkte': self.punkte, 'links': self.links,
            'entities': self.entities, 'status': self.status,
            'source': self.source, 'created_at': str(self.created_at),
            'updated_at': str(self.updated_at)
        }
```

---

## SCHRITT 3 — FINDINGS.HTML REDESIGN

**Aufwand: Mittel**

### 3A — Tab-Navigation (oben, vor Findings-Content)

```html
<div style="display:flex;gap:8px;margin-bottom:16px;border-bottom:1px solid var(--border);padding-bottom:8px">
  <button class="tab-btn active" id="tab-findings" onclick="switchTab('findings')">🔍 Findings</button>
  <button class="tab-btn" id="tab-story" onclick="switchTab('story')">🎯 Story-Ideen</button>
</div>
```

### 3B — Findings-Karte (neu, zeigt severity + klickbare Belege)

```html
<div class="finding-card finding-${f.severity || 'mittel'}">
  <div style="display:flex;justify-content:space-between;align-items:flex-start">
    <span class="badge badge-${f.severity || 'mittel'}">${(f.severity||'MITTEL').toUpperCase()}</span>
    <span class="finding-amount">${f.amount>0?fmtEur(f.amount):''}</span>
  </div>
  <div class="finding-title" style="font-size:15px;font-weight:600;margin:6px 0">
    ${escapeHtml(f.description||f.content||'')}
  </div>
  <div class="finding-bullets" style="font-size:13px;color:var(--muted);margin-bottom:6px">
    ${f.bullets ? '<ul style="margin-left:16px">'+f.bullets.map(b=>'<li>'+escapeHtml(b)+'</li>').join('')+'</ul>' : ''}
  </div>
  <div class="finding-links" style="font-size:12px;margin-bottom:6px">
    ${f.belege ? f.belege.map(b=>
      '<a href="'+escapeHtml(b.url||b)+'" target="_blank" style="color:var(--accent)">📎 '+escapeHtml(b.label||b)+'</a>'
    ).join(' '):''}
  </div>
  <div class="finding-meta">
    <span>📅 ${f.jahr||''}</span>
    <span class="${f.verified?'verified-yes':'verified-no'}">${f.verified?'✓ Verifiziert':'○ Offen'}</span>
    <span>${f.source||''}</span>
  </div>
</div>
```

**CSS:**
```css
.badge-kritisch { background:#dc2626; color:white; }
.badge-hoch     { background:#ea580c; color:white; }
.badge-mittel    { background:#ca8a04; color:white; }
.finding-kritisch { border-left:4px solid #dc2626; }
.finding-hoch     { border-left:4px solid #ea580c; }
.finding-mittel   { border-left:4px solid #ca8a04; }
```

**Severity-Logik (JS):**
```javascript
var severity = 'mittel';
if (f.relevance === 'hoch') severity = 'kritisch';
else if (f.relevance === 'mittel') severity = 'hoch';
```

### 3C — Story-Ideen Sub-Tab (neue Sektion)

```html
<div id="story-ideen-list" style="display:none">
  <!-- Story-Ideen werden hier gerendert -->
</div>
```

**Story-Ideen Karte:**
```
┌─────────────────────────────────────────┐
│ 🎯 NEU  [In Arbeit] [Fertig] [Archiv]  │
│                                         │
│ Sühne-Geld aus NS-Zwangsarbeit          │
│ finanziert HateAid                      │
│                                         │
│ Reimann-Familie → ALF → 1,4M€ HateAid  │
│                                         │
│ • Reimann: JAB Holding, NS-Zwangsarbeit│
│ • ALF = Benckiser Stiftung Zukunft     │
│ • HateAid-GF kam von Campact            │
│ • Beirat: Künast, Zypries, Schön       │
│                                         │
│ → alfred-landecker.org                  │
│ → hateaid.org                           │
└─────────────────────────────────────────┘
```

**Story-Karte JS:**
```javascript
function renderStoryCard(si) {
  var statusColors = {'neu':'badge-neu','in_arbeit':'badge-in_arbeit','fertig':'badge-fertig','archiv':'badge-archiv'};
  var statusLabels = {'neu':'🎯 NEU','in_arbeit':'🔄 IN ARBEIT','fertig':'✅ FERTIG','archiv':'📦 ARCHIV'};
  var html = '<div class="finding-card">';
  html += '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px">';
  html += '<span class="badge '+statusColors[si.status]+'">'+statusLabels[si.status]+'</span>';
  html += '<div style="display:flex;gap:6px">';
  html += '<button onclick="event.stopPropagation();patchStatus('+si.id+',\'in_arbeit\')">🔄</button>';
  html += '<button onclick="event.stopPropagation();patchStatus('+si.id+',\'fertig\')">✅</button>';
  html += '<button onclick="event.stopPropagation();patchStatus('+si.id+',\'archiv\')">📦</button>';
  html += '</div></div>';
  html += '<div style="font-size:15px;font-weight:600;margin-bottom:4px">'+escapeHtml(si.titel)+'</div>';
  if(si.these) html += '<p style="font-size:12px;color:var(--muted);font-style:italic;margin-bottom:8px">'+escapeHtml(si.these)+'</p>';
  if(si.punkte && si.punkte.length)
    html += '<ul style="font-size:13px;margin-left:16px;margin-bottom:8px">'+si.punkte.map(p=>'<li>'+escapeHtml(p)+'</li>').join('')+'</ul>';
  if(si.links && si.links.length)
    html += '<div style="font-size:12px">'+si.links.map(l=>
      '<a href="'+escapeHtml(l.url||l)+'" target="_blank" style="color:var(--accent)">→ '+escapeHtml(l.label||l.url)+'</a>'
    ).join(' ')+'</div>';
  html += '<div style="font-size:11px;color:var(--muted);margin-top:6px">'+escapeHtml(si.source)+' · '+new Date(si.created_at).toLocaleDateString('de-DE')+'</div>';
  html += '</div>';
  return html;
}
```

### 3D — Tab-Switch-Funktion (JS)

```javascript
function switchTab(tab) {
  document.getElementById('tab-findings').classList.toggle('active', tab==='findings');
  document.getElementById('tab-story').classList.toggle('active', tab==='story');
  document.getElementById('findings-list').style.display = tab==='findings' ? '' : 'none';
  document.getElementById('story-ideen-list').style.display = tab==='story' ? '' : 'none';
  if(tab==='story' && !window.storyIdeenLoaded) {
    window.storyIdeenLoaded = true;
    loadStoryIdeen();
  }
}

function loadStoryIdeen() {
  fetch('/api/story-ideen').then(r=>r.json()).then(function(data){
    var container = document.getElementById('story-ideen-list');
    if(!data.length) {
      container.innerHTML = '<p style="color:var(--muted);text-align:center;padding:30px">Keine Story-Ideen</p>';
      return;
    }
    container.innerHTML = data.map(renderStoryCard).join('');
  });
}

function patchStatus(id, status) {
  fetch('/api/story-ideen/'+id, {
    method:'PATCH',
    headers:{'Content-Type':'application/json'},
    body: JSON.stringify({status:status})
  }).then(r=>r.json()).then(loadStoryIdeen);
}
```

---

## SCHRITT 4 — MANUELL HINZUFÜGEN (Formular)

**Aufwand: Niedrig**

Unter Story-Ideen Tab, über der Liste:

```html
<div id="add-story-form" style="background:var(--surface2);border:1px solid var(--border);border-radius:8px;padding:14px;margin-bottom:16px">
  <button onclick="toggleStoryForm()" style="font-weight:600">+ Neue Story-Idee</button>
  <div id="story-form-fields" style="display:none;margin-top:12px">
    <input id="si-titel" placeholder="Titel" style="width:100%;margin-bottom:8px;padding:6px">
    <textarea id="si-these" placeholder="Kernthese (1 Satz)" style="width:100%;margin-bottom:8px;padding:6px"></textarea>
    <textarea id="si-punkte" placeholder="Punkte (einer pro Zeile)" style="width:100%;margin-bottom:8px;padding:6px;height:80px"></textarea>
    <input id="si-link-label" placeholder="Link-Text" style="width:48%;margin-bottom:8px;padding:6px">
    <input id="si-link-url" placeholder="URL" style="width:48%;margin-bottom:8px;padding:6px;float:right">
    <button onclick="submitStoryIdee()" style="padding:8px 16px;background:var(--accent);color:white;border:none;border-radius:4px">Speichern</button>
  </div>
</div>
```

```javascript
function toggleStoryForm() {
  var f = document.getElementById('story-form-fields');
  f.style.display = f.style.display === 'none' ? '' : 'none';
}

function submitStoryIdee() {
  var titel = document.getElementById('si-titel').value.trim();
  var these = document.getElementById('si-these').value.trim();
  var punkteRaw = document.getElementById('si-punkte').value.trim();
  var linkLabel = document.getElementById('si-link-label').value.trim();
  var linkUrl = document.getElementById('si-link-url').value.trim();
  var punkte = punkteRaw ? punkteRaw.split('\n').filter(p=>p.trim()) : [];
  var links = (linkLabel && linkUrl) ? [{label:linkLabel, url:linkUrl}] : [];
  if(!titel) { alert('Titel erforderlich'); return; }
  fetch('/api/story-ideen', {
    method:'POST',
    headers:{'Content-Type':'application/json'},
    body: JSON.stringify({titel:titel, these:these, punkte:punkte, links:links})
  }).then(r=>r.json()).then(function(){
    document.getElementById('si-titel').value='';
    document.getElementById('si-these').value='';
    document.getElementById('si-punkte').value='';
    document.getElementById('si-link-label').value='';
    document.getElementById('si-link-url').value='';
    toggleStoryForm();
    loadStoryIdeen();
  });
}
```

---

## AUFWAND PRO SCHRITT

| Schritt | Aufwand | Begründung |
|---------|---------|------------|
| SCHRITT 0 Checkpoint | Niedrig | Nur 2 cp-Befehle |
| SCHRITT 1 DB-Tabelle | Mittel | CREATE TABLE + Migration |
| SCHRITT 2 Backend Routes | Niedrig | 4 Routes + 1 Model |
| SCHRITT 3 Findings Redesign | Mittel | Tab-Nav + 3 Karten-Typen + JS |
| SCHRITT 4 Formular | Niedrig | Simples Form + Fetch |

**Gesamtaufwand: Mittel**

---

## ARTHEMIS URTEIL: BLOCKED

Kein GREENLIGHT ohne Iggy-Entscheidung.

- DB + Migration: APPROVED (Schema-stabil, SQL-only)
- API Routes: APPROVED (Standard CRUD)
- UI: APPROVED mit Einschränkung — Findings.html wird substanziell geändert, Backups zwingend
- Story-Ideen Migration: 1 Row aus agent_knowledge (story_alfred_landecker_hateaid) — minimal risk

@Apollon: Warten auf Iggy GREENLIGHT.
