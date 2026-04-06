"""
情绪分析工具

提供新闻情绪分析、恐贪指数估算等功能。

面试要点：
- TextBlob：基于规则的NLP情绪分析，polarity范围[-1, 1]
- 恐贪指数：综合VIX、市场动量、安全资产需求等因子的简化版
- 生产环境会接入专业NLP模型（FinBERT等）做金融文本情绪分析
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import yfinance as yf
from textblob import TextBlob


@dataclass
class NewsSentimentResult:
    avg_polarity: float
    avg_subjectivity: float
    positive_count: int
    negative_count: int
    neutral_count: int
    total_count: int
    headlines: list[str]


def analyze_news_sentiment(ticker: str, max_articles: int = 20) -> NewsSentimentResult:
    """分析股票相关新闻的情绪"""
    stock = yf.Ticker(ticker)
    news = stock.news or []
    news = news[:max_articles]

    polarities = []
    subjectivities = []
    positive = negative = neutral = 0
    headlines = []

    for item in news:
        title = item.get("title", "")
        if not title:
            continue

        headlines.append(title)
        blob = TextBlob(title)
        pol = blob.sentiment.polarity
        sub = blob.sentiment.subjectivity
        polarities.append(pol)
        subjectivities.append(sub)

        if pol > 0.1:
            positive += 1
        elif pol < -0.1:
            negative += 1
        else:
            neutral += 1

    return NewsSentimentResult(
        avg_polarity=np.mean(polarities) if polarities else 0.0,
        avg_subjectivity=np.mean(subjectivities) if subjectivities else 0.0,
        positive_count=positive,
        negative_count=negative,
        neutral_count=neutral,
        total_count=len(headlines),
        headlines=headlines,
    )


def estimate_fear_greed_index(ticker: str = "^GSPC") -> dict[str, float]:
    """
    简化版恐贪指数 (0=极度恐惧, 100=极度贪婪)

    因子：
    1. 市场动量：S&P500 vs 125日均线
    2. 波动率：VIX水平
    3. 安全资产需求：债券 vs 股票表现
    """
    sp500 = yf.Ticker(ticker)
    sp_hist = sp500.history(period="6mo")
    if sp_hist.empty:
        return {"index": 50, "label": "Neutral"}

    current = sp_hist["Close"].iloc[-1]
    sma_125 = sp_hist["Close"].rolling(125).mean().iloc[-1]
    momentum_score = min(max((current / sma_125 - 0.95) / 0.10 * 100, 0), 100)

    try:
        vix = yf.Ticker("^VIX")
        vix_hist = vix.history(period="1d")
        vix_val = vix_hist["Close"].iloc[-1] if not vix_hist.empty else 20
    except Exception:
        vix_val = 20

    if vix_val < 12:
        vix_score = 90
    elif vix_val < 20:
        vix_score = 60
    elif vix_val < 30:
        vix_score = 30
    else:
        vix_score = 10

    index = (momentum_score * 0.5 + vix_score * 0.5)

    if index >= 80:
        label = "Extreme Greed"
    elif index >= 60:
        label = "Greed"
    elif index >= 40:
        label = "Neutral"
    elif index >= 20:
        label = "Fear"
    else:
        label = "Extreme Fear"

    return {"index": round(index, 1), "label": label}
