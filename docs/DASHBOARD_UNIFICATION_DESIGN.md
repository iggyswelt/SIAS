# Dashboard Unification Design Document

**Report ID:** ARTH-2026-0416-001  
**Created:** 2026-04-16  
**Status:** Awaiting User Greenlight

---

## 1. Executive Summary

Aktuell laufen **6 Dashboard-Instanzen** gleichzeitig auf verschiedenen Ports im Bereich 5000–5010. Die Codebases haben sich stark divergiert:

- **/opt/dashboard** (5000) — älteste Prod-Instanz, 4.103 Zeilen
- **/opt/dashboard-dev** (5001) — Dev-Branch, manuell gestartet, 4.805 Zeilen
- **/opt/dashboard-v2** (5002) — Feature-Superset, 5.121 Zeilen
- **/opt/dashboard-v3** (5003) — aktuellste und größte Version, 5.129 Zeilen
- **/opt/rheingold-standalone** (5004) — OSINT/Rheingold-Only, 623 Zeilen
- **/opt/sias-dashboard-v4** (5010) — Minimal-Version, nur 103 Zeilen

**Empfohlene Basis:** `/opt/dashboard-v3` (Port 5003)  
**Begründung:** Neueste Änderung (2026-04-11), meiste Zeilen, aktivster systemd-Service, höchste Feature-Dichte (Mail, YouTube, Rheingold, Hestia).

---

## 2. Discovery Table

| Port | Service | Directory | app.py lines | Last modified | Binding |
|------|---------|-----------|--------------|---------------|---------|
| 5000 | metamaus-dashboard.service | /opt/dashboard | 4.103 | 2026-04-09 | 127.0.0.1 |
| 5001 | *(manuell, PID 270162)* | /opt/dashboard-dev | 4.805 | 2026-04-08 | 127.0.0.1 |
| 5002 | metamaus-v2.service | /opt/dashboard-v2 | 5.121 | 2026-04-11 | 127.0.0.1 |
| 5003 | sias-dashboard-v3.service | /opt/dashboard-v3 | 5.129 | 2026-04-11 | 127.0.0.1 |
| 5004 | sias-rheingold-standalone.service | /opt/rheingold-standalone | 623 | 2026-04-15 | 127.0.0.1 |
| 5010 | sias-dashboard-v4.service | /opt/sias-dashboard-v4 | 103 | 2026-04-14 | 127.0.0.1 |

### Inaktive aber relevante Codebases
| Directory | app.py lines | Last modified | Status |
|-----------|--------------|---------------|--------|
| /opt/dashboard-MASTER | 5.072 | 2026-04-10 | Nicht aktiv gestartet |
| /home/iggy/SIAS/dashboard_prod | ~3.800 | 2026-04-09 | Git-Repo, älter als /opt/ |
| /home/iggy/SIAS/dashboard_v2 | ~4.900 | 2026-04-09 | Git-Repo, älter als /opt/ |

---

## 3. Feature Matrix

| Feature | 5000 | 5001 | 5002 | 5003 | 5004 | 5010 | Best Version |
|---------|------|------|------|------|------|------|--------------|
| YouTube / Hestia | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ | 5003 (150 hits) |
| Tasks API | ✅ | ✅ | ✅ | ✅ | ❌ | ✅ | 5003 |
| Mail / Himalaya | ✅ | ✅ | ✅ | ✅ | ⚠️ | ❌ | 5003 (117 hits) |
| Rheingold / IFG / Netzwerk | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ | 5003 (231 hits) |
| Demos API | ✅ | ✅ | ✅ | ✅ | ❌ | ✅ | 5003 |
| DB-Tasks API | ❌ | ✅ | ✅ | ✅ | ❌ | ❌ | 5003 |
| `/ifg` Route | ❌ | ❌ | ✅ | ✅ | ✅ | ❌ | 5003 |
| `/api/hestia/pipeline` | ❌ | ❌ | ✅ | ✅ | ❌ | ❌ | 5003 |
| Agent-Dashboard | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ | 5010 |
| Community / Elite / Loyalty | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | 5000/5001 |

**Anmerkungen:**
- 5000 und 5001 haben noch Community-Features (`/api/youtube/community/...`), die in v2/v3 fehlen.
- 5004 (rheingold-standalone) ist ein reines OSINT-Dashboard mit eigener Karte und Medien-API.
- 5010 (v4) ist ein komplett neuer Ansatz mit SPA-ähnlicher Router-Struktur (`/tasks`, `/demos`, `/youtube`, `/agents`, `/settings`).

---

## 4. Basis Recommendation

### Gewählte Basis
**`/opt/dashboard-v3`** (Port 5003)

### Warum v3?
1. **Recency:** Letzte Änderung am 2026-04-11 (neueste aller aktiven Instanzen).
2. **Size:** 5.129 Zeilen — größte aktive Codebase.
3. **Service status:** Läuft unter `sias-dashboard-v3.service`, ist also systemd-integriert.
4. **Feature completeness:** Enthält alle großen Module (YouTube, Tasks, DB-Tasks, Mail, Rheingold, Hestia, IFG).
5. **Git-Desync:** /opt/dashboard-v3 ist neuer als /home/iggy/SIAS/ — aber das ist das *aktive* System. Ein Re-Import ins Git-Repo muss nach der Unifikation passieren.

### Was muss in die Basis portiert werden
| Feature | Quelle | Komplexität |
|---------|--------|-------------|
| Community / Top100 / Elite / Loyalty | 5000 oder 5001 | Medium |
| Agent-Dashboard / `/agents` Route | 5010 (v4) | High (SPA-Struktur) |
| Rheingold-Karten-Frontend | 5004 (standalone) | Medium |

### Was kann fallen gelassen werden
- **/opt/dashboard** (5000) — komplett durch v3 ersetzbar.
- **/opt/dashboard-dev** (5001) — Dev-Features sind größtenteils in v3/v2 integriert.
- **/opt/dashboard-v2** (5002) — v3 ist der direkte Nachfolger (nur 8 Zeilen Unterschied).
- **/opt/dashboard-MASTER** — veraltet gegenüber v3.

---

## 5. Target Structure

```
/home/iggy/SIAS/dashboard/
├── app.py                  # Einheitliche Basis (aus v3)
├── config_prod.py          # Port 5000, PROD-Settings
├── config_dev.py           # Port 5001, DEV-Settings
├── requirements.txt        # Vereinheitlichte Dependencies
├── index.html              # Haupt-Frontend
├── templates/              # Jinja2-Templates (Legacy)
├── static/                 # CSS, JS, Assets
│   ├── js/
│   ├── css/
│   └── img/
├── routes/                 # OPTIONAL: Modulare Route-Dateien
│   ├── youtube.py
│   ├── tasks.py
│   ├── rheingold.py
│   └── agents.py
└── docs/
    └── MIGRATION_LOG.md
```

---

## 6. Port Migration Map

| Port | Before | After | Aktion |
|------|--------|-------|--------|
| 5000 | /opt/dashboard/ | /home/iggy/SIAS/dashboard/ (PROD) | Service ersetzen |
| 5001 | /opt/dashboard-dev/ | /home/iggy/SIAS/dashboard/ (DEV) | Manuellen Prozess stoppen |
| 5002 | /opt/dashboard-v2/ | ARCHIVE | Service stoppen + deaktivieren |
| 5003 | /opt/dashboard-v3/ | /home/iggy/SIAS/dashboard/ (PROD) | Temporär, dann auf 5000 |
| 5004 | /opt/rheingold-standalone/ | **ENTSCHEIDUNG OFFEN** | Siehe Frage 3 |
| 5010 | /opt/sias-dashboard-v4/ | ARCHIVE | Service stoppen + deaktivieren |

---

## 7. Hidden Traps Detected

1. **Git-Repo Desync:**
   `/home/iggy/SIAS/dashboard_prod/app.py` ist vom 2026-04-09 und hat ~3.800 Zeilen.
   `/opt/dashboard-v3/app.py` ist vom 2026-04-11 und hat 5.129 Zeilen.
   **→ Entwicklung läuft außerhalb des Git-Repos.** Nach der Unifikation muss das canonical Repo aktualisiert werden.

2. **Manueller Prozess auf Port 5001:**
   `/opt/dashboard-dev` läuft ohne systemd-Service (PID 270162). Ein Reboot würde diesen Prozess killen.

3. **Rheingold-Dualität:**
   Rheingold-Features existieren sowohl im Haupt-Dashboard (v2/v3) als auch als eigenständige App (5004). Datenbank-Schema könnte divergieren.

4. **v4 als kompletter Neuanfang:**
   `/opt/sias-dashboard-v4` hat nur 103 Zeilen und eine SPA-Router-Struktur. Falls das die Zukunft ist, müsste man v3-Features in diese Architektur migrieren — das ist ein Rewrite, kein Merge.

---

## 8. Risks & Complexity

| Risk | Probability | Mitigation |
|------|-------------|------------|
| Route-Kollisionen beim Merge | Medium | Jede Route aus allen Codebases inventarisieren und deduplizieren |
| DB-Schema-Divergenz (Rheingold) | Medium | Vor dem Merge DB-Schemas von v3 und 5004 vergleichen |
| Service-Downtime bei Migration | High | Blau-Grün-Deployment: erst neue Instanz auf 5001 testen, dann 5000 switchen |
| Verlust von Community-Features | Low | Explizit aus 5000/5001 extrahieren und in v3 integrieren |
| v4-Architektur macht v3 obsolet | Low | Klären, ob v4 das langfristige Ziel ist |

---

## 9. Open Questions (Required before Greenlight)

1. **Soll `/home/iggy/SIAS/dashboard/` das neue canonical Verzeichnis sein, oder bleibt `/opt/dashboard-v3/` als Basis am Leben?**
   *(Empfehlung: /home/iggy/SIAS/dashboard/ als canonical Pfad, da alle anderen Services dort hinschauen.)*

2. **Was ist mit den Community-Features (`/api/youtube/community/top100`, `/elite`, `/loyalty`)?**
   Diese existieren in 5000/5001, aber nicht in v2/v3. Sollen sie übernommen oder absichtlich entfernt werden?

3. **Soll der Rheingold-Standalone (Port 5004) in das Unified Dashboard integriert werden, oder als separate App bestehen bleiben?**
   Er hat eine eigene Karten-UI und Medien-API. Ein Merge ist möglich, aber nicht trivial.

4. **Ist v4 (Port 5010) eine Spielwiese oder die Zukunft?**
   Falls v4 der langfristige Ersatz ist, wäre ein Merge von v3 in v4 sinnvoller als ein neues v3-Setup.

---

**Do NOT proceed to implementation without explicit user approval.**
