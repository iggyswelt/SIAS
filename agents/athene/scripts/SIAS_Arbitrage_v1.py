"""
SIAS_Arbitrage_v1.py — Pair-Correlation Arbitrage Strategy
Inspired by Catalyst/Enigma arbitrage bot concept.

Core idea: Monitor two highly correlated pairs (e.g. BTC/USDT and ETH/USDT).
When their price ratio diverges from the rolling mean beyond a threshold,
enter the pair that is relatively "cheap" and exit when ratio reverts.

⚠️ dry_run = true — NEVER set to false without explicit approval!
"""

import logging
from typing import Optional
from pandas import DataFrame, Series
from freqtrade.strategy import IStrategy, DecimalParameter, IntParameter
import talib.abstract as ta

logger = logging.getLogger(__name__)


class SIAS_Arbitrage_v1(IStrategy):
    INTERFACE_VERSION = 3

    # ── Timeframe & metadata ──────────────────────────────────────
    timeframe = "5m"
    can_short = False

    # ── ROI table (conservative — arbitrage targets small profits) ─
    minimal_roi = {
        "0": 0.015,      # 1.5% immediate take-profit
        "30": 0.008,     # 0.8% after 30 min
        "60": 0.004,     # 0.4% after 1h
        "120": 0.001,    # 0.1% after 2h — let trailing handle rest
    }

    # ── Stoploss ──────────────────────────────────────────────────
    stoploss = -0.02  # 2% hard stop

    # ── Trailing stop ─────────────────────────────────────────────
    trailing_stop = True
    trailing_stop_positive = 0.003      # 0.3% trail once in profit
    trailing_stop_positive_offset = 0.005  # activate at 0.5% profit
    trailing_only_offset_is_reached = True

    # ── Order settings ────────────────────────────────────────────
    startup_candle_count: int = 200

    # ── Hyperoptable parameters ───────────────────────────────────
    corr_window = IntParameter(20, 100, default=50, space="buy", optimize=True)
    ratio_window = IntParameter(20, 100, default=50, space="buy", optimize=True)
    diverge_std = DecimalParameter(1.0, 3.0, default=1.8, space="buy", optimize=True)
    min_corr = DecimalParameter(0.7, 0.98, default=0.85, space="buy", optimize=True)

    # The "reference pair" to compute correlation against
    ref_pair = "BTC/USDT"

    # ── Populate indicators ───────────────────────────────────────
    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        pair = metadata["pair"]

        # Get reference pair dataframe if available
        ref_df: Optional[DataFrame] = self.dp.get_pair_dataframe(pair=self.ref_pair)

        if ref_df is not None and not ref_df.empty:
            # Align to same timestamps
            merged = dataframe.join(ref_df["close"], rsuffix="_ref", how="inner")
            merged["ratio"] = merged["close"] / merged["close_ref"]

            # Rolling statistics on the ratio
            w = self.ratio_window.value
            merged["ratio_mean"] = merged["ratio"].rolling(w).mean()
            merged["ratio_std"] = merged["ratio"].rolling(w).std()
            merged["ratio_zscore"] = (
                (merged["ratio"] - merged["ratio_mean"]) / merged["ratio_std"]
            )

            # Rolling correlation
            cw = self.corr_window.value
            merged["corr"] = merged["close"].rolling(cw).corr(merged["close_ref"])

            # RSI for additional confirmation
            merged["rsi"] = ta.RSI(merged, timeperiod=14)

            # Bollinger Bands on ratio for exit signals
            merged["ratio_bb_upper"] = merged["ratio_mean"] + 2.0 * merged["ratio_std"]
            merged["ratio_bb_lower"] = merged["ratio_mean"] - 2.0 * merged["ratio_std"]

            # Copy back
            dataframe["ratio_zscore"] = merged["ratio_zscore"]
            dataframe["corr"] = merged["corr"]
            dataframe["ratio_mean"] = merged["ratio_mean"]
            dataframe["rsi"] = merged["rsi"]
            dataframe["ratio_bb_lower"] = merged["ratio_bb_lower"]
        else:
            # Fallback: no reference data available
            dataframe["ratio_zscore"] = 0.0
            dataframe["corr"] = 1.0
            dataframe["ratio_mean"] = 0.0
            dataframe["rsi"] = ta.RSI(dataframe, timeperiod=14)
            dataframe["ratio_bb_lower"] = 0.0

        return dataframe

    # ── Entry logic ───────────────────────────────────────────────
    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        conditions_long = []

        # Condition 1: Ratio z-score is significantly negative (pair is cheap relative to ref)
        conditions_long.append(dataframe["ratio_zscore"] < -self.diverge_std.value)

        # Condition 2: Pairs are sufficiently correlated
        conditions_long.append(dataframe["corr"] > self.min_corr.value)

        # Condition 3: Not already in overbought territory
        conditions_long.append(dataframe["rsi"] < 65)

        # Combine
        if conditions_long:
            dataframe.loc[
                reduce(lambda a, b: a & b, conditions_long),
                ["enter_long", "enter_tag"],
            ] = (1, "arb_diverge_long")

        return dataframe

    # ── Exit logic ────────────────────────────────────────────────
    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # Exit when ratio reverts to mean (z-score crosses above 0)
        conditions_exit = (
            (dataframe["ratio_zscore"] > 0)
            & (dataframe["corr"] > 0.7)
        )

        dataframe.loc[conditions_exit, ["exit_long", "exit_tag"]] = (1, "arb_revert")

        return dataframe


# Need reduce for combining conditions
from functools import reduce
