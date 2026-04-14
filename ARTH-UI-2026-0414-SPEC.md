# ARTH-UI-2026-0414 — RHEINGOLD UI REDESIGN SPEC
**Status:** APPROVED
**Reviewer:** Arthemis
**Datum:** 2026-04-14

---

## BESTANDSAUFNAHME (Ist-Zustand)

| Check | Ergebnis | Details |
|-------|----------|---------|
| Landing Page `/` | ✅ Live Feed existiert | `/` zeigt Live Feed, kein Dashboard-Widget |
| Dashboard `/dashboard` | ✅ Stats-Grid + Activity Feed | `/api/stats` liefert Daten |
| Entities `/entities` | ⚠️ Nur Stadtteil-Filter | Keine Hierarchie (Stadt → Bezirk → Stadtteil) |
| Entity Detail | ⚠️ Fallakte unstrukturiert | Keine Fördertopf-Priorisierung |
| Ampel-System | ❌ Nicht vorhanden | Nur recherche_status-Badge |
| Notizfeld | ✅ Spalte existiert | `notes` in rheingold_orgas, aber leer + kein PATCH-API |
| Netzwerk `/netzwerk` | ⚠️ D3 existiert | Keine Top-50-Filterung, kein Node-Klick → Detail |
| Karte `/karte` | ✅ Karte existiert | |
| Findings `/findings` | ✅ Tabelle existiert | `is_verified`-Feld vorhanden |
| IFG `/ifg` | ✅ Tracker existiert | |

**DB-Schema (relevant):**
- `rheingold_orgas`: id, name, foerderbetrag_eur, bewilligt, antrag_datum, jury_urteil,
  adresse, plz, stadtteil, webseite, recherche_status (verifiziert/manuell-verifiziert/offen/KRITISCH),
  priority_score, notes
- `rheingold_findings`: id, org_name, is_verified, quelle, beschreibung, betrag, jahr
- KEIN `belastbarkeit_stufe` (existiert nicht)
- KEIN `stadt`-Feld (nur stadtteil + plz)

---

## PHASE 1 — Apollon kann HEUTE bauen

### Prio 1 — Landing Page Dashboard-Widgets

**`/` (index.html):** Stats-Grid links, Ampel-Übersicht mitte, Live-Feed rechts (intern).
Top-Stats: Anzahl Orgas, Summe Förderbetrag (EUR), Findings mit is_verified,
IFG-Status (offene Anfragen).

```
Widget links:   [🔢 49 Orgas] [💰 €1.2M Förderung] [📋 12 Findings]
Widget mitte:   [🟢 43] [🟡 3] [🔴 3] — Ampel nach recherche_status
Widget rechts:  Live Feed (intern, unverändert)
```

**API `/api/stats` erweitern** um:
```sql
SELECT COUNT(*) as org_count FROM rheingold_orgas;
SELECT SUM(foerderbetrag_eur) as total_funding FROM rheingold_findings;
SELECT COUNT(*) FILTER (WHERE is_verified = true) as verified_findings FROM rheingold_findings;
```

---

### Prio 2 — Entity Fallakte neu strukturieren

**Neue Reihenfolge in `/entities/<id>`:**
1. **Fördertopf + Bewilligung** (beantragt, bewilligt, foerderbetrag_eur)
2. **Gegenstand** (foerdergegenstand, foerderstrang) — ERSTER PUNKT
3. **Jury-Urteil + Datum** (jury_urteil, antrag_datum)
4. **Adresse, Website, Stadtteil** (adresse, webseite, plz, stadtteil)
5. **Ampel-Badge** (neu: visuellem Ampel-Indikator)
6. **Notizfeld** (notes — textarea, Auto-Save)
7. **Quellenangabe** (neu: letzte Finding-Quelle)

---

### Prio 3 — Hierarchischer Filter Entities

**Filter-Hierarchie in `/entities`:**
```
[Alle Städte ▾] → aus plz (50672 = Köln, 51103 = Köln-Mitte, etc.)
[Alle Bezirke ▾] → Bezirksname aus stadtteil (Kalk, Ehrenfeld, etc.)
[Alle Stadtteile ▾] → einzelne stadtteil-Werte
```

**Umsetzung:** Dropdowns per JS befüllen aus `/api/entities` (plz/stadtteil extrahieren).
Kein neues DB-Feld nötig. Köln-PLZ 506xx/511xx als "Köln" gruppieren.
PLZ 11xxxx = Berlin (skaliert später).

---

### Prio 3 — Notizfeld API + UI

**DB:** `notes` existiert bereits (leer).
**UI:** `<textarea>` in Fallakte, Auto-Save nach 1s Debounce.
**API:** Neuer Endpoint:
```
PATCH /api/entity/<id>/notiz
Body: { "notizen": "..." }
```
```python
@app.route('/api/entity/<int:entity_id>/notiz', methods=['PATCH'])
def update_entity_notiz(entity_id):
    data = request.get_json()
    cur.execute("UPDATE rheingold_orgas SET notes = %s WHERE id = %s",
                (data['notizen'], entity_id))
    return jsonify({"success": True})
```

---

### Prio 3 — Ampel-System

**Logik basierend auf vorhandenen Feldern:**
```
🟢 GRÜN:  recherche_status IN ('verifiziert', 'manuell-verifiziert')
           UND findings.is_verified = true
🟡 GELB:  recherche_status = 'offen'
           ODER findings.is_verified = false
🔴 ROT:   recherche_status = 'KRITISCH'
           ODER findings haben keine quelle
```
Hinweis: `belastbarkeit_stufe` existiert NICHT in DB —
Ampel basiert auf `recherche_status` + `is_verified` + `quelle`.

**UI:** Farbiger Punkt + Tooltip mit Begründung.
Einbauen in: Entities-Liste (Badge), Fallakte (Header), Dashboard (Ampel-Widget).

---

## PHASE 2 — Folgeschritt

| Task | Beschreibung | DB-Änderung |
|------|-------------|-------------|
| Netzwerk Top-50 | D3: Nur Entities mit priority_score Top-50, Filter >20 | keine |
| Node-Klick → Fallakte | D3: Klick auf Node öffnet `/entities/<id>` | keine |
| Quelle-Pflicht | Jedes Finding braucht `quelle`-Pflichtfeld | `ALTER TABLE` |
| Stadt-Hub | Neue Spalte `stadt` aus PLZ ableiten (506xx=Köln, 11xxx=Berlin) | `ALTER TABLE` |
| IFG-Tracker Integration | IFG-Status Badge auf Fallakte | keine |
| Handelsregister-Link | Aus `handelsregister_nr` Google-Suchlink bauen | keine |

---

## DB-ÄNDERUNGEN (Apollon: ALTER TABLE)

```sql
-- 1. Notizfeld (notes existiert bereits — nur PATCH fehlt)
-- Kein ALTER nötig

-- 2. Stadt-Hub (Phase 2)
ALTER TABLE rheingold_orgas ADD COLUMN stadt VARCHAR(100);

-- 3. Quelle-Pflicht (Phase 2)
ALTER TABLE rheingold_findings ALTER COLUMN quelle SET NOT NULL;
```

---

## ENTSCHEIDUNG: APPROVED

Apollon hat alle nötigen Infos. Spec liegt vor.

**Nächster Schritt:** Apollon baut Phase 1 (Prio 1-3).
Arthemis macht erneutes Review nach Fertigstellung.
