# SPRINT1-6: Mail Posteingang Subtab für Dashboard DEV
**Datum:** 2026-04-05  
**Status:** ✅ Fertig — Pythia QC ausstehend

## Geänderte Dateien
1. `/opt/dashboard-dev/app.py`
2. `/opt/dashboard-dev/index.html`

## Änderungen

### Backend (app.py)
- Neue Endpoint-Gruppe "HIMALAYA MAIL API (DEV only)" vor Freqtrade-Block eingefügt
- `GET /api/mails/himalaya?folder=<inbox|sent|drafts>` — Listet Mails
- `POST /api/mails/himalaya/read` mit Body `{"id": "<id>", "folder": "<folder>"}` — Liest Mail-Body
- Hilfsfunktionen: `_himalaya_list()`, `_himalaya_read()`, `_himalaya_env()`
- Expliziter PATH für himalaya: `/home/linuxbrew/.linuxbrew/bin/himalaya`
- Himalaya-Ordner-Mapping: inbox→INBOX, sent→INBOX.Sent, drafts→INBOX.Drafts

### Frontend (index.html)
- Neue Subtab-Unterstruktur im Mails-Tab:
  - 📥 Posteingang, 📤 Gesendet, 📝 Entwürfe
- JavaScript: `switchHimalayaSubtab()`, `loadHimalayaMails()`, `readHimalayaMail()`, `closeHimalayaDetail()`
- Caching pro Subtab (keine redundanten API-Calls)
- Click-to-expand: Klick auf Mail → Detail-Panel mit Body
- Bestehender Rheingold-Mails-Bereich bleibt unverhalten (Separator dazwischen)
- Beim Öffnen des Mails-Tabs: Automatisch Posteingang laden + Rheingold Mails laden

## Verifizierung
| Test | Ergebnis |
|------|----------|
| GET /api/mails/himalaya?folder=inbox | ✅ 10 Mails, korrektes JSON |
| GET /api/mails/himalaya?folder=sent | ✅ success, 0 Mails |
| GET /api/mails/himalaya?folder=drafts | ✅ success, 0 Mails |
| POST /api/mails/himalaya/read (ID 31) | ✅ 2506 chars Body |
| Frontend enthält Subtabs | ✅ "Posteingang", "Gesendet", "Entwürfe" |
| DEV bindet auf 127.0.0.1 | ✅ |
| PROD (5000) nicht angefasst | ✅ |

## Security
- DEV: 127.0.0.1:5001 (lokal nur)
- PROD: unverändert (5000)
- Keine externen Bindings für Mail API
