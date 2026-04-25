# NETZWERK V2 — APOLLON SPEC
**Report-ID:** ARTH-2026-0423-001
**Author:** Arthemis
**Scope:** Rheingold Standalone Netzwerk-Graph (`/opt/rheingold-standalone/templates/netzwerk.html` + `app.py`)
**Library:** D3 v7 (kein Wechsel zu Sigma/Cytoscape)
**Daten:** 764 Nodes, 809 Links
**Constraint:** Keine neuen npm/pip Packages. D3 v7 CDN bleibt.

---

## CHECKPOINT (IMMENS WICHTIG — IMMER ZUERST AUSFÜHREN)

```bash
cp /opt/rheingold-standalone/templates/netzwerk.html \
   /opt/rheingold-standalone/templates/netzwerk.html.bak.$(date +%Y%m%d_%H%M%S)
cp /opt/rheingold-standalone/app.py \
   /opt/rheingold-standalone/app.py.bak.$(date +%Y%m%d_%H%M%S)
```

---

## ZUSTANDSANALYSE (für Apollon — NICHT ÄNDERN, nur lesen)

| Komponente | Status |
|------------|--------|
| Graph-Library | D3 v7 via CDN |
| Renderer | `renderGraph(data)` — D3 forceSimulation, Link-Distanz 80, Charge -200, Collision 20 |
| Datenquelle | `fetch('/api/netzwerk?filter=all')` → `{nodes:[], links:[]}` |
| Node-Keys | `db_id, gruppe, id, name, typ, type` |
| Link-Keys | `source, target, typ, type` |
| Filter | Typ-Pills (9 Stück, hardcoded) + Hub-Buttons (5 Stück, hardcoded) |
| Suche | Substring auf `n.id`/`n.name`, max 8 Treffer, Dropdown, Klick zoomt auf Node + 1-Hop Nachbarn |
| Detail-Panel | Rechts oben, zeigt Verbindungen, Link zu Fallakte |
| Fallakte | Slide-in Panel rechts, ruft `/api/entities/<db_id>` + `/api/entities/<db_id>/relations` |
| **Fehlt** | Clustering, Smart-Search (Typ/Verbindung/Förderer), Fallakten-Badges, Pfadanalyse, Performance-Optimierung |

---

## PRIORISIERUNG & ROADMAP

| # | Feature | Aufwand | Visueller Impact | Video-Nützlichkeit | Gesamt | Phase |
|---|---------|---------|------------------|--------------------|--------|-------|
| 1 | **SMARTE SUCHE** | 2 | 4 | 5 | **11** | 🟢 Phase 1 |
| 2 | **CLUSTERING** | 3 | 5 | 5 | **13** | 🟢 Phase 1 |
| 3 | **FALLAKTEN-INTEGRATION** | 2 | 3 | 4 | **9** | 🟢 Phase 1 |
| 4 | **PFAD-ANALYSE** | 4 | 5 | 4 | **13** | 🟡 Phase 2 |
| 5 | **PERFORMANCE** | 4 | 3 | 3 | **10** | 🟡 Phase 2 |

**Empfehlung:** Phase 1 = Features 1+2+3 (maximaler Impact bei minimalem Aufwand). Phase 2 = Features 4+5.

---

## FEATURE 1: CLUSTERING

### Problem
764 Nodes sind visuell unstrukturiert. Der Nutzer sieht keine Gruppen. Hubs, NGOs, Politiker liegen durcheinander. Für Videos brauchen wir sofort erkennbare Strukturen ("Hier das BMFSFJ-Cluster, hier das Campact-Cluster").

### Lösung
**Zwei Cluster-Modi:**
1. **Typ-Cluster:** Nodes gruppieren nach `entity_type` (Hub, NGO, Person, Politiker, Ministerium, Firma, Verein, Stiftung, Organisation). 9 Cluster.
2. **Förderer-Cluster:** Nodes gruppieren nach Förderer (`source_name` aus `rheingold_funding`). Top-Förderer + "Sonstige".

Cluster-Center im Kreis um die Canvas-Mitte anordnen. Nodes werden durch D3 `forceX`/`forceY` zu ihrem Cluster-Center gezogen. Jeder Cluster bekommt einen transparenten Hintergrund-Kreis + Label. Klick auf Label toggelt Collapse/Expand (collapsed: nur ein Cluster-Node mit Anzahl; expanded: alle Nodes sichtbar).

### Code-Änderungen

**Datei: `/opt/rheingold-standalone/app.py`**

1. Funktion `api_network()` (Zeile ~533): Response erweitern.
   - Nach dem Enrichment-Block (Zeile ~606), füge einen Funding-Cluster-Block ein:
   ```python
   # --- CLUSTER ENRICHMENT ---
   try:
       # Get top funding sources for clustering
       cur.execute("""
           SELECT DISTINCT f.source_id, s.name
           FROM rheingold_funding f
           LEFT JOIN rheingold_entities s ON s.id = f.source_id
           WHERE f.source_id IS NOT NULL AND s.name IS NOT NULL
       """)
       funding_sources = {row[0]: row[1] for row in cur.fetchall()}
       
       # Get funding per node
       cur.execute("""
           SELECT e.name, s.name as source_name
           FROM rheingold_funding f
           JOIN rheingold_entities e ON e.id = f.entity_id
           LEFT JOIN rheingold_entities s ON s.id = f.source_id
       """)
       node_funding = {}
       for row in cur.fetchall():
           ent_name, src_name = row
           if ent_name not in node_funding:
               node_funding[ent_name] = []
           if src_name:
               node_funding[ent_name].append(src_name)
   except Exception:
       node_funding = {}
   
   # Attach to nodes
   for nid, n in nodes.items():
       n['funding_sources'] = node_funding.get(nid, [])
       n['cluster_type'] = n.get('typ', 'unknown')
       # Pick primary funding source (first one) for cluster_funder
       if n['funding_sources']:
           n['cluster_funder'] = n['funding_sources'][0]
       else:
           n['cluster_funder'] = 'Keine Förderung'
   ```
   - Die existierende `nodes` Dict wird in eine Liste umgewandelt und zurückgegeben. Stelle sicher, dass `funding_sources` und `cluster_type`/`cluster_funder` in jedem Node enthalten sind.

**Datei: `/opt/rheingold-standalone/templates/netzwerk.html`**

2. **Neue State-Variablen** (nach Zeile 191):
   ```js
   var clusterMode = 'none'; // 'none', 'type', 'funder'
   var clusterCollapsed = {}; // Map clusterKey -> bool
   var clusterCenters = {};   // Map clusterKey -> {x, y}
   ```

3. **UI-Controls** (nach dem Hub-Filter, vor `<!-- FEATURE 1: Multi-Select Typen-Filter -->`):
   ```html
   <!-- FEATURE 1: Cluster-Modus Switcher -->
   <div style="margin-bottom:8px;display:flex;flex-wrap:wrap;gap:6px;align-items:center">
     <span class="section-label">Cluster</span>
     <button class="hub-btn active" onclick="setClusterMode('none')" id="cluster-none">Aus</button>
     <button class="hub-btn" onclick="setClusterMode('type')" id="cluster-type">Nach Typ</button>
     <button class="hub-btn" onclick="setClusterMode('funder')" id="cluster-funder">Nach Förderer</button>
   </div>
   ```
   (Wiederverwendung der `.hub-btn` Klasse ist OK, da gleiches Styling gewünscht.)

4. **Funktion `setClusterMode(mode)`** (nach `filterHub`, vor `applyFilters`):
   ```js
   function setClusterMode(mode) {
     clusterMode = mode;
     document.querySelectorAll('[id^="cluster-"]').forEach(function(b) { b.classList.remove('active'); });
     document.getElementById('cluster-' + mode).classList.add('active');
     applyFilters();
   }
   ```

5. **Funktion `computeClusterCenters(data, mode)`** (neu, vor `renderGraph`):
   ```js
   function computeClusterCenters(data, mode) {
     if (mode === 'none') return {};
     var keys = new Set();
     data.nodes.forEach(function(n) {
       var key = (mode === 'type') ? (n.cluster_type || n.typ || 'unknown')
                                   : (n.cluster_funder || 'Keine Förderung');
       keys.add(key);
     });
     var arr = Array.from(keys).sort();
     var radius = Math.min(width, height) * 0.35;
     var centers = {};
     arr.forEach(function(key, i) {
       var angle = (2 * Math.PI * i) / arr.length - Math.PI / 2;
       centers[key] = {
         x: width / 2 + radius * Math.cos(angle),
         y: height / 2 + radius * Math.sin(angle),
         label: key,
         count: 0
       };
     });
     data.nodes.forEach(function(n) {
       var key = (mode === 'type') ? (n.cluster_type || n.typ || 'unknown')
                                   : (n.cluster_funder || 'Keine Förderung');
       if (centers[key]) centers[key].count++;
     });
     return centers;
   }
   ```

6. **Funktion `renderClusterBackgrounds(centers)`** (neu, nach `renderGraph` oder innerhalb):
   Innerhalb `renderGraph`, nach `g.selectAll('*').remove()`:
   ```js
   // Render cluster backgrounds
   if (clusterMode !== 'none') {
     var clusterData = Object.values(clusterCenters).filter(function(c) { return c.count > 0; });
     var clusterGroups = g.append('g').attr('class', 'clusters')
       .selectAll('g').data(clusterData).join('g');
     
     clusterGroups.append('circle')
       .attr('cx', function(d) { return d.x; })
       .attr('cy', function(d) { return d.y; })
       .attr('r', function(d) { return 60 + Math.sqrt(d.count) * 5; })
       .attr('fill', 'rgba(30,58,95,0.15)')
       .attr('stroke', 'rgba(100,148,199,0.3)')
       .attr('stroke-width', 1)
       .attr('stroke-dasharray', '4,4')
       .style('pointer-events', 'none');
     
     clusterGroups.append('text')
       .attr('x', function(d) { return d.x; })
       .attr('y', function(d) { return d.y - 70 - Math.sqrt(d.count) * 5; })
       .attr('text-anchor', 'middle')
       .style('font-size', '12px')
       .style('font-weight', '600')
       .style('fill', '#64748b')
       .style('pointer-events', 'none')
       .text(function(d) { return d.label + ' (' + d.count + ')'; });
   }
   ```

7. **Simulation-Forces anpassen** (innerhalb `renderGraph`):
   Ersetze die bestehende Simulation durch:
   ```js
   var simulation = d3.forceSimulation(data.nodes)
     .alphaDecay(0.05)
     .alphaMin(0.001)
     .force('link', d3.forceLink(data.links).id(function(d){return d.id;}).distance(60))
     .force('charge', d3.forceManyBody().strength(-150));
   
   if (clusterMode !== 'none') {
     simulation
       .force('center', null) // Deaktiviere Center-Force im Cluster-Modus
       .force('clusterX', d3.forceX(function(d) {
         var key = (clusterMode === 'type') ? (d.cluster_type || d.typ || 'unknown')
                                            : (d.cluster_funder || 'Keine Förderung');
         return (clusterCenters[key] || {}).x || width/2;
       }).strength(0.4))
       .force('clusterY', d3.forceY(function(d) {
         var key = (clusterMode === 'type') ? (d.cluster_type || d.typ || 'unknown')
                                            : (d.cluster_funder || 'Keine Förderung');
         return (clusterCenters[key] || {}).y || height/2;
       }).strength(0.4))
       .force('collision', d3.forceCollide().radius(15));
   } else {
     simulation
       .force('center', d3.forceCenter(width/2, height/2))
       .force('collision', d3.forceCollide().radius(20));
   }
   ```

8. **Collapse/Expand Logik** (optional, falls Zeit reicht):
   Wenn `clusterCollapsed[key] === true`, filtere alle Nodes dieses Clusters aus `data.nodes` heraus (bevor sie an die Simulation übergeben werden). Füge stattdessen einen Meta-Node ein:
   ```js
   // Pseudocode für Collapse
   // In applyFilters oder vor renderGraph:
   if (clusterMode !== 'none') {
     var visibleNodes = [];
     data.nodes.forEach(function(n) {
       var key = (clusterMode === 'type') ? (n.cluster_type || n.typ) : (n.cluster_funder || 'Keine Förderung');
       if (!clusterCollapsed[key]) {
         visibleNodes.push(n);
       }
     });
     // Füge Meta-Nodes für collapsed Cluster hinzu
     Object.keys(clusterCollapsed).forEach(function(key) {
       if (clusterCollapsed[key] && clusterCenters[key]) {
         visibleNodes.push({
           id: '__cluster_' + key,
           name: key + ' (' + clusterCenters[key].count + ')',
           typ: 'cluster',
           x: clusterCenters[key].x,
           y: clusterCenters[key].y,
           fx: clusterCenters[key].x,
           fy: clusterCenters[key].y,
           _clusterKey: key
         });
       }
     });
     data.nodes = visibleNodes;
   }
   ```
   **WICHTIG:** Diese Collapse/Expand-Logik ist komplex. Wenn Zeit knapp ist, **zuerst ohne Collapse implementieren**. Cluster-Hintergründe + ForceX/Y reichen für den visuellen Impact.

### Test
1. Seite laden → "Cluster: Aus" ist aktiv → Graph verhält sich wie bisher.
2. "Cluster: Nach Typ" klicken → Nodes gruppieren sich in 9 Bereichen. Hintergrund-Kreise sichtbar.
3. "Cluster: Nach Förderer" klicken → Nodes gruppieren sich nach Förderern. BMFSFJ-Cluster sichtbar.
4. Hub-Filter + Cluster-Modus kombinieren → Kein Crash.
5. Suche + Cluster-Modus → Zoom funktioniert trotzdem.

---

## FEATURE 2: SMARTE SUCHE

### Problem
Aktuelle Suche ist primitiv: Nur Substring auf Name, max 8 Treffer. Keine Suche nach Typ ("zeig mir alle Hubs"), kein Förderer-Filter ("alle BMFSFJ-Geförderten"), keine Verbindungs-Suche ("Campact-Nachbarn").

### Lösung
Query-Syntax im Suchfeld:
- `hub` → zeigt alle Nodes mit Typ `hub` (wie bisher, aber mit Typ-Erkennung)
- `typ:hub` → explizit nach Typ filtern
- `foerderer:bmfsfj` → zeigt alle Nodes, die BMFSFJ-Förderung haben
- `campact` → Substring-Suche wie bisher
- `campact verbindungen` → zeigt Campact + alle direkten Nachbarn

Autocomplete zeigt Kategorien:
- 🔍 Name: Campact e.V.
- 🏷 Typ: hub
- 💰 Förderer: BMFSFJ

Graph reagiert:
- Ein Treffer → Zoom auf Node + 1-Hop Nachbarn (wie bisher)
- Mehrere Treffer → Zoom auf Bounding-Box aller Treffer + Nachbarn
- Alle nicht-Treffer ausgrauen (opacity 0.15)
- Treffer bekommen gelben Glow (CSS-Filter oder dickerer Stroke)

### Code-Änderungen

**Datei: `/opt/rheingold-standalone/app.py`**

1. Funktion `api_network()` (Zeile ~533): `funding_sources` ist bereits durch FEATURE 1 im Node enthalten. Keine weiteren Änderungen nötig.

**Datei: `/opt/rheingold-standalone/templates/netzwerk.html`**

2. **Suchbox Placeholder ändern** (Zeile 147):
   ```html
   <input id="search-box" type="text" placeholder="Suche: Name, typ:hub, foerderer:bmfsfj..." autocomplete="off">
   ```

3. **Funktion `performSearch(query)` ersetzen** (Zeile 415):
   ```js
   function performSearch(query) {
     if (!fullData) return;
     var q = query.toLowerCase().trim();
     if (q.length < 2) {
       searchDropdown.style.display = 'none';
       return;
     }
     
     // Parse query
     var mode = 'name'; // name | typ | foerderer | connections
     var term = q;
     var m = q.match(/^(typ|foerderer):\s*(.+)$/);
     if (m) {
       mode = m[1];
       term = m[2].trim();
     } else if (q.indexOf(' verbindungen') !== -1 || q.indexOf(' nachbarn') !== -1) {
       mode = 'connections';
       term = q.replace(/ verbindungen| nachbarn/g, '').trim();
     }
     
     var results = [];
     if (mode === 'typ') {
       fullData.nodes.forEach(function(n) {
         if ((n.typ || n.type || '').toLowerCase() === term) {
           results.push(n);
         }
       });
     } else if (mode === 'foerderer') {
       fullData.nodes.forEach(function(n) {
         var sources = n.funding_sources || [];
         if (sources.some(function(s) { return s.toLowerCase().indexOf(term) !== -1; })) {
           results.push(n);
         }
       });
     } else if (mode === 'connections') {
       // Find node by name, then add neighbors
       var centerNode = null;
       fullData.nodes.forEach(function(n) {
         if ((n.name || n.id).toLowerCase().indexOf(term) !== -1) {
           centerNode = n;
         }
       });
       if (centerNode) {
         results.push(centerNode);
         fullData.links.forEach(function(l) {
           var srcId = typeof l.source === 'object' ? l.source.id : l.source;
           var tgtId = typeof l.target === 'object' ? l.target.id : l.target;
           if (srcId === centerNode.id) {
             var neighbor = fullData.nodes.find(function(n) { return n.id === tgtId; });
             if (neighbor) results.push(neighbor);
           } else if (tgtId === centerNode.id) {
             var neighbor = fullData.nodes.find(function(n) { return n.id === srcId; });
             if (neighbor) results.push(neighbor);
           }
         });
       }
     } else {
       // Name search (substring)
       fullData.nodes.forEach(function(n) {
         var label = (n.name || n.id || '').toLowerCase();
         if (label.indexOf(term) !== -1) {
           results.push(n);
           if (results.length >= 8) return;
         }
       });
     }
     
     results = results.slice(0, 12);
     
     // Build dropdown HTML
     if (results.length === 0) {
       searchDropdown.innerHTML = '<div class="no-results">Keine Ergebnisse für "' + escHtml(query) + '"</div>';
     } else {
       var html = '';
       results.forEach(function(n) {
         var t = n.typ || n.type || '';
         var badge = '';
         if (mode === 'typ') badge = '🏷 Typ';
         else if (mode === 'foerderer') badge = '💰 Förderung';
         else if (mode === 'connections') badge = '🔗 Nachbarn';
         else badge = '🔍 Name';
         html += '<div class="search-item" onclick="focusNodeMulti([\'' + escAttr(n.id) + '\'])\">';
         html += '<span>' + escHtml(n.name || n.id) + '</span>';
         html += '<span class="s-type">' + badge + ' · ' + escHtml(t) + '</span>';
         html += '</div>';
       });
       // Add "Zeige alle" option for typ/foerderer searches
       if (mode === 'typ' || mode === 'foerderer') {
         html += '<div class="search-item" style="border-top:1px solid #334155;font-weight:600;color:#f59e0b;" onclick="focusNodeMulti([\'__ALL_RESULTS__\'])">Zeige alle ' + results.length + ' im Graph</div>';
       }
       searchDropdown.innerHTML = html;
     }
     searchDropdown.style.display = 'block';
   }
   ```

4. **Neue Funktion `focusNodeMulti(nodeIds)`** (nach `focusNode`):
   ```js
   function focusNodeMulti(nodeIds) {
     searchDropdown.style.display = 'none';
     searchBox.value = '';
     if (!fullData) return;
     
     // Reset filters
     activeHub = null;
     document.querySelectorAll('.hub-btn').forEach(function(b) { b.classList.remove('active'); });
     document.getElementById('hub-all').classList.add('active');
     
     var targetIds = new Set();
     var neighborIds = new Set();
     
     if (nodeIds.length === 1 && nodeIds[0] === '__ALL_RESULTS__') {
       // This is a hack — we need to store the last search results globally.
       // Better: pass all result IDs directly.
       // Simpler: don't use __ALL_RESULTS__. Instead, the "Zeige alle" option
       // should call a different function with the actual IDs.
       // CORRECTION: The onclick above is wrong. Better approach:
       // Store lastResults globally.
       return; // Will be implemented via lastResults below.
     }
     
     nodeIds.forEach(function(id) {
       targetIds.add(id);
       neighborIds.add(id);
       fullData.links.forEach(function(l) {
         var srcId = typeof l.source === 'object' ? l.source.id : l.source;
         var tgtId = typeof l.target === 'object' ? l.target.id : l.target;
         if (srcId === id) neighborIds.add(tgtId);
         if (tgtId === id) neighborIds.add(srcId);
       });
     });
     
     var filteredNodes = fullData.nodes.filter(function(n) { return neighborIds.has(n.id); });
     var filteredLinks = fullData.links.filter(function(l) {
       var srcId = typeof l.source === 'object' ? l.source.id : l.source;
       var tgtId = typeof l.target === 'object' ? l.target.id : l.target;
       return neighborIds.has(srcId) && neighborIds.has(tgtId);
     });
     
     // Mark target nodes for highlighting
     filteredNodes.forEach(function(n) {
       n._searchTarget = targetIds.has(n.id);
     });
     filteredLinks.forEach(function(l) {
       var srcId = typeof l.source === 'object' ? l.source.id : l.source;
       var tgtId = typeof l.target === 'object' ? l.target.id : l.target;
       l._searchLink = targetIds.has(srcId) || targetIds.has(tgtId);
     });
     
     renderGraph({nodes: filteredNodes, links: filteredLinks});
     
     // Zoom to bounding box of targets
     setTimeout(function() {
       var targets = filteredNodes.filter(function(n) { return n._searchTarget; });
       if (targets.length === 0) return;
       var minX = d3.min(targets, function(n) { return n.x; });
       var maxX = d3.max(targets, function(n) { return n.x; });
       var minY = d3.min(targets, function(n) { return n.y; });
       var maxY = d3.max(targets, function(n) { return n.y; });
       var midX = (minX + maxX) / 2;
       var midY = (minY + maxY) / 2;
       var scale = Math.min(3, 0.8 / Math.max((maxX - minX) / width, (maxY - minY) / height));
       if (!isFinite(scale) || scale > 3) scale = 1.5;
       var transform = d3.zoomIdentity
         .translate(width/2 - midX * scale, height/2 - midY * scale)
         .scale(scale);
       svg.transition().duration(600).call(d3.zoom().transform, transform);
     }, 1200);
   }
   ```

5. **Globale Variable `lastSearchResults`:**
   ```js
   var lastSearchResults = []; // Array of node objects
   ```
   In `performSearch`, vor dem HTML-Building: `lastSearchResults = results;`
   Das Dropdown-HTML für "Zeige alle" ändern zu:
   ```js
   html += '<div class="search-item" style="border-top:1px solid #334155;font-weight:600;color:#f59e0b;" onclick="focusAllLastResults()">Zeige alle ' + results.length + ' im Graph</div>';
   ```
   Und `focusAllLastResults`:
   ```js
   function focusAllLastResults() {
     searchDropdown.style.display = 'none';
     searchBox.value = '';
     if (!lastSearchResults.length) return;
     var ids = lastSearchResults.map(function(n) { return n.id; });
     focusNodeMulti(ids);
   }
   ```
   **Hinweis:** `focusNodeMulti` muss so umgeschrieben werden, dass es mit einer Menge von IDs umgehen kann (siehe oben, das ist bereits der Fall).

6. **Visual Highlighting in `renderGraph`:**
   - Node-Circle (Zeile ~367):
     ```js
     node.append('circle')
       .attr('r', function(d){ return d._hubRadius || getNodeRadius(d); })
       .attr('fill', function(d){ return d._hubColor || getNodeColor(d); })
       .attr('stroke', function(d) { return d._searchTarget ? '#fbbf24' : 'var(--bg)'; })
       .attr('stroke-width', function(d) { return d._searchTarget ? 4 : 2; });
     ```
   - Non-target Nodes ausgrauen:
     ```js
     node.style('opacity', function(d) {
       return d._searchTarget ? 1 : (d._searchNeighbor ? 0.6 : 0.2);
     });
     link.style('opacity', function(d) {
       return d._searchLink ? 1 : 0.1;
     });
     ```
     Dafür müssen wir in `focusNodeMulti` auch `_searchNeighbor` setzen:
     ```js
     filteredNodes.forEach(function(n) {
       n._searchTarget = targetIds.has(n.id);
       n._searchNeighbor = neighborIds.has(n.id) && !targetIds.has(n.id);
     });
     ```

### Test
1. Suche "campact" → Dropdown zeigt Campact + ähnliche Namen.
2. Klick auf Campact → Zoom auf Campact + Nachbarn. Campact hat goldenen Rand, Nachbarn sind halbtransparent, Rest ist versteckt.
3. Suche "typ:hub" → Dropdown zeigt alle Hubs. "Zeige alle" klicken → Graph zeigt nur Hubs.
4. Suche "foerderer:bmfsfj" → Dropdown zeigt alle BMFSFJ-geförderten Nodes.
5. Suche "campact verbindungen" → Dropdown zeigt Campact + Nachbarn.
6. Leeres Suchfeld → Dropdown verschwindet.

---

## FEATURE 3: FALLAKTEN-INTEGRATION

### Problem
Nodes mit Fallakten sind im Graph nicht visuell erkennbar. Der Nutzer muss auf jeden Node klicken, um zu sehen, ob eine Fallakte existiert. Für Videos brauchen wir ein sofortiges Signal: "Diese Person/Organisation hat eine Fallakte".

### Lösung
1. **Badge auf Node:** Nodes mit `has_fallakte === true` bekommen einen kleinen goldenen Stern (⭐ oder SVG-Star) als Badge oben rechts auf dem Node-Circle.
2. **Detail-Panel:** Zeigt Badge "🕵️ Fallakte verfügbar" zusammen mit dem "→ Fallakte öffnen" Link.
3. **Klick:** Wie bisher — Detail-Panel öffnet sich, Link zur Fallakte ist da. Kein neues Popup nötig.

### Code-Änderungen

**Datei: `/opt/rheingold-standalone/app.py`**

1. Funktion `api_network()` (Zeile ~533): Erweitere den Enrichment-Block.
   Nach dem Funding-Block (siehe FEATURE 1), füge hinzu:
   ```python
   # --- FALLAKTE ENRICHMENT ---
   try:
       cur.execute("""
           SELECT DISTINCT org_name FROM rheingold_findings
           WHERE org_name IS NOT NULL
       """)
       finding_names = {row[0] for row in cur.fetchall()}
       
       for nid, n in nodes.items():
           # Check if any finding matches this node name (case-insensitive substring)
           n['has_fallakte'] = any(
               nid.lower() in fname.lower() or fname.lower() in nid.lower()
               for fname in finding_names
           )
   except Exception:
       for nid, n in nodes.items():
           n['has_fallakte'] = False
   ```
   **WICHTIG:** Die substring-Matching-Logik ist heuristisch. Wenn `rheingold_findings.org_name` exakte Namen enthält, kann man auch `nid in finding_names` prüfen. Aktuell ist substring sicherer für unterschiedliche Schreibweisen.

**Datei: `/opt/rheingold-standalone/templates/netzwerk.html`**

2. **Badge im Node-Rendering** (innerhalb `renderGraph`, nach dem Circle-Append):
   ```js
   // Fallakte Badge
   node.filter(function(d) { return d.has_fallakte; })
     .append('path')
     .attr('d', 'M0,-12 L3,-4 L11,-4 L5,1 L7,9 L0,4 L-7,9 L-5,1 L-11,-4 L-3,-4 Z') // Star shape
     .attr('transform', 'translate(' + (getNodeRadius({}) + 6) + ',-' + (getNodeRadius({}) + 6) + ') scale(0.6)')
     .attr('fill', '#fbbf24')
     .attr('stroke', '#0f172a')
     .attr('stroke-width', 1);
   ```
   **Problem:** `getNodeRadius({})` funktioniert nicht statisch. Besser:
   ```js
   node.each(function(d) {
     if (d.has_fallakte) {
       var r = d._hubRadius || getNodeRadius(d);
       d3.select(this).append('path')
         .attr('d', 'M0,-12 L3,-4 L11,-4 L5,1 L7,9 L0,4 L-7,9 L-5,1 L-11,-4 L-3,-4 Z')
         .attr('transform', 'translate(' + (r + 4) + ',-' + (r + 4) + ') scale(0.5)')
         .attr('fill', '#fbbf24')
         .attr('stroke', '#0f172a')
         .attr('stroke-width', 1.5);
     }
   });
   ```

3. **Detail-Panel erweitern** (in `showDetail`, vor dem HTML-Building):
   ```js
   var fallakteBadge = (d.has_fallakte)
     ? '<div style="margin-bottom:8px"><span style="background:#fbbf24;color:#0f172a;padding:2px 8px;border-radius:4px;font-size:11px;font-weight:600;">🕵️ Fallakte verfügbar</span></div>'
     : '';
   ```
   Und im HTML-String einfügen:
   ```js
   var html = '<h3>'+d.id+'</h3>'+
     fallakteBadge +
     '<div style="margin-bottom:6px"><span class="badge badge-blue">'+(d.type || d.typ || 'verbunden')+'</span></div>'+
     ...
   ```

### Test
1. Seite laden → Einige Nodes haben goldenen Stern.
2. Klick auf Node mit Stern → Detail-Panel zeigt "🕵️ Fallakte verfügbar".
3. Klick auf Node ohne Stern → Kein Badge.
4. Stern-Position passt sich Node-Radius an (kleine Nodes = Stern näher, große Nodes = Stern weiter außen).

---

## FEATURE 4: PFAD-ANALYSE

### Problem
Keine Möglichkeit, die Verbindungskette zwischen zwei Nodes zu sehen. Beispiel: "Wie ist Campact mit der ALF verbunden?" → Manuell durch den Graph zu navigieren ist unmöglich bei 764 Nodes.

### Lösung
UI für Node-Auswahl:
1. Zwei Suchfelder (oder Klick-Modus): "Von" und "Nach".
2. BFS clientseitig auf `fullData.links` (ungerichtet).
3. Visualisierung:
   - Nur Pfad-Nodes und -Links anzeigen, Rest ausgegraut (opacity 0.08).
   - Pfad-Links: Dick, rot (#ef4444), animiert (CSS `stroke-dasharray` Animation).
   - Pfad-Nodes: Größer, goldener Ring.
   - Info-Box oben links: "Campact → HateAid → ALF (2 Schritte)".
4. Wenn kein Pfad: Info-Box zeigt "Kein direkter Pfad gefunden".

### Code-Änderungen

**Datei: `/opt/rheingold-standalone/templates/netzwerk.html`**

1. **UI-Controls** (nach dem Cluster-Switcher oder nach Hub-Filter):
   ```html
   <!-- FEATURE 4: Pfad-Analyse -->
   <div id="path-analysis" style="margin-bottom:8px;display:none;flex-wrap:wrap;gap:6px;align-items:center;background:#1e293b;border:1px solid #334155;padding:8px 12px;border-radius:8px;">
     <span class="section-label">Pfad</span>
     <input id="path-from" type="text" placeholder="Von..." style="background:#0f172a;border:1px solid #334155;border-radius:6px;padding:4px 8px;font-size:12px;color:#e2e8f0;width:140px;">
     <span style="color:#64748b">→</span>
     <input id="path-to" type="text" placeholder="Nach..." style="background:#0f172a;border:1px solid #334155;border-radius:6px;padding:4px 8px;font-size:12px;color:#e2e8f0;width:140px;">
     <button class="action-btn" onclick="findPath()">Finden</button>
     <button class="action-btn" onclick="clearPath()" style="color:#ef4444;border-color:#ef4444;">✕</button>
     <span id="path-result" style="font-size:12px;color:#e2e8f0;margin-left:8px;"></span>
   </div>
   <button class="hub-btn" onclick="togglePathAnalysis()" id="btn-path-toggle">🛤 Pfad-Analyse</button>
   ```

2. **Toggle-Funktion**:
   ```js
   function togglePathAnalysis() {
     var panel = document.getElementById('path-analysis');
     panel.style.display = (panel.style.display === 'flex') ? 'none' : 'flex';
     document.getElementById('btn-path-toggle').classList.toggle('active');
   }
   ```

3. **BFS-Algorithmus** (neu):
   ```js
   function findShortestPath(startId, endId) {
     if (!fullData || startId === endId) return null;
     
     // Build adjacency list
     var adj = {};
     fullData.nodes.forEach(function(n) { adj[n.id] = []; });
     fullData.links.forEach(function(l) {
       var src = typeof l.source === 'object' ? l.source.id : l.source;
       var tgt = typeof l.target === 'object' ? l.target.id : l.target;
       if (adj[src]) adj[src].push({node: tgt, link: l});
       if (adj[tgt]) adj[tgt].push({node: src, link: l});
     });
     
     var queue = [[startId]];
     var visited = new Set([startId]);
     
     while (queue.length > 0) {
       var path = queue.shift();
       var current = path[path.length - 1];
       if (current === endId) return path;
       
       (adj[current] || []).forEach(function(edge) {
         if (!visited.has(edge.node)) {
           visited.add(edge.node);
           var newPath = path.slice();
           newPath.push(edge.node);
           queue.push(newPath);
         }
       });
     }
     return null;
   }
   ```

4. **`findPath()` und `clearPath()`**:
   ```js
   function findPath() {
     var fromVal = document.getElementById('path-from').value.trim();
     var toVal = document.getElementById('path-to').value.trim();
     if (!fromVal || !toVal) return;
     
     // Resolve names to IDs (substring match)
     var fromId = null, toId = null;
     fullData.nodes.forEach(function(n) {
       if ((n.name || n.id).toLowerCase().indexOf(fromVal.toLowerCase()) !== -1 && !fromId) fromId = n.id;
       if ((n.name || n.id).toLowerCase().indexOf(toVal.toLowerCase()) !== -1 && !toId) toId = n.id;
     });
     
     if (!fromId || !toId) {
       document.getElementById('path-result').textContent = 'Nodes nicht gefunden';
       return;
     }
     
     var path = findShortestPath(fromId, toId);
     if (!path) {
       document.getElementById('path-result').textContent = 'Kein Pfad gefunden';
       return;
     }
     
     var pathSet = new Set(path);
     var pathEdges = new Set();
     for (var i = 0; i < path.length - 1; i++) {
       fullData.links.forEach(function(l) {
         var src = typeof l.source === 'object' ? l.source.id : l.source;
         var tgt = typeof l.target === 'object' ? l.target.id : l.target;
         if ((src === path[i] && tgt === path[i+1]) || (src === path[i+1] && tgt === path[i])) {
           pathEdges.add(l); // Note: objects can't be in Sets reliably. Use index or string key.
         }
       });
     }
     
     // Better: mark path links by index
     var pathLinkIndices = new Set();
     fullData.links.forEach(function(l, idx) {
       var src = typeof l.source === 'object' ? l.source.id : l.source;
       var tgt = typeof l.target === 'object' ? l.target.id : l.target;
       for (var i = 0; i < path.length - 1; i++) {
         if ((src === path[i] && tgt === path[i+1]) || (src === path[i+1] && tgt === path[i])) {
           pathLinkIndices.add(idx);
         }
       }
     });
     
     // Render full graph but mark path
     fullData.nodes.forEach(function(n) {
       n._pathNode = pathSet.has(n.id);
     });
     fullData.links.forEach(function(l, idx) {
       l._pathLink = pathLinkIndices.has(idx);
     });
     
     renderGraph(fullData);
     
     var label = path.map(function(id) {
       var n = fullData.nodes.find(function(x) { return x.id === id; });
       return n ? (n.name || n.id) : id;
     }).join(' → ');
     document.getElementById('path-result').innerHTML = '<span style="color:#fbbf24">' + label + '</span> (' + (path.length - 1) + ' Schritte)';
   }
   
   function clearPath() {
     document.getElementById('path-from').value = '';
     document.getElementById('path-to').value = '';
     document.getElementById('path-result').textContent = '';
     if (fullData) {
       fullData.nodes.forEach(function(n) { delete n._pathNode; });
       fullData.links.forEach(function(l) { delete l._pathLink; });
       applyFilters();
     }
   }
   ```

5. **Visual Highlighting in `renderGraph`**:
   - Nodes:
     ```js
     node.style('opacity', function(d) {
       if (d._pathNode) return 1;
       if (d._searchTarget !== undefined) return d._searchTarget ? 1 : 0.2;
       return 1;
     });
     node.selectAll('circle')
       .attr('stroke', function(d) {
         if (d._pathNode) return '#ef4444';
         if (d._searchTarget) return '#fbbf24';
         return 'var(--bg)';
       })
       .attr('stroke-width', function(d) {
         if (d._pathNode) return 4;
         if (d._searchTarget) return 4;
         return 2;
       });
     ```
   - Links:
     ```js
     link.attr('stroke-width', function(d) { return d._pathLink ? 3 : 1.5; })
         .attr('stroke', function(d) {
           if (d._pathLink) return '#ef4444';
           return linkColors[d.typ] || '#334155';
         })
         .style('opacity', function(d) {
           if (d._pathLink) return 1;
           if (d._searchLink !== undefined) return d._searchLink ? 1 : 0.1;
           return 0.4;
         });
     // Animated dash for path links
     link.filter(function(d) { return d._pathLink; })
       .attr('stroke-dasharray', '8,4')
       .append('animate') // SVG animate element
       .attr('attributeName', 'stroke-dashoffset')
       .attr('from', 12)
       .attr('to', 0)
       .attr('dur', '1s')
       .attr('repeatCount', 'indefinite');
     ```

### Test
1. Pfad-Analyse öffnen.
2. "Von: Campact", "Nach: ALF" → Klick "Finden".
3. Graph zeigt nur Pfad rot hervorgehoben. Info-Box zeigt "Campact → ... → ALF (X Schritte)".
4. "✕" klicken → Graph zurück zur normalen Ansicht.
5. Nicht existierende Nodes → "Nodes nicht gefunden".
6. Kein Pfad → "Kein Pfad gefunden".

---

## FEATURE 5: PERFORMANCE

### Problem
764 Nodes rendern auf einmal. D3 forceSimulation braucht lange zum Settlen. Browser kann laggen, besonders auf schwächerer Hardware. Labels überlappen sich beim Herauszoomen.

### Lösung
**Level-of-Detail (LoD)** basierend auf Zoom-Level:
- Zoom < 0.6: Nur Hubs + Top-20 Nodes nach `score` (oder `priority_score` falls verfügbar). Labels ausgeblendet.
- Zoom 0.6–1.5: Alle Nodes, Labels nur für Hubs und Nodes mit `score > 50`.
- Zoom > 1.5: Alle Labels sichtbar.

**Ego-Modus:**
- Toggle-Button "🎯 Ego-Modus". Wenn aktiv und ein Node fokussiert (via Suche oder Klick), zeige nur 1-Hop-Nachbarn. Slider für 1–3 Hops.
- Wenn kein Node fokussiert, zeige Top-50 Nodes (nach Score).

**Force-Simulation Tuning:**
- `alphaDecay(0.05)` beibehalten, aber `velocityDecay(0.3)` hinzufügen (schnelleres Settling).
- `requestAnimationFrame` Throttling: Aktuell macht D3 das intern. Keine Änderung nötig.

### Code-Änderungen

**Datei: `/opt/rheingold-standalone/templates/netzwerk.html`**

1. **Neue State-Variablen**:
   ```js
   var egoMode = false;
   var egoHops = 1;
   var focusedNodeId = null;
   ```

2. **UI-Controls** (nach Pfad-Analyse oder Cluster):
   ```html
   <div style="margin-bottom:8px;display:flex;flex-wrap:wrap;gap:6px;align-items:center">
     <span class="section-label">Performance</span>
     <button class="hub-btn" onclick="toggleEgoMode()" id="btn-ego">🎯 Ego-Modus</button>
     <select id="ego-hops" onchange="setEgoHops(this.value)" style="background:#0f172a;border:1px solid #334155;border-radius:6px;padding:4px 8px;font-size:12px;color:#e2e8f0;display:none;">
       <option value="1">1 Hop</option>
       <option value="2">2 Hops</option>
       <option value="3">3 Hops</option>
     </select>
   </div>
   ```

3. **Toggle-Funktionen**:
   ```js
   function toggleEgoMode() {
     egoMode = !egoMode;
     document.getElementById('btn-ego').classList.toggle('active', egoMode);
     document.getElementById('ego-hops').style.display = egoMode ? 'inline-block' : 'none';
     applyFilters();
   }
   function setEgoHops(h) {
     egoHops = parseInt(h);
     if (egoMode && focusedNodeId) applyFilters();
   }
   ```

4. **Zoom-Handler erweitern** (Zeile 172, Zoom-Definition):
   ```js
   svg.call(d3.zoom().scaleExtent([0.3,5]).on('zoom', function(e){
     g.attr('transform', e.transform);
     updateLOD(e.transform.k);
   }));
   ```

5. **LOD-Funktion** (neu):
   ```js
   function updateLOD(scale) {
     if (!fullData) return;
     // Hide/show labels based on zoom
     if (scale < 0.6) {
       g.selectAll('.node text').style('display', 'none');
     } else if (scale < 1.5) {
       g.selectAll('.node text').style('display', function(d) {
         return (d.typ === 'hub' || (d.score || 0) > 50) ? 'block' : 'none';
       });
     } else {
       g.selectAll('.node text').style('display', 'block');
     }
   }
   ```

6. **Ego-Filter in `applyFilters`** (erweitern):
   Nach dem Hub-Filter-Block, vor `renderGraph`:
   ```js
   // Ego-Mode Filter
   if (egoMode && focusedNodeId) {
     var allowedIds = new Set();
     allowedIds.add(focusedNodeId);
     
     // BFS for N hops
     var frontier = new Set([focusedNodeId]);
     for (var hop = 0; hop < egoHops; hop++) {
       var nextFrontier = new Set();
       frontier.forEach(function(fid) {
         fullData.links.forEach(function(l) {
           var srcId = typeof l.source === 'object' ? l.source.id : l.source;
           var tgtId = typeof l.target === 'object' ? l.target.id : l.target;
           if (srcId === fid) { allowedIds.add(tgtId); nextFrontier.add(tgtId); }
           if (tgtId === fid) { allowedIds.add(srcId); nextFrontier.add(srcId); }
         });
       });
       frontier = nextFrontier;
     }
     
     filteredNodes = filteredNodes.filter(function(n) { return allowedIds.has(n.id); });
     var finalIds = new Set(filteredNodes.map(function(n) { return n.id; }));
     filteredLinks = filteredLinks.filter(function(l) {
       var srcId = typeof l.source === 'object' ? l.source.id : l.source;
       var tgtId = typeof l.target === 'object' ? l.target.id : l.target;
       return finalIds.has(srcId) && finalIds.has(tgtId);
     });
   }
   ```

7. **Node-Klick setzt `focusedNodeId`**:
   In `renderGraph`, Node-Click-Handler (Zeile 360):
   ```js
   .on('click', function(e,d){
     focusedNodeId = d.id;
     showDetail(d);
     if(d.db_id||d.id) openFallakte(d.db_id||d.id);
   })
   ```

### Test
1. Seite laden → Alle 764 Nodes sichtbar.
2. Herauszoomen (Zoom < 0.6) → Labels verschwinden.
3. "Ego-Modus" aktivieren → Graph zeigt nur Top-50 Nodes (da noch kein Node fokussiert).
4. Auf Node klicken → Graph zeigt nur 1-Hop-Nachbarn.
5. Dropdown auf "2 Hops" → Mehr Nachbarn erscheinen.
6. Ego-Modus deaktivieren → Alle Nodes wieder sichtbar.

---

## ARCHITEKTUR-DIAGRAMM (Data Flow)

```
┌─────────────────┐      fetch('/api/netzwerk?filter=all')      ┌─────────────────┐
│  netzwerk.html  │ ◄────────────────────────────────────────── │     app.py      │
│   (D3 v7)       │        {nodes:[], links:[]}                │  /api/netzwerk  │
└────────┬────────┘                                              └─────────────────┘
         │
         ▼
┌─────────────────┐
│   fullData      │  ← Rohdaten (immutable)
└────────┬────────┘
         │
         ├─► applyFilters() ──► filteredNodes/links
         │
         ├─► renderGraph(data) ──► D3 forceSimulation
         │
         ├─► focusNode() / focusNodeMulti() ──► Zoom + Highlight
         │
         ├─► findShortestPath() ──► BFS clientseitig
         │
         └─► openFallakte() ──► fetch('/api/entities/<id>')
```

---

## SICHERHEIT & PERFORMANCE HINWEISE

1. **Keine SQL-Injection:** `api_network()` verwendet keine user-input in SQL (außer `filter_val` was hardcoded geprüft wird). Beibehalten.
2. **XSS:** `escHtml()` und `escAttr()` existieren. In allen neuen HTML-Generierungen verwenden.
3. **Memory:** `fullData` ist global. Keine Duplikate erstellen. `applyFilters()` erzeugt nur Arrays mit Referenzen, keine Kopien der Nodes.
4. **D3 Simulation:** Bei jedem `renderGraph` wird `g.selectAll('*').remove()` aufgerufen. Das ist teuer. Für Phase 2 könnte man auf D3 Update-Pattern umsteigen (`.join()` statt `.remove()`). Für Phase 1 ist es OK.

---

## APPROVED / BLOCKED CHECKLIST FÜR ARTHEMIS

- [ ] Phase 1 Features implementiert (Smarte Suche, Clustering, Fallakten-Badges)
- [ ] Backup-Files existieren (`*.bak.YYYYMMDD_HHMMSS`)
- [ ] Keine neuen npm/pip Packages installiert
- [ ] D3 v7 CDN unverändert
- [ ] `/api/netzwerk` liefert weiterhin gültiges JSON mit `nodes` und `links`
- [ ] Fallback: Wenn `rheingold_funding` leer ist, crasht nichts
- [ ] Fallback: Wenn `rheingold_findings` leer ist, crasht nichts
- [ ] Mobile Viewport (Responsive) nicht kaputt

---

**Arthemis Entscheidung:** ⏳ PENDING — Wartet auf Apollon-Implementierung für erneuten Review.

**Nächster Schritt:** Apollon implementiert Phase 1. Dann Arthemis Review (ARTH-2026-0423-002).
