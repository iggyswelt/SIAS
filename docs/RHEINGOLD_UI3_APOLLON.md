# ARTH-2026-0418-001 — Rheingold 5004 UI-Audit
**Audit-Datum:** 2026-04-18
**Auditor:** Arthemis
**Status:** BLOCKED — Apollon-Fix erforderlich

---

## P-01: Fallakte als Popup statt eigene Seite

**Befund:**

Die Fallakte wird in `netzwerk.html` Z.190 als HTML-Link (`<a href="/entities/'+d.db_id+'"`) geöffnet → **volle Seiten-navigation** zu `/entities/<int:entity_id>` auf Route L35-60 `app.py`. Das ist eine separate Page mit eigenem Request/Response-Zyklus, inkl. neuem HTML-Rendered Template.

`entity_detail.html` existiert und ist technisch funktionsfähig — aber der Klick auf den "Fallakte öffnen"-Button im Netzwerk-Panel resettet den gesamten Graph-Zustand (D3 Simulation, Zoom, Filter, aktive Tab).

In `karte.html` Z.194 existiert bereits `openKarteFallakte(id)` — eine JS-Funktion die im Netzwerk nicht genutzt wird.

**Issue:** [Schwer] Navigation über Router-Link statt JS-Panel. Vollständiger Page-Reload zerstört Netzwerk-Context. Benutzer verliert Zoom/Pan/Filter/aktive Simulation.

**Fix:** Apollon implementiert ein Slide-in/Einblend-Panel in `netzwerk.html` (analog zum bestehenden `#detail-panel` Z.53):
1. Neues `<div id="fallakte-panel">` mit `position:absolute; top:0; right:0; width:420px; height:100%; background:var(--surface); border-left:1px solid var(--border); display:none; z-index:500; overflow-y:auto`
2. `window.openFallakte = function(db_id)` — fetch `/api/entities/<db_id>`, HTML + Relations + Funding + Findings ins Panel schreiben, Panel einblenden
3. Den "Fallakte öffnen"-Link in `showDetail()` Z.190 ersetzen: `href="/entities/..."` → `onclick="openFallakte(d.db_id); return false;"`
4. Close-Button im Panel (X oben rechts, `display:none` toggeln)
5. Kein Page-Reload, Netzwerk-Graph bleibt intakt

**AUFWAND:** Mittel — neues Panel + JS-Funktion, kein Backend-Change nötig (API `/api/entities/<id>` existiert bereits)

---

## P-02: Fragmente im Netzwerk (Datenqualität)

**Befund:**

| Metrik | Wert |
|--------|------|
| Gesamte Entities | 2.710 |
| Isolierte Nodes (0 Verbindungen) | 2.691 |
| Relations insgesamt | 21 |
| Fragment-Garbage (Kurznamen < 5 Zeichen) | 30+ Examples |

Die Datenqualität ist kritisch: **99,3% aller Entities haben NULL Verbindungen**. Nur 21 Relationen existieren in der DB.

Zusätzlich: dozens of garbage entities mit Namen wie `Abgabe`, `Absatz`, `Amadeu`, `Anfech`, `Anhang`, `Anlass`, `Ansatz`, `Anteil`, `Antrag`, `Appell`, `Arbeit`, `Aufnah`, `Aufruf`, `Bedarf`, `Beginn`, `Bekämp`, `Berlin`, `Bilanz`, `Bisher`, `Budget`, `Bundes`, `Bürger`, `Chance`, `Charta`, `Cookie` — das sind OCR/PDF-Extraktions-Fragmente, keine realen Organisationen.

Korrekt erkannt: `BAMF`, `BMBF`, `ICIJ` (das sind legitime Akronyme, nicht Fragment-Müll).

**Issue:** [KRITISCH] Scraping/Parsing erzeugt Word-Fragment-Entities. Beziehungs-Netzwerk ist praktisch unbrauchbar. Die 2.691 isolierten Nodes sollten als Kandidaten für automatisiertes Matching/Linking geprüft werden.

**Fix:** Apollon erstellt ein Bereinigungs-Script:
1. SQL-Delete-Query für Entities deren `name`:
   - Länge < 4 Zeichen (Oder < 6 bei echten Akronymen prüfen)
   - Matcht Regex `^(Ab|An|Auf|Beg|Bek|Ber|Bi|Bis|Büd|Cha|Ant|App|Arb|Auf)$` etc. (häufige PDF-Fragment-Prefixes)
   - `source` ist eine PDF-URL und `name` ist ein einzelnes Wort ohne Umlaute/Großbuchstaben-Muster (Echte Namen haben gemischte Cases)
2. Alternativ: Neue Extraktions-Routine die nur Entities mit Score > 10 oder mit mindestens einer Funding-Zuordnung behält
3. Für das Relations-Problem: Separate Analyse — warum nur 21 Relations? Prüfen ob `rheingold_relations` korrekt befüllt wird oder ob das Scraping die Relationen nicht extrahiert

**AUFWAND:** Niedrig (Cleanup-SQL) + Mittel (Debugging Relations-Scraping)

---

## P-03: Vollbild-Skalierung

**Befund:**

`netzwerk.html` Z.7: `#graph-container` definiert mit:
```css
height: calc(100vh - 180px);
```
Das ist eine **hartecodierte Subtraktion** von 180px (Header + Subtab-Navigation + Margins). Das bedeutet:

1. **Kein echtes Vollbild:** Der Graph geht nie bis zum Browserrand — immer 180px vertikaler Rand
2. **Statische SVG-Dimensionen:** `width`/`height` werden in JS nur einmal beim Laden ermittelt (Z.59-60), nicht bei Fenster-Resize nachgeführt
3. **Kein Vollbild-Toggle-Button:** Es existiert kein UI-Element um in einen echten Vollbild-Modus zu wechseln (z.B. via `requestFullscreen()` API)
4. **Fixed-Legende überlappt:** `#netzwerk-legende` ist `position:fixed` mit `z-index:999` — im Vollbild würde die Legende über dem Graph liegen ohne Abschaltung

Die Legende am Bottom-Left (`position:fixed; bottom:10px; left:10px`) ist ebenfalls statisch und könnte bei true-fullscreen stören.

**Issue:** [Mittel] Kein echter Vollbild-Modus. Statische Dimensionen. Kein Resize-Handler.

**Fix:** Apollon:
1. CSS-Variable einführen: `--graph-offset: 180px` in `netzwerk.html <style>` — damit der Offset zentral konfigurierbar ist
2. Resize-Handler in JS: `window.addEventListener('resize', function(){ var w = container.offsetWidth; var h = container.offsetHeight; svg.attr('width',w).attr('height',h); simulation.force('center', d3.forceCenter(w/2, h/2)).alpha(0.3).restart(); })`
3. Optionaler Vollbild-Button: `<button onclick="document.documentElement.requestFullscreen()" style="position:absolute;top:12px;right:300px;z-index:998">⛶ Vollbild</button>` — ruft Browser-Fullscreen-API auf, Graph passt sich über Resize-Handler automatisch an
4. Legende im Vollbild optional ausblenden (via `fullscreenchange` Event): `document.addEventListener('fullscreenchange', () => { legende.style.display = document.fullscreenElement ? 'none' : 'block'; })`

**AUFWAND:** Niedrig — CSS-Variable + Resize-Handler (~15 Zeilen JS)

---

## Summary

| Issue | Severity | Fix-Aufwand |
|-------|----------|-------------|
| P-01: Fallakte Page-Reload | Schwer | Mittel |
| P-02: Datenqualität / Fragmente | Kritisch | Niedrig + Mittel |
| P-03: Vollbild fehlt | Mittel | Niedrig |

**ENTSCHEIDUNG: BLOCKED**

Apollon: Bitte P-01 (Fallakte-Panel), P-02 (Cleanup-SQL + Relations-Debugging) und P-03 (Resize-Handler + CSS-Variable) implementieren. Nach Fertigstellung → "REVISED CODE READY FOR ARTHEMIS" an Metamaus.

*Arthemis — unbestechlicher Code-Auditor — 2026-04-18*
