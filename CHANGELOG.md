
## [2.4.0] — 2026-04-03

*Platzhalter für nächste Version*

---

## [2.3.0] — 2026-04-04

### Dashboard DEV Fixes
- **#24, #25, #29, #30, #31, #32, #33, #34:** Umfassende Bugfix-Runde im DEV-Environment

### Bug Fixes
- **Rheingold Navigation Fix (SPRINT1-1):** Navigation korrigiert

### Infrastruktur
- **Cronos SSD Cleanup + Docker Migration nach HDD:** SSD entlastet, Container auf HDD umgezogen

### Trading
- **Bot03 dry_run mit SIAS_Arbitrage_v3:** Neue Arbitrage-Strategie im Testbetrieb

### Agent
- **Athene Autonomie Regel:** Neue Regel für autonome Agent-Entscheidungen

---

## [2.2.0] — 2026-04-03

### Neue Features
- **Task Queue System:** `agent_tasks` Tabelle in PostgreSQL
- **Dispatcher + Heartbeat Loop:** Metamaus prüft alle 31m pending Tasks
- **Dashboard systemd Services:** `dashboard-prod.service` (5000), `dashboard-dev.service` (5001)
- **Freqtrade auf Cronos:** Config bot_01.json, dry_run: true, Cleanup 75+ defekte Strategien
- **Skills in allen 9 Agents:** Jeder Agent kennt seine relevanten Skills
- **Rollen neu definiert:** Hermes=QC (30min), Athene=Trading (120min)
- **Sicherheit:** Dashboard bindet strikt an 127.0.0.1

### Bug Fixes
- Bug #1: Token-Anzeige hardcoded → live aus PostgreSQL
- Bug #8: Agent Report leer → generischer Fallback für alle 9 Agents
- Bug #9: Agent Model in Cards → Modell aus openclaw.json
- DB Fix: `athena` → `athene` (Name-Mismatch korrigiert)
- IPFS 404 Logs → Stub in DEV

### Infrastruktur
- systemd Migration: Dashboard Services mit Auto-Restart
- Hermes QC: Übernahme von Athene (alle 30min)
- Athene: Nur Trading/Backtest/Freqtrade
- Skills-Mapping für alle Agents in BOOTSTRAP.md

## [2.2.0] — 2026-04-01 (ursprünglich als 2.3.0 released, zurückgestuft)

### Added
- SIAS Research Skill v1 (sias-research-v1): IFG/NGO/Mail/Rapid Modi
- Mail-Watcher für Rheingold (alle 30min, investigativ@abbydon.com)
- Checkpoint-System (7d Rolling + permanente Milestones)
- README DE + EN für SIAS Skill

### Changed
- Scripts vollständig zu Agent-Ordnern migriert
- Alle 9 Agents: Core-Files konsolidiert
- .openclaw Ordner aufgeräumt (204 MB freigegeben)

### Fixed
- metamaus Rollengrenze schärfer definiert
