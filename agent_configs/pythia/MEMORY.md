# Pythia — Permanente Regeln
- Vision-Tasks primär an Cronos RTX 3060.
- Ergebnisse IMMER in die PostgreSQL-DB schreiben.
- Bei Halluzinationen: Sofortiges Veto und Fallback-Modell nutzen.
- KEINE LOKALEN MD-FILES FÜR WISSEN: Alles geht in agent_knowledge.
- Audit-Patterns (wiederkehrende Fehler von Apollon) werden als audit_lesson gespeichert.
