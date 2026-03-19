# CHANGELOG

## [2.1.0] — 2026-03-19
### Major Update — Vision, Browser Crawler, Team Mindset

**New Features:**
- Browser-Crawler mit Playwright (JS-heavy Seiten)
- Self-Feeding Loop — Crawler generiert eigene Tasks
- Dashboard R4 — Logs gefiltert, Rheingold Live Widget
- Hyperopt Marathon — 22TB HDD, 40 parallel jobs
- Vision Stack — z.ai Vision + alicloud/qwen-vl
- Team Mindset — proaktiv, keine Leerlauf-Phasen
- ADM-Workflow — API-Key-Austausch permanent
- 9 spezialisierte Agents

**Architecture:**
- 8 Agents: Apollon, Athena, Hermes, Rheingold, Zerberus, Hestia, Orpheus, Pythia
- PostgreSQL: learnings, memory, rheingold_findings, athena_trades, hestia_comments, vault
- Server: metamaus, Cronos, NAS, DEMETER

**Breaking Changes:**
- RedQueen (192.168.23.101) DEPRECATED — nicht mehr nutzen!

---

## [2.0.0] — 2026-03-12
### Major Update — File-System → PostgreSQL
- B.A.S.E (Backup Agent Semantic Environment)
- Agent Registry in PostgreSQL
- Orpheus Monitor (automatische Überwachung)
- TPM2-Verschlüsselung
- Hardware-Security Monitoring
- GitHub Deploy Key via NitroKey HSM

## [1.0.0] — 2026-02-18
- Initial Release
- WAL-Protokoll
- .md File-basiertes Memory-System
