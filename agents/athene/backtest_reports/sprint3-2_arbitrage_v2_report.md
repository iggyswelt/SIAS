# SPRINT3-2: Arbitrage Optimierung — Backtest Report

**Datum:** 2026-04-04  
**Strategien:** SIAS_Arbitrage_v1 vs SIAS_Arbitrage_v2  
**Timerange:** 2025-01-01 → 2026-03-16  
**Paare:** BTC/USDT, ETH/USDT, SOL/USDT, ADA/USDT, AVAX/USDT  
**Stake:** 30 USDT pro Trade, max 3 open

---

## v1 Baseline (5m, 3425 Trades) — aus Backtest 2026-04-03

| Metrik | Wert |
|--------|------|
| Trades | 3,425 |
| Win Rate | 55.2% |
| Avg Profit | -0.26% |
| **Total Profit** | **-899.35 USDT (-89.94%)** |
| Drawdown | 907.26 USDT (90.01%) |
| Avg Duration | 1:02:00 |

**Diagnose:** Katastrophal. Zu viele Trades auf 5m, hoher Slippage, Stoploss-Treffer fressen Gewinne.

---

## v2 (1h, 38 Trades)

| Metrik | Wert |
|--------|------|
| Trades | 38 |
| Win Rate | **73.7%** |
| Avg Profit | -0.28% |
| **Total Profit** | **-3.17 USDT (-0.32%)** |
| **Drawdown** | **4.61 USDT (0.46%)** |
| Avg Duration | 4:49:00 |

### Exit Reasons:
- ROI (19 trades): +4.20 USDT (100% win)
- Trailing Stop (9 trades): +0.69 USDT (100% win)
- Stop Loss (10 trades): -8.06 USDT (0% win)

### Pro Pair:
- BTC/USDT: 0 Trades (Referenz-Pair)
- SOL/USDT: 12 Trades, -0.41 USDT (83.3% WR)
- ETH/USDT: 15 Trades, -1.00 USDT (80.0% WR)
- ADA/USDT: 5 Trades, -0.71 USDT (60.0% WR)
- AVAX/USDT: 6 Trades, -1.05 USDT (50.0% WR)

---

## v2 (4h, 4 Trades)

| Metrik | Wert |
|--------|------|
| Trades | 4 |
| Win Rate | 50.0% |
| **Total Profit** | **-0.95 USDT (-0.10%)** |
| Drawdown | 1.61 USDT (0.16%) |

**Diagnose:** Zu wenig Signale auf 4h. Nicht verwendbar.

---

## Zusammenfassung v1 vs v2

| Metrik | v1 (5m) | v2 (1h) | Δ |
|--------|---------|---------|---|
| Trades | 3,425 | 38 | -98.9% |
| Win Rate | 55.2% | 73.7% | +18.5pp |
| Total Profit | -899.35 | -3.17 | +99.6% |
| Drawdown | 90.01% | 0.46% | -89.55pp |

---

## v2 Verbesserungen vs v1
1. ✅ Timeframe 1h statt 5m — deutlich weniger Noise
2. ✅ Trendfilter (EMA30/60) — filtert Seitwärts/Downtrend-Entries
3. ✅ Spread-Threshold (ATR-basiert) — verhindert Eintritt bei hoher Volatilität
4. ✅ Weniger Trades, höhere Qualität

## Offene Probleme
- ⚠️ Noch leicht negativ (-3.17 USDT). ROI+Trailing (+4.89) wird von Stoploss (-8.06) übertroffen
- ⚠️ 4h liefert zu wenig Signale
- 🔧 Nächster Schritt: Stoploss optimieren (vielleicht -0.015 statt -0.025) oder entry-signals verschärfen

## Backtest-Logs gespeichert
- v2 1h: ~/freqtrade/user_data/backtest_results/backtest-result-2026-04-04_15-41-16.zip
- v2 4h: ~/freqtrade/user_data/backtest_results/backtest-result-2026-04-04_15-41-50.zip
- Logfile: ~/freqtrade/user_data/backtest_results/bt_v2_log_*.log
