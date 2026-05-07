"""
Sentiment Agent - 情绪面分析Agent

职责：新闻/社媒情绪分析、恐贪指数、机构持仓变化，输出市场情绪评分。

面试要点：
- 情绪分析的数据源：NewsAPI、yfinance新闻、社交媒体
- TextBlob做基础NLP情绪极性分析（-1到+1）
- 机构持仓变化反映"聪明钱"动向
- 恐贪指数：CNN Fear & Greed Index的简化实现
"""
from __future__ import annotations

import json
import time
from dataclasses import dataclass
from typing import Any

import yfinance as yf
from textblob import TextBlob
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage

from config.settings import CONFIG, get_yf_session, parse_llm_json


@dataclass
class SentimentAnalysis:
    ticker: str
    news_sentiment: float
    news_count: int
    institutional_holders_change: str
    analyst_recommendation: str
    score: float = 0.0
    signal: str = "HOLD"
    reasoning: str = ""


class SentimentAgent:
    """
    情绪面分析Agent：新闻情绪 + 机构持仓 + 分析师评级 → LLM综合 → 评分与信号

    架构角色：并行Fan-out的三个分析Agent之一，捕捉市场非理性因素。
    """

    SYSTEM_PROMPT = """你是一位市场情绪分析专家。你的任务是基于新闻情绪、机构持仓和分析师评级，评估市场对该股票的情绪状态。

评分标准 (1-10分):
- 新闻情绪: 极度正面(>0.5)(+2), 正面(0.1-0.5)(+1), 中性(-0.1-0.1)(0), 负面(<-0.1)(-1), 极度负面(<-0.5)(-2)
- 机构持仓: 增持(+2), 不变(0), 减持(-2)
- 分析师评级: 强烈买入(+2), 买入(+1), 持有(0), 卖出(-1), 强烈卖出(-2)
- 新闻数量: 高关注度(>20条)需警惕过热(±0), 低关注度(<5条)信息不足(-1)

请输出JSON格式:
{
    "score": <1-10的综合评分>,
    "signal": "<BUY/SELL/HOLD>",
    "reasoning": "<100字以内的情绪分析理由>"
}"""

    def __init__(self):
        kwargs = dict(
            model=CONFIG.llm.model,
            temperature=CONFIG.llm.temperature,
            api_key=CONFIG.llm.api_key,
        )
        if CONFIG.llm.base_url:
            kwargs["base_url"] = CONFIG.llm.base_url
        self.llm = ChatOpenAI(**kwargs)

    def _analyze_news_sentiment(self, ticker: str) -> tuple[float, int]:
        """用yfinance获取新闻，TextBlob计算情绪极性均值"""
        try:
            stock = yf.Ticker(ticker, session=get_yf_session())
            news = stock.news or []
        except Exception:
            return 0.0, 0

        if not news:
            return 0.0, 0

        sentiments = []
        for item in news[:20]:
            title = item.get("title", "")
            if title:
                blob = TextBlob(title)
                sentiments.append(blob.sentiment.polarity)

        avg_sentiment = sum(sentiments) / len(sentiments) if sentiments else 0.0
        return round(avg_sentiment, 4), len(sentiments)

    def _get_institutional_info(self, ticker: str) -> str:
        stock = yf.Ticker(ticker, session=get_yf_session())
        try:
            holders = stock.institutional_holders
            if holders is not None and not holders.empty:
                return "ACTIVE"
            return "UNKNOWN"
        except Exception:
            return "UNKNOWN"

    def _get_analyst_recommendation(self, ticker: str) -> str:
        stock = yf.Ticker(ticker, session=get_yf_session())
        try:
            rec = stock.recommendations
            if rec is not None and not rec.empty:
                latest = rec.iloc[-1]
                return str(latest.get("To Grade", "HOLD"))
            return "HOLD"
        except Exception:
            return "HOLD"

    def analyze(self, ticker: str) -> SentimentAnalysis:
        print(f"    └─ 获取新闻情绪数据...")
        news_sentiment, news_count = self._analyze_news_sentiment(ticker)
        print(f"       新闻情绪得分: {news_sentiment} (基于 {news_count} 条新闻)")

        print(f"    └─ 获取机构持仓信息...")
        institutional = self._get_institutional_info(ticker)
        print(f"       机构持仓状态: {institutional}")

        print(f"    └─ 获取分析师评级...")
        analyst_rec = self._get_analyst_recommendation(ticker)
        print(f"       分析师最新评级: {analyst_rec}")

        user_prompt = f"""请分析 {ticker} 的市场情绪：

- 新闻情绪得分: {news_sentiment} (范围: -1到+1)
- 新闻数量: {news_count} 条
- 机构持仓状态: {institutional}
- 分析师最新评级: {analyst_rec}"""

        print(f"    └─ 调用 LLM 进行情绪面研判...")
        response = self.llm.invoke([
            SystemMessage(content=self.SYSTEM_PROMPT),
            HumanMessage(content=user_prompt),
        ])
        print(f"    └─ LLM 原始返回:\n{response.content}")

        result = parse_llm_json(
            response.content,
            default={"score": 5.0, "signal": "HOLD", "reasoning": "LLM输出解析失败"}
        )

        return SentimentAnalysis(
            ticker=ticker,
            news_sentiment=news_sentiment,
            news_count=news_count,
            institutional_holders_change=institutional,
            analyst_recommendation=analyst_rec,
            score=result.get("score", 5.0),
            signal=result.get("signal", "HOLD"),
            reasoning=result.get("reasoning", ""),
        )

    def run(self, state: dict[str, Any]) -> dict[str, Any]:
        """LangGraph节点入口"""
        time.sleep(1)  # 延迟避免 yfinance 频率限制
        ticker = state["ticker"]
        print(f"\n{'─'*50}")
        print(f"  [Sentiment Agent] 开始分析 {ticker} 市场情绪...")
        analysis = self.analyze(ticker)
        print(f"  [Sentiment Agent] 完成 → 评分: {analysis.score}/10 | 信号: {analysis.signal}")
        print(f"    └─ 分析理由: {analysis.reasoning}")
        print(f"{'─'*50}")
        return {
            "analyses": [{
                "agent": "sentiment",
                "ticker": ticker,
                "score": analysis.score,
                "signal": analysis.signal,
                "reasoning": analysis.reasoning,
                "data": {
                    "news_sentiment": analysis.news_sentiment,
                    "news_count": analysis.news_count,
                    "analyst_recommendation": analysis.analyst_recommendation,
                },
            }]
        }
