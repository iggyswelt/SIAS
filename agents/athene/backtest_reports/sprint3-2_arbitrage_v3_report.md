# SPRINT3-2: Arbitrage v3 Backtest Report

**Date:** 2026-04-04  
**Timeframe:** 1h | **Period:** 2025-01-01 → 2026-03-16  
**Pairs:** BTC, ETH, SOL, AVAX, LINK, DOGE, ADA, DOT, XRP, MATIC (all /USDT)  
**Starting Balance:** 1000 USDT | **Market Change:** -52.55%

---

## v2 → v3 Changes
| Parameter | v2 | v3 |
|---|---|---|
| Stoploss | -2.5% | **-1.5%** |
| diverge_std range | 1.0–3.0 | **1.5–2.5** |
| diverge_std default | 1.8 | **2.2** |

---

## Comparison Table

| Metric | v2 | v3 | Δ |
|---|---|---|---|
| **Trades** | 62 | 35 | -44% |
| **Win Rate** | 79.0% | 74.3% | -4.7pp |
| **Total Profit** | -2.433 USDT | -0.368 USDT | +2.065 USDT |
| **Total Profit %** | -0.24% | -0.04% | +0.20pp |
| **Max Drawdown** | 5.244 USDT (0.52%) | 1.887 USDT (0.19%) | -64% |
| **Sharpe Ratio** | -0.25 | -0.05 | +0.20 |
| **Sortino** | -37.31 | -10.44 |大幅改善 |
| **Profit Factor** | 0.77 | 0.92 | +0.15 |
| **Avg Duration** | 4h28m | 2h29m | -44% |
| **Max Consec. Losses** | 4 | 3 | -1 |

---

## Exit Analysis v3
| Exit Reason | Exits | Avg Profit | Win% |
|---|---|---|---|
| ROI | 14 | +0.77% | 100% |
| Trailing Stop | 12 | +0.26% | 100% |
| Stop Loss | 9 | -1.70% | 0% |

---

## Key Findings

1. **v3 is significantly better** — loss reduced by 85% (-0.37 vs -2.43 USDT)
2. Fewer trades (35 vs 62) but higher quality — diverge_std tightening works
3. Drawdown cut by 64% — tighter stoploss prevents big bleed
4. **BUT: Still negative overall** (-0.04%) — no v4 dry_run recommendation yet
5. Stop losses are the only losing exit — avg -1.7% per hit (9 trades = -4.56 USDT)
6. All winning exits (ROI + trailing) total +4.19 USDT — not enough to offset stops

## Recommendation

**NO v4 dry_run yet.** Total profit still negative. Next steps to consider:
- Add a correlation quality filter (require corr > 0.90 instead of 0.85)
- Reduce max open trades to 1-2 (force better capital allocation)
- Add volume filter (avoid low-liquidity entries)
- Test with longer timeframe (4h) for fewer but stronger signals

**⛔ KEIN LIVE-TRADING ohne Iggy-Freigabe!**
