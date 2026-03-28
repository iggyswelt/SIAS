# CHANGELOG

## [2.1.0] — 2026-03-28
### Major Rebuild — System Restore, Token Strategy, Cleanup

**New Features:**
- Multi-Agent System mit 9 spezialisierten Agents
  - metamaus (Teamleader), apollon (Code), athene (Trading)
  - rheingold (Investigativ), pythia (Vision), hermes (Scraper)
  - hestia (YouTube), orpheus (Backup), zerberus (Security)
- Dashboard v1.0 (Port 5000 PROD / 5001 DEV)
- Rheingold IFG-System (994 Findings, NGO-Netzwerk Köln dokumentiert)
- Pythia Vision Integration (qwen3-vl via Alicloud)
- Hyperopt Marathon (Athene + Freqtrade auf Cronos)
- PostgreSQL als zentrales Memory (105 Tabellen)
- Agent Templates in DB (agent_templates Tabelle)
- Token-Tier Strategie (Tier 1/2/3 — spart bis 60% Token-Kosten)
- Secrets via localfile (sauber, eine Quelle — kein Hardcoding mehr!)
- Model-Protection Regel (openclaw.json READ ONLY für alle Agents)

**Architecture:**
- 9 Agents mit Core-Files (IDENTITY, BOOTSTRAP, MEMORY, HEARTBEAT, SOUL, TOOLS, USER, AGENTS)
- PostgreSQL: agent_knowledge, rheingold_findings, athena_trades, youtube_comments, zerberus_tasks
- Server: metamaus (192.168.23.170), RedQueen (192.168.23.101), NAS (192.168.23.104)
- Cronos: OFFLINE bis auf weiteres (GPU-Kabel fehlt — PCIe 8-Pin)
- Secrets: /home/iggy/.openclaw/secrets.json (localfile provider)

**Cleanup (2026-03-28):**
- 16 GB Speicher freigeschaufelt
- Alte Cache-Dateien (npm, Homebrew, ms-playwright, whisper)
- Ungenutzte Go-Verzeichnisse
- Veraltete Wekan-DB (37 Tage inaktiv)
- Legacy Workspace Archive

**Breaking Changes:**
- Cronos (192.168.23.80) OFFLINE — GPU nicht verfügbar
- Keine lokale RTX 3060 Fallback bis auf weiteres
- Alle Agents nutzen jetzt MiniMax/alicloud als Primary, kein Cronos mehr

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
