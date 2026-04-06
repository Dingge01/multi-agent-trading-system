"""
技术指标计算工具

独立的技术指标计算模块，供Technical Agent和回测引擎使用。
所有指标基于pandas_ta，纯Python实现，无需编译ta-lib。

面试要点：
- MACD原理：短期EMA(12) - 长期EMA(26)，信号线为MACD的EMA(9)
- RSI原理：一段时间内上涨幅度占总波动的比例
- 布林带原理：中轨=SMA(20)，上下轨=中轨±2倍标准差
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pandas as pd
import pandas_ta as ta
import numpy as np


@dataclass
class IndicatorSet:
    """一组技术指标的快照"""
    macd: float | None = None
    macd_signal: float | None = None
    macd_histogram: float | None = None
    rsi_14: float | None = None
    bb_upper: float | None = None
    bb_middle: float | None = None
    bb_lower: float | None = None
    sma_20: float | None = None
    sma_50: float | None = None
    sma_200: float | None = None
    atr_14: float | None = None
    volume_sma_20: float | None = None


def compute_all_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """为DataFrame添加所有技术指标列"""
    if df.empty:
        return df

    result = df.copy()
    result.ta.macd(append=True)
    result.ta.rsi(append=True)
    result.ta.bbands(length=20, append=True)
    result.ta.sma(length=20, append=True)
    result.ta.sma(length=50, append=True)
    result.ta.sma(length=200, append=True)
    result.ta.atr(append=True)
    result["Volume_SMA_20"] = result["Volume"].rolling(20).mean()
    return result


def get_latest_indicators(df: pd.DataFrame) -> IndicatorSet:
    """从已计算指标的DataFrame中提取最新值"""
    enriched = compute_all_indicators(df)
    if enriched.empty:
        return IndicatorSet()

    latest = enriched.iloc[-1]

    def safe_get(col: str) -> float | None:
        val = latest.get(col)
        if val is not None and not pd.isna(val):
            return float(val)
        return None

    return IndicatorSet(
        macd=safe_get("MACD_12_26_9"),
        macd_signal=safe_get("MACDs_12_26_9"),
        macd_histogram=safe_get("MACDh_12_26_9"),
        rsi_14=safe_get("RSI_14"),
        bb_upper=safe_get("BBU_20_2.0"),
        bb_middle=safe_get("BBM_20_2.0"),
        bb_lower=safe_get("BBL_20_2.0"),
        sma_20=safe_get("SMA_20"),
        sma_50=safe_get("SMA_50"),
        sma_200=safe_get("SMA_200"),
        atr_14=safe_get("ATRr_14"),
        volume_sma_20=safe_get("Volume_SMA_20"),
    )


def detect_crossover(series_fast: pd.Series, series_slow: pd.Series) -> str:
    """检测金叉/死叉"""
    if len(series_fast) < 2 or len(series_slow) < 2:
        return "NONE"

    prev_fast, curr_fast = series_fast.iloc[-2], series_fast.iloc[-1]
    prev_slow, curr_slow = series_slow.iloc[-2], series_slow.iloc[-1]

    if prev_fast <= prev_slow and curr_fast > curr_slow:
        return "GOLDEN_CROSS"
    if prev_fast >= prev_slow and curr_fast < curr_slow:
        return "DEATH_CROSS"
    return "NONE"


def calculate_support_resistance(df: pd.DataFrame, window: int = 20) -> dict[str, float]:
    """简化版支撑位/阻力位计算"""
    if len(df) < window:
        return {"support": 0, "resistance": 0}

    recent = df.tail(window)
    return {
        "support": float(recent["Low"].min()),
        "resistance": float(recent["High"].max()),
    }
