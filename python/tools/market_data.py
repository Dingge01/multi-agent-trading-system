"""
市场数据工具 - yfinance封装层

统一的数据获取接口，所有Agent通过此模块获取市场数据，避免重复请求和数据不一致。

面试要点：
- 为什么要封装而不是直接调yfinance？统一缓存、统一异常处理、便于替换数据源
- 缓存策略：同一次决策流程中，同一股票的数据只拉取一次
"""
from __future__ import annotations

from datetime import datetime, timedelta
from functools import lru_cache
from typing import Any

import yfinance as yf
import pandas as pd


class MarketDataProvider:
    """
    市场数据提供者 - 单次分析session内缓存数据

    生产环境中会替换为 TimescaleDB / InfluxDB 时序数据库连接。
    """

    def __init__(self):
        self._cache: dict[str, Any] = {}

    def get_stock_info(self, ticker: str) -> dict[str, Any]:
        cache_key = f"info_{ticker}"
        if cache_key not in self._cache:
            stock = yf.Ticker(ticker)
            self._cache[cache_key] = stock.info
        return self._cache[cache_key]

    def get_history(self, ticker: str, period: str = "1y",
                    interval: str = "1d") -> pd.DataFrame:
        cache_key = f"hist_{ticker}_{period}_{interval}"
        if cache_key not in self._cache:
            stock = yf.Ticker(ticker)
            self._cache[cache_key] = stock.history(period=period, interval=interval)
        return self._cache[cache_key]

    def get_financials(self, ticker: str) -> dict[str, pd.DataFrame]:
        cache_key = f"fin_{ticker}"
        if cache_key not in self._cache:
            stock = yf.Ticker(ticker)
            self._cache[cache_key] = {
                "income_stmt": stock.income_stmt,
                "balance_sheet": stock.balance_sheet,
                "cashflow": stock.cashflow,
            }
        return self._cache[cache_key]

    def get_current_price(self, ticker: str) -> float:
        info = self.get_stock_info(ticker)
        return info.get("currentPrice", info.get("regularMarketPrice", 0))

    def get_market_cap(self, ticker: str) -> float:
        return self.get_stock_info(ticker).get("marketCap", 0)

    def get_news(self, ticker: str) -> list[dict]:
        cache_key = f"news_{ticker}"
        if cache_key not in self._cache:
            stock = yf.Ticker(ticker)
            self._cache[cache_key] = stock.news or []
        return self._cache[cache_key]

    def clear_cache(self):
        self._cache.clear()


_provider = MarketDataProvider()


def get_provider() -> MarketDataProvider:
    return _provider
