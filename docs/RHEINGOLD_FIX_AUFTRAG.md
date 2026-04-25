# RHEINGOLD FIX AUFTRAG — ARTH-2026-0417-008

**Analyse Datum:** 2026-04-17 14:51  
**Service Status:** ✅ active (running), Port 5004 HTTP 200  
**DB Entities:** 1531 total (NGO: 1280, Ministerium: 89, Firma: 84, Person: 48, Verein: 30)  
**Network Graph:** 287 nodes, 267 links

---

## ISSUE 1: Fallakten öffnen nicht

### ROOT CAUSE
`entity_detail.html` existiert NICHT im Templates-Verzeichnis!  
Route `/entities/<int:entity_id>` (L36 in app.py) referenziert sie → 404 beim Öffnen einer Entity-Detailansicht.

Die Detailansicht ist bereits im DOM implementiert als **Client-Side Modal** (`detail-modal` in entities.html L98-L280), aber die separaten Detail-Route fehlt als Fallback.

### FIX für Apollon
**DATEI:** `/opt/rheingold-standalone/templates/entity_detail.html`  
**AKTION:** Neue Datei erstellen mit Entity-Template:

```html
{% extends "base.html" %}
{% block content %}
<div class="container">
  <h2>{{ entity.name }}</h2>
  <div class="detail-grid">
    <div class="detail-field"><label>Typ</label><span>{{ entity.entity_type }}</span></div>
    <div class="detail-field"><label>Adresse</label><span>{{ entity.adresse or '—' }}</span></div>
    <div class="detail-field"><label>Quelle</label><span>{{ entity.source or '—' }}</span></div>
    <div class="detail-field"><label>Priorität</label><span>{{ entity.priority_score or '—' }}</span></div>
  </div>
  {% if entity.alias %}
    <div class="detail-field"><label>Aliase</label><span>{{ entity.alias | join(', ') }}</span></div>
  {% endif %}
  <!-- Relations -->
  <h3>Beziehungen</h3>
  <ul id="relations-list"></ul>
  <!-- Funding -->
  <h3>Fördermittel</h3>
  <div id="funding-detail"></div>
</div>
{% endblock %}
```

**AUCH app.py L36-37 prüfen:** Falls `render_template('entity_detail.html', ...)` ohne Entity-Daten aufgerufen wird, muss der Route-Handler auch die Entity aus der DB laden und an das Template übergeben. Alternativ: Client-Side Modal direkt aufrufen mit `showOrgaDetail(entity_id)`.

### AUFWAND: Mittel (Neue Datei + DB-Ladelogik)

---

## ISSUE 2: "undefined" Tag im Netzwerk-Graph

### ROOT CAUSE
API antwortet mit Feldnamen `typ` (klein, kein `e`) — das Frontend erwartet `type`.

**Network API Response Struktur:**
```json
{
  "nodes": [{"gruppe":"ngo","id":"AWO...","name":"AWO...","typ":"ngo"}],
  "links": [{"source":"KulturForum...","target":"MO-Förderung...","typ":"gefördert"}]
}
```

Frontend `netzwerk.html` L150 verwendet `d.type` → `undefined`, weil das Feld `typ` heißt.

### FIX für Apollon
**DATEI:** `/opt/rheingold-standalone/templates/netzwerk.html`  

Zeile 150 ändern:
```javascript
// ALT: '<div style="margin-bottom:6px"><span class="badge badge-blue">'+d.type+'</span></div>'+
// NEU: '<div style="margin-bottom:6px"><span class="badge badge-blue">'+(d.type || d.typ || 'verbunden')+'</span></div>'+
```

Alle Stellen wo `.type` verwendet wird:
- L145: `c.type` → `(c.type || c.typ || '')`  
- L150: `d.type` → `(d.type || d.typ || 'verbunden')`  
- L156: `c.type` → `(c.type || c.typ || 'verbunden mit')`

**ODER BESSER (robust):** Im Python Backend ein Alias-Feld `type` zusätzlich zu `typ` setzen:

**DATEI:** `/opt/rheingold-standalone/app.py` (~L480 Network Route)  
Jeden Node-Dict um `'type': n.get('typ','')` ergänzen. Jeden Link-Dict um `'type': l.get('typ','')` ergänzen.

### AUFWAND: Niedrig (String-Ersetzungen oder 2 Zeilen Python)

---

## ISSUE 3: Vollbild-Layout nicht genutzt

### ANALYSE
Container sind auf `max-width: 1400px` beschränkt (base.html L51). Netzwerkgraph nutzt bereits `height: calc(100vh - 60px)` (karte.html L9) was richtig ist.

Dashboard-Kacheln verwenden CSS Grid mit `max-width: 1400px` — nicht fullscreen-tauglich.

### WENN VERBESSERUNGSWÜNSCHT
Für echten Fullscreen: `max-width:none` + `width:100vw` bei spezifischen Viewports (Netzwerk, Karte) anwenden.

### AUFWAND: Niedrig (CSS Änderungen)

---

## ISSUE 4: Filter vorhanden ABER nur client-seitig

### ANALYSE
Client-seitiger Filter existiert bereits (entities.html):
- Suchfeld (Search, Zeile 63)
- Stadt-Filter (Zeile 64)  
- Bezirks-Filter (Zeile 65)
- Stadtteil-Filter (Zeile 66)
- Type-Filter (Zeile 67-72)

ALLES passiert im Browser via JS (`renderOrgas()` in L168). Backend kennt `q` Parameter (L256) für Server-Side Search, aber keine Typ-/Stadt-Filterung per Backend.

### FIX ERFORDERLICH? NEIN — funktioniert so. Optional: Heavy-Datenfilterung server-seitig adden wenn >1000 Entities langsam im Frontend.

### AUFWAND: N/A

---

## ISSUE 5: Spidering/Scraping nicht implementiert

### ANALYSE
Keine Spider/Routes in app.py! Tabellenexistieren (`rheingold_crawl`, `rheingold_crawl_queue`, `rheingold_crawl_strategies`) aber KEINE aktive API-Routefür Spidering.

### AUFWAND: Hoch (komplette neue Feature-Implementierung)  
**NICHT im aktuellen Fix enthalten.**

---

## ZUSAMMENFASSUNG — Priorisierung

| Priority | Issue | Aufwand | Datei |
|----------|-------|---------|-------|
| P0 | "undefined" Tags im Network Graph | Niedrig | netzwerk.html |
| P1 | entity_detail.html fehlt | Mittel | entity_detail.html + app.py |
| P2 | Vollbild-Layout verbessern | Niedrig | base.html |
| P3 | Spidering implementieren | Hoch | app.py |

**Geschätzte Fix-Zeit für P0+P1+P2: ~30 Minuten**
