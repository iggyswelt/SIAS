# SIAS V5 — Apollon Auftrag

**Report-ID:** ARTH-2026-0416-005  
**Strategie:** V4-Architektur (SPA-Style) + V3-Feature-Vollständigkeit  
**Basis-Code:** `/opt/sias-dashboard-v4/app.py` (103 Zeilen)  
**Feature-Quelle:** `/opt/dashboard-v3/app.py` (5.129 Zeilen)  
**Ziel-Pfad:** `/home/iggy/SIAS/dashboard/`  
**Test-Port:** 5001  
**Prod-Port:** 5000 (erst nach Pythia-Freigabe)  
**Status:** Wartet auf Iggy Greenlight

---

## SCHRITT 0 — CHECKPOINT

VOR jeder Code-Änderung:

```bash
cp -r /opt/sias-dashboard-v4 \
  /home/iggy/backups/milestones/pre_v5_$(date +%Y%m%d_%H%M)/
cp -r /opt/dashboard-v3 \
  /home/iggy/backups/milestones/pre_v5_v3_source_$(date +%Y%m%d_%H%M)/
```

**HARD RULE:** Nie ohne Backup anfangen.

---

## SCHRITT 1 — V5 VERZEICHNIS ANLEGEN

```bash
mkdir -p /home/iggy/SIAS/dashboard
# V4 als saubere Basis reinkopieren
cp -r /opt/sias-dashboard-v4/* /home/iggy/SIAS/dashboard/
# Danach schrittweise mit V3-Features erweitern
```

Zielstruktur nach Fertigstellung:

```
/home/iggy/SIAS/dashboard/
├── app.py                  # V4-Basis + V3-Features
├── requirements.txt        # Vereinigte Dependencies
├── templates/
│   ├── base.html           # V4: Sidebar-Navigation
│   ├── dashboard.html      # V4: Landing (erweitern)
│   ├── tasks.html          # V4: Tasks (prüfen)
│   ├── demos.html          # V4: Demos (erweitern)
│   ├── youtube.html        # V4: YouTube (erweitern)
│   ├── agents.html         # V4: Agents (erweitern)
│   ├── settings.html       # V4: Settings (erweitern)
│   ├── mail.html           # NEU: Himalaya-Mail-Ansicht
│   ├── news.html           # NEU: News-Feed
│   ├── trading.html        # NEU: Athene/Portfolio
│   └── ...                 # Weitere V3-Templates bei Bedarf
└── static/
    ├── css/
    └── js/
```

---

## SCHRITT 2 — FEATURE-LISTE (Delta V4 → V5)

### V4 hat bereits (7 Routes):
- `/` → Dashboard-Landing
- `/tasks` → Agent-Tasks
- `/demos` → Demos
- `/youtube` → YouTube-Videos
- `/agents` → Agent-Log
- `/settings` → Einstellungen
- `/api/dashboard-stats` → System-Stats

### V3 hat ~90 Routes. Für V5 müssen folgende Features portiert werden:

---

#### F-01: Dashboard Landing (Token Usage, Agent Stats, Kurse)

| Komponente | Quelle V3 |
|------------|-----------|
| `/api/stats/dashboard` | Zeile 1733 |
| `/api/stats/agents` | Zeile 1929 |
| `/api/stats/system` | Zeile 1955 |
| `/api/prices` | Zeile 2197 |
| `/api/openclaw/stats` | Zeile 3968 |

**Aufgabe:** `dashboard.html` erweitern. Aktuell zeigt V4 nur einen statischen Welcome-Bereich. V3 liefert mehrere Stats-APIs — diese müssen in Karten/Widgets auf der Landing-Page landen.

**Test:**
```bash
curl -s http://127.0.0.1:5001/api/dashboard-stats | jq .
curl -s http://127.0.0.1:5001/api/stats/dashboard | jq .
```

---

#### F-02: Tasks (Vollständigkeit prüfen)

| Komponente | Quelle V3 |
|------------|-----------|
| `/api/tasks` (GET/POST) | Zeile 484, 542 |
| `/api/tasks/<int:task_id>` (GET/PUT/DELETE) | Zeile 571, 588, 645 |
| `/api/tasks/<int:task_id>/status` (PATCH) | Zeile 622 |
| `/api/tasks/<int:task_id>/archive` (POST) | Zeile 663 |
| `/api/tasks/move` (POST) | Zeile 461 |
| `/api/db/tasks` (GET/POST) | Zeile 686, 758 |
| `/api/db/tasks/<int:task_id>/stop` (POST) | Zeile 789 |
| `/api/db/tasks/<int:task_id>/status` (PATCH) | Zeile 815 |

**Anmerkung:** V4 hat `/tasks` als Frontend-Route, aber das Backend ist sehr dünn (nur `agent_tasks` Tabelle auslesen). V3 hat ein vollständiges Task-Management mit DB-Tasks und Status-Updates.

**Aufgabe:** V4 `tasks.html` und `app.py` Task-Route mit V3-Backend verheiraten.

**Test:**
```bash
curl -s http://127.0.0.1:5001/api/tasks | jq '. | length'
curl -s http://127.0.0.1:5001/api/db/tasks | jq '. | length'
```

---

#### F-03: Demos / Demo-Kalender Köln

| Komponente | Quelle V3 |
|------------|-----------|
| `/api/demos` | Zeile 325 |
| `/api/demos/all` | Zeile 394 |
| `/api/demos/categories` (GET) | Zeile 3053 |
| `/api/demos/categorize` (POST) | Zeile 3007 |
| `/api/demo/validate` (POST) | Zeile 3084 |
| `/api/demos/invalid` (POST) | Zeile 2918 |
| `/api/demo/feedback` (POST) | Zeile 2862 |
| `/api/news_events` | Zeile 3123 |

**Anmerkung:** Kein dediziertes `demo*.html` Template in `/opt/dashboard-v3/templates/` gefunden. Demo-Daten werden wahrscheinlich inline oder über JS in ein Haupt-Template gerendert. V4 hat bereits `demos.html` — dieses muss mit den V3-APIs verknüpft werden.

**Aufgabe:** `demos.html` erweitern: Demo-Liste, Kalender-Ansicht, Kategorien, Validierung.

**Test:**
```bash
curl -s http://127.0.0.1:5001/api/demos | jq .
curl -s http://127.0.0.1:5001/api/demos/all | jq .
```

---

#### F-04: YouTube + Community (top100, elite, loyalty)

| Komponente | Quelle V3 |
|------------|-----------|
| `/api/youtube/channels` (GET/POST) | Zeile 86, 99 |
| `/api/youtube/stats/all` | Zeile 137 |
| `/api/youtube/progress` | Zeile 173 |
| `/api/youtube/refresh` (POST) | Zeile 205 |
| `/api/youtube/videos/<channel_id>` | Zeile 250 |
| `/api/youtube/<video_id>` | Zeile 294 |
| `/api/youtube/background-refresh` (POST) | Zeile 451 |
| `/api/youtube/community/top100/comments` | Zeile 854 |
| `/api/youtube/community/top100/loyalty` | Zeile 871 |
| `/api/youtube/community/elite` | Zeile 888 |
| `/api/youtube/community/<author_id>` | Zeile 905 |
| `/api/hestia/pipeline` | Zeile 34 |
| `/api/hestia/comments` | Zeile 3253 |
| `/api/hestia/stats` | Zeile 3336 |

**Anmerkung:** V4 hat `/youtube` bereits, holt aber nur `agent_knowledge`. V3 hat eine vollständige YouTube-Hestia-Pipeline.

**Aufgabe:** `youtube.html` massiv erweitern oder durch V3-YouTube-Template ersetzen (wenn vorhanden). Community-Routes (4 Stück) müssen rein.

**Test:**
```bash
curl -s http://127.0.0.1:5001/api/youtube/stats/all | jq .
curl -s http://127.0.0.1:5001/api/youtube/community/top100/comments | jq .
```

---

#### F-05: Mail (Ansicht + Send-Funktion)

| Komponente | Quelle V3 |
|------------|-----------|
| `/api/mails/himalaya` (GET) | Zeile 3738 |
| `/api/mails/himalaya/read` (POST) | Zeile 3768 |
| `send_smtp_mail(to_email, subject, body)` | Zeile 3592 |
| `/api/rheingold/mail/send/<int:mail_id>` (POST) | Zeile 3612 |
| `/api/ifg/<int:ifg_id>/mail/<int:mail_id>/send` (POST) | Zeile 5045 |
| `/api/rheingold/mails` (GET) | Zeile 3479 |
| `/api/rheingold/mail/<int:mail_id>` (GET/PUT/DELETE) | Zeile 3497, 3510, 3523 |

**Anmerkung:** V4 hat keine Mail-Seite. V3 hat sowohl Himalaya-Mail-Ansicht (IMAP) als auch Rheingold-Mail-Verwaltung + SMTP-Send.

**Aufgabe:** Neue `mail.html` anlegen. Sidebar-Item `mail` hinzufügen. Himalaya-Liste anzeigen + SMTP-Send-Button integrieren.

**Test:**
```bash
curl -s "http://127.0.0.1:5001/api/mails/himalaya?folder=inbox&limit=5" | jq .
```

---

#### F-06: News (neu designen, neue Sources)

| Komponente | Quelle V3 |
|------------|-----------|
| `/api/news` (GET) | Zeile 1427 |
| `/api/news/woke-filter` (GET) | Zeile 1529 |
| `/api/news/sources` (GET/POST) | Zeile 1621, 1634 |
| `/api/news/sources/<int:source_id>` (DELETE) | Zeile 1653 |
| `/api/news/fetch` (POST) | Zeile 1669 |
| `/api/news/<int:article_id>/read` (POST) | Zeile 1713 |
| `/news` | Zeile 3158 |
| `/api/news_events` | Zeile 3123 |
| `/api/news_events/refresh` | Zeile 3153 |

**Anmerkung:** V4 hat keinen News-Bereich.

**Aufgabe:** Neue `news.html` mit modernem Design. News-Feed, Source-Verwaltung, Woke-Filter, Refresh-Button.

**Test:**
```bash
curl -s http://127.0.0.1:5001/api/news | jq .
```

---

#### F-07: Agents

| Komponente | Quelle V3 |
|------------|-----------|
| `/api/agents` (GET) | Zeile 2326 |
| `/api/agents/status` (GET) | Zeile 2358 |
| `/api/agents/<agent>/report` (GET) | Zeile 2393 |
| `/api/agents/<agent>/<action>` (POST) | Zeile 2585 |
| `/api/agents/usage` (GET) | Zeile 4088 |
| `/api/rheingold/engine-status` | Zeile 4595 |
| `/api/rheingold/status` | Zeile 4520 |

**Anmerkung:** V4 hat `/agents` bereits, zeigt aber nur die letzten 30 Zeilen aus `inter_agent_chat.log`. V3 hat ein vollständiges Agent-Management.

**Aufgabe:** `agents.html` erweitern: Agent-Status, Report-Download, Actions (start/stop/restart), Engine-Logs.

**Test:**
```bash
curl -s http://127.0.0.1:5001/api/agents | jq .
curl -s http://127.0.0.1:5001/api/agents/status | jq .
```

---

#### F-08: Trading / Athene

| Komponente | Quelle V3 |
|------------|-----------|
| `/api/prices` | Zeile 2197 |
| `/api/watchlist` | Zeile 2239 |
| `/api/portfolio` | Zeile 2255 |
| `/api/portfolio/add` (POST) | Zeile 2272 |
| `/api/watchlist/add` (POST) | Zeile 2300 |
| `/api/freqtrade/profit` | Zeile 3806 |
| `/api/freqtrade/status` | Zeile 3828 |
| `/api/freqtrade/balance` | Zeile 3840 |
| `/api/freqtrade/performance` | Zeile 3849 |
| `/api/trading/queue` | Zeile 3866 |
| `/api/trading/top` | Zeile 3893 |
| `/api/trading/bots` | Zeile 3914 |
| `/api/athene/iterations` | Zeile 4929 |
| `/api/athene/baseline` | Zeile 4947 |
| `/api/athene/events` | Zeile 4961 |
| `/api/athene/backtest-results` | Zeile 4461 |
| `/api/athene/marathon-status` | Zeile 4484 |
| `/trading/backtests` | Zeile 4184 |
| `/api/backtest-status` | Zeile 4193 |
| `/portfolio` | Zeile 3430 |

**Anmerkung:** V4 hat keinen Trading-Bereich.

**Aufgabe:** Neue `trading.html` anlegen. Portfolio, Watchlist, Freqtrade-Stats, Athene-Marathon.

**Test:**
```bash
curl -s http://127.0.0.1:5001/api/portfolio | jq .
curl -s http://127.0.0.1:5001/api/freqtrade/status | jq .
```

---

#### F-09: Settings

| Komponente | Quelle V3 |
|------------|-----------|
| `/api/gateway/usage` | Zeile 4111 |
| `/api/openclaw/sync` (POST) | Zeile 4054 |
| `/api/openclaw/tools` | Zeile 4020 |
| `/api/openclaw/models` | Zeile 3986 |

**Anmerkung:** V4 hat `/settings` bereits, ist aber leer. V3 hat Settings über verschiedene API-Routes verteilt.

**Aufgabe:** `settings.html` füllen: Gateway-Usage, OpenClaw-Sync, Model-Liste.

**Test:**
```bash
curl -s http://127.0.0.1:5001/api/openclaw/tools | jq .
```

---

## SCHRITT 3 — MIGRATIONS-REIHENFOLGE

**Reihenfolge:**

1. **F-01 Dashboard** → Sofort sichtbar, niedriges Risiko
2. **F-02 Tasks** → V4 hat schon UI, nur Backend erweitern
3. **F-04 YouTube** → Hoher Nutzen, klar abgegrenzt
4. **F-03 Demos** → Kalender-Logik portieren
5. **F-05 Mail** → Neue Seite, Himalaya + SMTP
6. **F-06 News** → Neue Seite, Source-Verwaltung
7. **F-08 Trading** → Neue Seite, Athene-Integration
8. **F-07 Agents** → V4-UI erweitern
9. **F-09 Settings** → Letzter Schliff

**Nach jedem Feature:**
- `curl http://127.0.0.1:5001/[route] → 200`
- Checkpoint ins Backup-Verzeichnis
- Pythia-Stamp in DB (oder manuell im Log vermerken)

---

## SCHRITT 4 — HARD RULES FÜR APOLLON

- **Nur auf 5001 testen.** Kein Touch von 5000.
- **0.0.0.0 NIEMALS.** Alle Bindings müssen `127.0.0.1` sein.
- **Ein Feature nach dem anderen.** Kein Bulk-Merge.
- **Nach jedem Feature: Checkpoint.**
- **5004 FINGER WEG.** Rheingold-Standalone bleibt unangetastet.
- **Templates aus V3 nur kopieren, nicht verschieben.** Originale in `/opt/dashboard-v3/` müssen erhalten bleiben.
- **Keine Schema-Änderungen ohne Pythia-Freigabe.**
- **V4 `base.html` beibehalten** — Sidebar-Navigation ist die UX-Grundlage von V5.

---

## SCHRITT 5 — FINALE MIGRATION

**Nur wenn alle Features grün + Pythia approved:**

1. systemd `sias-dashboard-prod.service` auf `/home/iggy/SIAS/dashboard/` umstellen
2. Port 5000 testen:
   ```bash
   curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:5000/api/healthz
   ```
3. Alte Services stoppen + deaktivieren:
   - metamaus-dashboard.service (5000, alter Pfad)
   - metamaus-v2.service (5002)
   - sias-dashboard-v3.service (5003)
   - sias-dashboard-v4.service (5010)
   - Manuelller Prozess auf 5001 (dashboard-dev)
4. Archivieren nach `/home/iggy/backups/cold/`
5. Git-Commit in `/home/iggy/SIAS/dashboard/`

---

## ANHANG — V3 Route-Delta (vollständig)

V4 Routes: 7  
V3 Routes: ~90  
Fehlende in V4 (für V5 relevant): ~50+ Routes

**Kritische V3-Routes, die in V5 rein müssen:**

| Route | Zeile V3 | Beschreibung |
|-------|----------|--------------|
| `/api/stats/dashboard` | 1733 | Token & Agent Stats |
| `/api/tasks` | 484 | Task-Liste |
| `/api/db/tasks` | 686 | DB-Task-Manager |
| `/api/demos` | 325 | Demo-Events |
| `/api/demos/all` | 394 | Alle Demos |
| `/api/youtube/stats/all` | 137 | YouTube Übersicht |
| `/api/youtube/community/top100/comments` | 854 | Community Top100 |
| `/api/youtube/community/top100/loyalty` | 871 | Loyalty Score |
| `/api/youtube/community/elite` | 888 | Elite Members |
| `/api/mails/himalaya` | 3738 | Mail-Ansicht |
| `/api/mails/himalaya/read` | 3768 | Mail lesen |
| `send_smtp_mail()` | 3592 | SMTP-Send Helper |
| `/api/rheingold/mail/send/<int:mail_id>` | 3612 | Rheingold Mail Send |
| `/api/news` | 1427 | News-Feed |
| `/api/news/sources` | 1621 | News Sources |
| `/api/agents` | 2326 | Agent-Liste |
| `/api/agents/status` | 2358 | Agent-Status |
| `/api/portfolio` | 2255 | Portfolio |
| `/api/freqtrade/status` | 3828 | Freqtrade Status |
| `/api/athene/marathon-status` | 4484 | Athene Marathon |

---

**Dokument erstellt von:** Arthemis  
**Nächster Schritt:** Iggy gibt Greenlight → Apollon beginnt mit SCHRITT 0.
