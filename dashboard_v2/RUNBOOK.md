# Dashboard DEV — Runbook

> Letztes Update: 2026-04-05 | Autor: Orpheus (automatisiert)

## Architektur
- **Framework:** Flask (Python)
- **Port:** 5001 (DEV) / 5000 (PROD)
- **DB:** PostgreSQL `metamaus` (`scraper@localhost` via psycopg2, RealDictCursor)
- **Host:** metamaus
- **User:** iggy
- **Main SPA:** `index.html` (157 KB, 2790 Zeilen — Single-Page-App mit JS-Tabs)
- **App:** `app.py` (~4530 Zeilen, Flask + REST API)
- **Logging:** `/opt/dashboard-dev/flask.log` (stdout redirect)

## Routes & Funktionen

### Page Routes
| Route | Methode | Funktion | Zweck |
|---|---|---|---|
| `/` | GET | `index()` | SPA index.html ausliefern |
| `/youtube_analysis.json` | GET | `youtube_analysis()` | YouTube Analyse JSON |
| `/news` | GET | `news_page()` | News-Seite (render_template_string) |
| `/ngo_map` | GET | `serve_ngo_map()` | NGO Map (template) |
| `/rheingold` | GET | `serve_rheingold()` | Rheingold Dashboard |
| `/rheingold/content` | GET | `serve_rheingold_content()` | Rheingold Content |
| `/network` | GET | `serve_network()` | Netzwerk-Ansicht |
| `/portfolio` | GET | `serve_portfolio()` | Portfolio-Ansicht |
| `/trading/backtests` | GET | `backtest_tab()` | Backtest-Tab |
| `/rheingold_findings_tab` | GET | `rheingold_findings_tab()` | Rheingold Findings Tab |

### YouTube API
| Route | Methode | Funktion | DB Tabelle |
|---|---|---|---|
| `/api/youtube/channels` | GET | `get_youtube_channels()` | `youtube_channels` |
| `/api/youtube/channels` | POST | `add_youtube_channel()` | `youtube_channels` (INSERT) |
| `/api/youtube/channels/<id>` | DELETE | `delete_youtube_channel()` | `youtube_channels` |
| `/api/youtube/stats/all` | GET | `get_all_youtube_stats()` | `youtube_channels` + `youtube_stats` |
| `/api/youtube/progress` | GET | `get_youtube_progress()` | `iggy_playlists` |
| `/api/youtube/refresh` | POST | `refresh_youtube_stats()` | `youtube_channels` + `youtube_stats` |
| `/api/youtube/videos/<id>` | GET | `get_channel_videos()` | `youtube_channels` |
| `/api/youtube/<video_id>` | GET | `youtube_stats()` | YouTube Data API (extern) |
| `/api/youtube/background-refresh` | POST | `refresh_youtube()` | `youtube_channels` |
| `/api/youtube/comments` | GET | `get_comments()` | `yt_comments` |
| `/api/youtube/comments/vip` | GET | `get_vip_comments()` | `yt_comments` + `yt_community` |
| `/api/youtube/comments/fetch` | POST | `fetch_comments()` | `yt_comments` (INSERT) |
| `/api/youtube/comments/auto-like` | POST | `auto_like_comments()` | `yt_comments` |
| `/api/youtube/comments/<id>/like` | POST | `like_comment()` | `yt_comments` |
| `/api/youtube/comments/<id>/ignore` | POST | `ignore_comment()` | `yt_comments` |
| `/api/youtube/comments/<id>/suggest` | POST | `suggest_reply()` | `yt_comments` (OpenAI) |
| `/api/youtube/comments/<id>/reply` | POST | `reply_comment()` | YouTube API (extern) |
| `/api/youtube/comments/thread/<id>` | GET | `get_comment_thread()` | YouTube API (extern) |
| `/api/youtube/community/top100/comments` | GET | `get_top100_comments()` | `yt_community` |
| `/api/youtube/community/top100/loyalty` | GET | `get_top100_loyalty()` | `yt_community` |
| `/api/youtube/community/elite` | GET | `get_elite_members()` | `yt_community` |
| `/api/youtube/community/<author_id>` | GET | `get_member_profile()` | `yt_community` |
| `/api/youtube/style/examples` | GET/POST/DELETE | Style Examples CRUD | `yt_style_examples` |

### Demo Events API
| Route | Methode | Funktion | DB Tabelle |
|---|---|---|---|
| `/api/demos` | GET | `get_demos()` | `demo_events` |
| `/api/demos/all` | GET | `get_all_demos()` | `demo_events` |
| `/api/demos/categorize` | POST | `categorize_events()` | `demo_events` |
| `/api/demos/categories` | GET | `get_categories()` | `demo_events` |
| `/api/demo/feedback` | POST | `demo_feedback()` | `demo_events` |
| `/api/demos/invalid` | POST | `mark_invalid()` | `demo_events` |
| `/api/demo/validate` | POST | `demo_validate()` | `demo_events` |

### Tasks API (interne Tasks)
| Route | Methode | Funktion | DB Tabelle |
|---|---|---|---|
| `/api/tasks` | GET | `get_tasks()` | `tasks` |
| `/api/tasks` | POST | `create_task()` | `tasks` |
| `/api/tasks/<id>` | GET | `get_task()` | `tasks` |
| `/api/tasks/<id>` | PUT | `update_task()` | `tasks` |
| `/api/tasks/<id>` | DELETE | `delete_task()` | `tasks` |
| `/api/tasks/<id>/status` | PATCH | `update_task_status()` | `tasks` |
| `/api/tasks/<id>/archive` | POST | `archive_task()` | `tasks` |
| `/api/tasks/move` | POST | `move_task()` | `tasks` |

### Agent Tasks API (OpenClaw Agent Tasks)
| Route | Methode | Funktion | DB Tabelle |
|---|---|---|---|
| `/api/db/tasks` | GET | `get_agent_tasks()` | `agent_tasks` |
| `/api/db/tasks` | POST | `create_agent_task()` | `agent_tasks` |
| `/api/db/tasks/<id>/stop` | POST | `stop_agent_task()` | `agent_tasks` |
| `/api/db/tasks/<id>/status` | PATCH | `update_agent_task_status()` | `agent_tasks` |

### News API
| Route | Methode | Funktion | DB Tabelle |
|---|---|---|---|
| `/api/news` | GET | `get_news_events()` | `news_events` |
| `/api/news/woke-filter` | GET | `get_woke_filtered_news()` | `news_events` |
| `/api/news/sources` | GET | `get_news_sources()` | `news_sources` |
| `/api/news/sources` | POST | `add_news_source()` | `news_sources` |
| `/api/news/sources/<id>` | DELETE | `delete_news_source()` | `news_sources` |
| `/api/news/fetch` | POST | `fetch_news()` | `news_events` (INSERT) |
| `/api/news/<id>/read` | POST | `mark_news_read()` | `news_events` |
| `/api/news_events` | GET | `get_hermes_news()` | `news_events` |
| `/api/news_events/refresh` | GET | `news_events_refresh()` | News Sources (scrape) |

### Stats & Monitoring API
| Route | Methode | Funktion | Zweck |
|---|---|---|---|
| `/api/stats/dashboard` | GET | `get_dashboard_stats()` | Dashboard-Statistiken |
| `/api/db/stats` | GET | `get_db_stats()` | DB Statistiken |
| `/api/stats/models` | GET | `get_model_stats()` | Modell-Nutzung |
| `/api/stats/providers` | GET | `get_provider_stats()` | Provider-Statistiken |
| `/api/stats/agents` | GET | `get_agent_stats()` | Agent-Aktivität |
| `/api/stats/system` | GET | `get_system_stats()` | System-Ressourcen |
| `/api/system-health` | GET | `system_health()` | System-Healthcheck |
| `/api/openclaw/stats` | GET | `openclaw_stats()` | OpenClaw Stats |
| `/api/openclaw/models` | GET | `top_models()` | Top Modelle |
| `/api/openclaw/tools` | GET | `top_tools()` | Top Tools |
| `/api/openclaw/sync` | GET | `sync_stats()` | Sync-Statistiken |
| `/api/agents/usage` | GET | `agents_usage()` | Agent-Nutzung |
| `/api/gateway/usage` | GET | `gateway_usage()` | Gateway-Nutzung |
| `/api/quota` | GET | `get_quota()` | API Quota |
| `/api/prices` | GET | `get_prices()` | Token-Preise |
- `/api/healthz` → Health Check (Alias zu /api/system-health)
- `/api/watchlist` → GET watchlist items
- `/api/portfolio` → GET portfolio positions
| `/api/events/today` | GET | `get_events_today()` | Heute Events |

### Agents API
| Route | Methode | Funktion | Zweck |
|---|---|---|---|
| `/api/agents` | GET | `agents_list()` | Alle Agents |
| `/api/agents/status` | GET | `agents_status()` | Agent-Status |
| `/api/agents/<agent>/report` | GET | `agent_report()` | Agent-Report |
| `/api/agents/<agent>/<action>` | POST | `agent_action()` | Agent-Aktion |

### Rheingold API
| Route | Methode | Funktion | Zweck |
|---|---|---|---|
| `/api/rheingold/mails` | GET/POST/PUT/DELETE | Mail CRUD | Rheingold E-Mails |
| `/api/rheingold/mail/send/<id>` | POST | `rheingold_mail_send()` | SMTP Versand |
| `/api/rheingold/engine-logs` | GET | `rheingold_engine_logs()` | Engine Logs |
| `/api/rheingold/findings` | GET | `rheingold_findings()` | Findings |
| `/api/rheingold/orgs` | GET | `rheingold_orgs()` | Organisationen |
| `/api/rheingold/ifg` | GET | `rheingold_ifg()` | IFG-Daten |
| `/api/rheingold/activity` | GET | `rheingold_activity()` | Aktivität |
| `/api/rheingold/status` | GET | `rheingold_status()` | Status-Übersicht |
| `/api/rheingold/engine-status` | GET | `rheingold_engine_status()` | Engine Status |
| `/api/rheingold/expansion-rate` | GET | `rheingold_expansion_rate()` | Wachstumsrate |
| `/api/rheingold/activity-feed` | GET | `rheingold_activity_feed()` | Activity Feed |
| `/api/rheingold/network-connections` | GET | `rheingold_network_connections()` | Netzwerk |
| `/api/rheingold/profiles` | GET | `rheingold_profiles()` | Profile |
| `/api/rheingold/orgas` | GET | `rheingold_orgas()` | Orgas |
| `/api/rheingold/ngo-map` | GET | `rheingold_ngo_map()` | NGO Map Daten |
| `/api/rheingold/entity/<id>` | GET | `rheingold_entity()` | Einzelne Entity |
| `/api/rheingold/live-stats` | GET | `rheingold_live_stats()` | Live-Statistiken |
| `/api/rheingold/crawl-queue` | GET | `rheingold_crawl_queue_api()` | Crawl Queue |

### Trading & Freqtrade API
| Route | Methode | Funktion | Zweck |
|---|---|---|---|
| `/api/trading/pairs` | GET | `trading_pairs()` | Trading-Paare |
| `/api/trading/queue` | GET | `trading_queue()` | Trading Queue |
| `/api/trading/top` | GET | `trading_top()` | Top Trades |
| `/api/trading/bots` | GET | `trading_bots()` | Bot-Liste |
| `/api/freqtrade/profit` | GET | `freqtrade_profit()` | Profit |
| `/api/freqtrade/status` | GET | `freqtrade_status()` | Bot Status |
| `/api/freqtrade/balance` | GET | `freqtrade_balance()` | Balance |
| `/api/freqtrade/performance` | GET | `freqtrade_performance()` | Performance |
| `/api/backtest-status` | GET | `backtest_status()` | Backtest Status |

### Athena API
| Route | Methode | Funktion | Zweck |
|---|---|---|---|
| `/api/athena/backtest-results` | GET | `athena_backtest_results()` | Athena Backtests |
| `/api/athena/marathon-status` | GET | `athena_marathon_status()` | Marathon Status |

### Sonstige API
| Route | Methode | Funktion | Zweck |
|---|---|---|---|
| `/api/logs` | GET/POST | `get_logs()` / `add_log()` | Logs |
| `/api/learnings/status` | GET | `learnings_status()` | Learnings |
| `/api/orpheus/report` | GET | `orpheus_report()` | Orpheus Report |
| `/api/hestia/comments` | GET | `hestia_comments()` | Hestia Comments |
| `/api/hestia/stats` | GET | `hestia_stats()` | Hestia Stats |
| `/api/network/devices` | GET | `network_devices()` | Netzwerk-Geräte |
| `/api/network/device/<ip>` | GET | `network_device()` | Einzelnes Gerät |
| `/api/network/update` | POST | `network_update()` | Gerät aktualisieren |
| `/api/mails/himalaya` | GET | `himalaya_mails()` | Himawaya Mail-Liste |
| `/api/mails/himalaya/read` | POST | `himalaya_mail_read()` | Himawaya Mail lesen |

## DB Tabellen (aus Queries extrahiert)
- `youtube_channels` — YT Kanäle
- `youtube_stats` — YT Statistiken (pro Kanal, mit fetched_at)
- `iggy_playlists` — Playlist Fortschritt
- `yt_comments` — YT Kommentare
- `yt_community` — YT Community-Mitglieder
- `yt_style_examples` — Antwort-Stil Beispiele
- `demo_events` — Demo-Events
- `tasks` — Interne Aufgaben
- `agent_tasks` — OpenClaw Agent Tasks
- `news_events` — News-Artikel
- `news_sources` — News-Quellen

## Templates
| Template | Datei | Zweck |
|---|---|---|
| NGO Map | `ngo_map.html` | Interaktive Karte |
| Network | `network.html` | Netzwerk-Übersicht |
| Portfolio | `portfolio.html` | Portfolio-Ansicht |
| Orpheus Report | `orpheus_report.html` | Backup-Report |
| Rheingold | `rheingold.html` | Rheingold Dashboard |
| Rheingold Content | `rheingold_content.html` | Rheingold Detailansicht |
| Rheingold Findings | `rheingold_findings.html` | Research Findings |
| Backtest | `backtest_tab.html` | Trading Backtests |
| Athena | `athena_tab.html` | Athena Marathon |
| News | (render_template_string in `news_page()`) | News-Seite |

## Static Assets
- `/static/leaflet/` — Leaflet.js (Karten)
- `/static/vendor/` — Externe Libraries

## Known Bugs
- **Port 5001 Conflict:** Flask.log zeigt "Address already in use" — DEV-Instanz konnte nicht starten, weil Port 5001 bereits belegt war. Vor Neustart prüfen: `lsof -i :5001`
- **Keine dashboard_fix Einträge** in `agent_knowledge` (Tabelle leer oder keine Einträge mit category='dashboard_fix')

## Deployment
- **DEV starten:** `cd /opt/dashboard-dev && python3 app.py &`
- **DEV stoppen:** `pkill -f "python3.*dashboard-dev"`
- **DEV Logs:** `tail -f /opt/dashboard-dev/flask.log`
- **Backup vor Fix:** `cp -p app.py app.py.bak.$(date +%H%M%S)`
- **PROD: FINGER WEG** (Port 5000, `/opt/dashboard/`)

## Schrott-Archiv Regel
- Kaputten Code anschauen
- Lernen: relevantes in RUNBOOK.md oder `agent_knowledge`
- Archivieren: `mv nach /opt/dashboard-dev/archive/`
- 7 Tage behalten, dann: `find /opt/dashboard-dev/archive/ -mtime +7 -delete`

## Backup Dateien im Verzeichnis
| Datei | Typ |
|---|---|
| `app.py.bak.sprint2` | App Backup Sprint 2 |
| `index.html.bak.1774945201` | Index Backup |
| `index.html.bak.1775037853` | Index Backup |
| `index.html.bak.1775038906` | Index Backup |
| `index.html.bak.jsfix.1774945558` | JS Fix Backup |
| `index.html.bak.sprint2` | Index Sprint 2 |
| `index.html.bak.taskcontrol` | Task Control Backup |
| `rheingold_content-old01.html` | Altes Template |
| `rheingold_content-old02.html` | Altes Template |
