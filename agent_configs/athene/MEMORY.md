# Athene — Permanente Regeln
- Cronos: [SERVER_IP_CRONOS] (SSH für schwere Berechnungen/Hyperopt).
- Freqtrade UI: http://[SERVER_IP_CRONOS]:8080 (iggy / [REDACTED]).
- Fokus: Arbitrage-Strategien (Triangle/Cross-Exchange).
- Wissen: NUR in PostgreSQL agent_knowledge und athene_trading DB.

## V3 Regel
Keine lokalen MD-Files für Lernkurven. Jede erfolgreiche Arbitrage-Erkennung wird geloggt.

## Strategie-Status (Stand 06.04.2026)
- v3 (19 Pairs): BESTER Kandidat, +0.40%, 88.2% WR, 0.25% DD
- v15 (Hyperopt): +0.28%, solide aber weniger Trades
- v1-v2: gescheitert (Fees fressen Spreads)
- v16 PLAN: dynamischer Spread (ATR), Liquiditätsfilter, Trailing SL

## Erkenntnisse
- Pair-Auswahl > Strategie-Logik (v3 mit 5 Pairs = minus, mit 19 = plus)
- Hoher Spread + niedriges Volumen = Falle (RDNT 30% aber illiquid)
- CEX-CEX Arbitrage bei Top-Pairs tot (<0.1% Spread)
- Mid/Low-Cap Pairs haben Chancen aber Slippage-Risiko

## Infra
- Freqtrade auf Cronos (192.168.23.80) via Docker
- bot01 (8081), bot02 (8082), bot03 (8084)
- Backtests: /mnt/bigdata/freqtrade/
- SIAS Event Bus: sias:arbitrage Channel aktiv

## Regeln
- KEIN Live-Trading ohne Iggy Freigabe
- dry_run: true IMMER
- Ergebnisse über Event Bus publizieren
- Autonom iterieren: v16, v17, ... bis profitabel

## Iterations-Regel (seit 06.04.2026)
- Nach jedem Backtest: SOFORT bewerten
- Besser als v3 Baseline? → speichern, weiter iterieren
- Schlechter als v3? → verwerfen, Lesson lernen, nächste Version
- NICHT FRAGEN ob weiter — IMMER weiter
- NICHT auf Iggy warten zwischen Iterationen
- Ergebnis + Lesson in DB speichern: category='athene_backtest'
- Event Bus: backtest_complete nach jedem Run
- v3 ist die Baseline: 17 Trades, 88.2% WR, +4.04 USDT, 0.25% DD
- Ziel: MEHR Trades bei gleicher oder besserer WR

## v16 Lesson (GELERNT)
- ATR-basierter Spread filtert zu aggressiv → 5 statt 17 Trades
- Lösung: diverge_std senken, spread_threshold lockern
- NICHT den Filter verschärfen wenn zu wenig Trades kommen
