"""
Technical Agent - 技术面分析Agent

职责：K线形态识别、技术指标计算（MACD/RSI/布林带），输出技术面评分和交易信号。

面试要点：
- MACD：短期EMA与长期EMA的差值，金叉/死叉判断趋势转折
- RSI：相对强弱指标，>70超买，<30超卖
- 布林带：价格在上轨附近可能回调，下轨附近可能反弹
- 为什么用pandas_ta而不是ta-lib？pandas_ta纯Python，安装无障碍
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

import yfinance as yf
import pandas as pd
import pandas_ta as ta
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage

from config.settings import CONFIG


@dataclass
class TechnicalAnalysis:
    ticker: str
    current_price: float
    macd: float | None
    macd_signal: float | None
    macd_histogram: float | None
    rsi: float | None
    bb_upper: float | None
    bb_middle: float | None
    bb_lower: float | None
    sma_20: float | None
    sma_50: float | None
    volume_trend: str = "NORMAL"
    score: float = 0.0
    signal: str = "HOLD"
    reasoning: str = ""


class TechnicalAgent:
    """
    技术面分析Agent：拉取K线数据 → 计算技术指标 → LLM综合研判 → 输出评分与信号

    架构角色：并行Fan-out的三个分析Agent之一，与Fundamental/Sentiment并行执行。
    """

    SYSTEM_PROMPT = """你是一位资深的技术分析师。你的任务是基于以下技术指标，给出股票的技术面评分和交易信号。

评分标准 (1-10分):
- MACD: 金叉(histogram>0且上升)(+2), 死叉(histogram<0且下降)(-2)
- RSI: 30-70正常区间(+1), <30超卖可能反弹(+2), >70超买可能回调(-2)
- 布林带: 价格在中轨附近(+1), 触及下轨(+2超卖), 触及上轨(-1超买)
- 均线: 价格>SMA20>SMA50多头排列(+2), 反之空头排列(-2)
- 成交量: 放量上涨(+1), 缩量下跌(+1), 放量下跌(-2)

请输出JSON格式:
{
    "score": <1-10的综合评分>,
    "signal": "<BUY/SELL/HOLD>",
    "reasoning": "<100字以内的技术面分析理由>"
}"""

    def __init__(self):
        self.llm = ChatOpenAI(
            model=CONFIG.llm.model,
            temperature=CONFIG.llm.temperature,
            api_key=CONFIG.llm.api_key,
        )

    def fetch_and_compute(self, ticker: str, period: str = "6mo") -> dict[str, Any]:
        stock = yf.Ticker(ticker)
        df = stock.history(period=period)
        if df.empty:
            return {}

        df.ta.macd(append=True)
        df.ta.rsi(append=True)
        df.ta.bbands(append=True)
        df.ta.sma(length=20, append=True)
        df.ta.sma(length=50, append=True)

        latest = df.iloc[-1]
        prev = df.iloc[-2] if len(df) > 1 else latest

        vol_avg = df["Volume"].rolling(20).mean().iloc[-1]
        vol_current = latest.get("Volume", 0)
        if vol_current > vol_avg * 1.5:
            volume_trend = "HIGH"
        elif vol_current < vol_avg * 0.5:
            volume_trend = "LOW"
        else:
            volume_trend = "NORMAL"

        return {
            "current_price": latest["Close"],
            "macd": latest.get("MACD_12_26_9"),
            "macd_signal": latest.get("MACDs_12_26_9"),
            "macd_histogram": latest.get("MACDh_12_26_9"),
            "rsi": latest.get("RSI_14"),
            "bb_upper": latest.get("BBU_5_2.0"),
            "bb_middle": latest.get("BBM_5_2.0"),
            "bb_lower": latest.get("BBL_5_2.0"),
            "sma_20": latest.get("SMA_20"),
            "sma_50": latest.get("SMA_50"),
            "volume_trend": volume_trend,
            "price_change_5d": (latest["Close"] - df.iloc[-5]["Close"]) / df.iloc[-5]["Close"] if len(df) >= 5 else 0,
        }

    def analyze(self, ticker: str) -> TechnicalAnalysis:
        indicators = self.fetch_and_compute(ticker)
        if not indicators:
            return TechnicalAnalysis(ticker=ticker, current_price=0, macd=None,
                                     macd_signal=None, macd_histogram=None, rsi=None,
                                     bb_upper=None, bb_middle=None, bb_lower=None,
                                     sma_20=None, sma_50=None)

        user_prompt = f"""请分析 {ticker} 的技术指标（当前价格: ${indicators['current_price']:.2f}）：

- MACD: {indicators.get('macd', 'N/A'):.4f}
- MACD Signal: {indicators.get('macd_signal', 'N/A')}
- MACD Histogram: {indicators.get('macd_histogram', 'N/A')}
- RSI(14): {indicators.get('rsi', 'N/A')}
- Bollinger Upper: {indicators.get('bb_upper', 'N/A')}
- Bollinger Middle: {indicators.get('bb_middle', 'N/A')}
- Bollinger Lower: {indicators.get('bb_lower', 'N/A')}
- SMA(20): {indicators.get('sma_20', 'N/A')}
- SMA(50): {indicators.get('sma_50', 'N/A')}
- Volume Trend: {indicators.get('volume_trend', 'N/A')}
- 5-Day Price Change: {indicators.get('price_change_5d', 0):.2%}"""

        response = self.llm.invoke([
            SystemMessage(content=self.SYSTEM_PROMPT),
            HumanMessage(content=user_prompt),
        ])

        try:
            result = json.loads(response.content)
        except json.JSONDecodeError:
            result = {"score": 5.0, "signal": "HOLD", "reasoning": "LLM输出解析失败"}

        return TechnicalAnalysis(
            ticker=ticker,
            current_price=indicators["current_price"],
            macd=indicators.get("macd"),
            macd_signal=indicators.get("macd_signal"),
            macd_histogram=indicators.get("macd_histogram"),
            rsi=indicators.get("rsi"),
            bb_upper=indicators.get("bb_upper"),
            bb_middle=indicators.get("bb_middle"),
            bb_lower=indicators.get("bb_lower"),
            sma_20=indicators.get("sma_20"),
            sma_50=indicators.get("sma_50"),
            volume_trend=indicators.get("volume_trend", "NORMAL"),
            score=result.get("score", 5.0),
            signal=result.get("signal", "HOLD"),
            reasoning=result.get("reasoning", ""),
        )

    def run(self, state: dict[str, Any]) -> dict[str, Any]:
        """LangGraph节点入口"""
        ticker = state["ticker"]
        analysis = self.analyze(ticker)
        return {
            "analyses": [{
                "agent": "technical",
                "ticker": ticker,
                "score": analysis.score,
                "signal": analysis.signal,
                "reasoning": analysis.reasoning,
                "data": {
                    "current_price": analysis.current_price,
                    "rsi": analysis.rsi,
                    "macd_histogram": analysis.macd_histogram,
                    "volume_trend": analysis.volume_trend,
                },
            }]
        }
