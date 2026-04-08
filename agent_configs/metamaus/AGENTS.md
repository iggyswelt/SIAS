# metamaus — Team

## Mein Team
| Agent | Rolle | Wann einsetzen |
|-----------|------------------|--------------------------------|
| apollon | Code/Dashboard | Fixes, Scripts, API Routes |
| athene | Trading/Arbitrage| Backtests, Hyperopt, Analyse |
| rheingold | OSINT/IFG | PDFs, Recherche, Netzwerke |
| zerberus | Security/Install | Pakete, Scans, Monitoring |
| pythia | Audit/QA | Verifizierung, Vision, Prüfung |
| hermes | Scraping | News, Preise, Web-Daten |
| hestia | YouTube | Shorts, Comments, Channel |
| orpheus | Backup/Docs | GitHub, Doku, Backups |

## Vollständiges Team (V3)
| Agent | Emoji | Aufgabe | Audit-Instanz |
|----------|-------|-------------------------------|---------------|
| apollon | 🔥 | Code, Scripts, Dashboard | Pythia |
| pythia | 👁⚖️ | Vision & SYSTEM-AUDITORIN | - |
| athene | 🏛 | Trading, Backtest, Hyperopt | Pythia |
| rheingold| 💸 | IFG, NGO-Recherche, Köln | Pythia |
| hermes | 🦅 | Scraping, Demo-Events | Pythia |
| hestia | 💬 | YouTube, Kommentare | Pythia |
| orpheus | 📝 | Backups, GitHub, Vault | Pythia |
| zerberus | 🛡 | Security, Server-Monitoring | Pythia |

## Regeln
- NUR Zerberus installiert Pakete und macht updates
- Pythia auditiert nach jeder 3. Iteration (bzw. jeden Task — V3 Regel)
- Max 2 Subagents parallel (Gateway-Limit)
- Event Bus für Kommunikation: Redis sias:* Channels
- Jeder Task benötigt Pythia-Audit für 'done'
- Kein Task ist ohne Pythia-Audit offiziell beendet
