"""
Fundamental Agent - 基本面分析Agent

职责：分析财报、营收增长、估值指标（PE/PB/ROE），输出基本面评分和投资建议。

面试要点：
- 为什么独立成Agent？因为基本面分析需要专门的财务知识和数据源，与技术面/情绪面解耦
- 数据来源：yfinance获取实时财务数据，无需付费API
- 输出标准化：统一的评分体系(1-10)便于下游Debate Agent比较
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

import yfinance as yf
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage

from config.settings import CONFIG


@dataclass
class FundamentalAnalysis:
    ticker: str
    pe_ratio: float | None
    pb_ratio: float | None
    roe: float | None
    revenue_growth: float | None
    profit_margin: float | None
    debt_to_equity: float | None
    free_cash_flow: float | None
    score: float = 0.0
    signal: str = "HOLD"
    reasoning: str = ""


class FundamentalAgent:
    """
    基本面分析Agent：拉取财报数据 → 计算估值指标 → LLM综合研判 → 输出评分与信号

    架构角色：并行Fan-out的三个分析Agent之一，结果汇入Debate Agent。
    """

    SYSTEM_PROMPT = """你是一位资深的基本面分析师。你的任务是基于以下财务指标，给出股票的基本面评分和投资建议。

评分标准 (1-10分):
- PE ratio: <15优秀(+2), 15-25正常(+1), >25偏高(-1)
- PB ratio: <1.5优秀(+2), 1.5-3正常(+1), >3偏高(-1)
- ROE: >20%优秀(+2), 10-20%良好(+1), <10%一般(-1)
- Revenue Growth: >20%高增长(+2), 5-20%稳健(+1), <5%缓慢(-1)
- Profit Margin: >20%优秀(+2), 10-20%良好(+1), <10%较弱(-1)
- Debt/Equity: <0.5低杠杆(+1), 0.5-1适中(0), >1高杠杆(-1)
- Free Cash Flow: 正值(+1), 负值(-1)

请输出JSON格式:
{
    "score": <1-10的综合评分>,
    "signal": "<BUY/SELL/HOLD>",
    "reasoning": "<100字以内的分析理由>"
}"""

    def __init__(self):
        self.llm = ChatOpenAI(
            model=CONFIG.llm.model,
            temperature=CONFIG.llm.temperature,
            api_key=CONFIG.llm.api_key,
        )

    def fetch_fundamentals(self, ticker: str) -> dict[str, Any]:
        stock = yf.Ticker(ticker)
        info = stock.info
        return {
            "pe_ratio": info.get("trailingPE"),
            "pb_ratio": info.get("priceToBook"),
            "roe": info.get("returnOnEquity"),
            "revenue_growth": info.get("revenueGrowth"),
            "profit_margin": info.get("profitMargins"),
            "debt_to_equity": info.get("debtToEquity"),
            "free_cash_flow": info.get("freeCashflow"),
            "market_cap": info.get("marketCap"),
            "sector": info.get("sector"),
            "industry": info.get("industry"),
        }

    def analyze(self, ticker: str) -> FundamentalAnalysis:
        fundamentals = self.fetch_fundamentals(ticker)

        user_prompt = f"""请分析 {ticker} 的基本面数据：

- PE Ratio: {fundamentals.get('pe_ratio', 'N/A')}
- PB Ratio: {fundamentals.get('pb_ratio', 'N/A')}
- ROE: {fundamentals.get('roe', 'N/A')}
- Revenue Growth: {fundamentals.get('revenue_growth', 'N/A')}
- Profit Margin: {fundamentals.get('profit_margin', 'N/A')}
- Debt/Equity: {fundamentals.get('debt_to_equity', 'N/A')}
- Free Cash Flow: {fundamentals.get('free_cash_flow', 'N/A')}
- Market Cap: {fundamentals.get('market_cap', 'N/A')}
- Sector: {fundamentals.get('sector', 'N/A')}"""

        response = self.llm.invoke([
            SystemMessage(content=self.SYSTEM_PROMPT),
            HumanMessage(content=user_prompt),
        ])

        try:
            result = json.loads(response.content)
        except json.JSONDecodeError:
            result = {"score": 5.0, "signal": "HOLD", "reasoning": "LLM输出解析失败，默认HOLD"}

        return FundamentalAnalysis(
            ticker=ticker,
            pe_ratio=fundamentals.get("pe_ratio"),
            pb_ratio=fundamentals.get("pb_ratio"),
            roe=fundamentals.get("roe"),
            revenue_growth=fundamentals.get("revenue_growth"),
            profit_margin=fundamentals.get("profit_margin"),
            debt_to_equity=fundamentals.get("debt_to_equity"),
            free_cash_flow=fundamentals.get("free_cash_flow"),
            score=result.get("score", 5.0),
            signal=result.get("signal", "HOLD"),
            reasoning=result.get("reasoning", ""),
        )

    def run(self, state: dict[str, Any]) -> dict[str, Any]:
        """LangGraph节点入口：接收state，返回分析结果写入state"""
        ticker = state["ticker"]
        analysis = self.analyze(ticker)
        return {
            "analyses": [{
                "agent": "fundamental",
                "ticker": ticker,
                "score": analysis.score,
                "signal": analysis.signal,
                "reasoning": analysis.reasoning,
                "data": {
                    "pe_ratio": analysis.pe_ratio,
                    "pb_ratio": analysis.pb_ratio,
                    "roe": analysis.roe,
                    "revenue_growth": analysis.revenue_growth,
                    "profit_margin": analysis.profit_margin,
                },
            }]
        }
