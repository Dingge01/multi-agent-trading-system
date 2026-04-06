"""
全局配置：从环境变量加载所有配置项，集中管理。
"""
import os
from dataclasses import dataclass, field
from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class LLMConfig:
    provider: str = os.getenv("LLM_PROVIDER", "openai")
    api_key: str = os.getenv("OPENAI_API_KEY", "")
    model: str = os.getenv("OPENAI_MODEL", "gpt-4")
    temperature: float = float(os.getenv("LLM_TEMPERATURE", "0.3"))
    max_tokens: int = int(os.getenv("LLM_MAX_TOKENS", "2048"))


@dataclass(frozen=True)
class AlpacaConfig:
    api_key: str = os.getenv("ALPACA_API_KEY", "")
    secret_key: str = os.getenv("ALPACA_SECRET_KEY", "")
    base_url: str = os.getenv("ALPACA_BASE_URL", "https://paper-api.alpaca.markets")


@dataclass(frozen=True)
class RiskConfig:
    max_position_size: float = float(os.getenv("MAX_POSITION_SIZE", "0.1"))
    max_drawdown_limit: float = float(os.getenv("MAX_DRAWDOWN_LIMIT", "0.08"))
    stop_loss_pct: float = float(os.getenv("STOP_LOSS_PCT", "0.05"))
    take_profit_pct: float = float(os.getenv("TAKE_PROFIT_PCT", "0.15"))
    max_portfolio_risk: float = float(os.getenv("MAX_PORTFOLIO_RISK", "0.02"))


@dataclass(frozen=True)
class BacktestConfig:
    start_date: str = os.getenv("BACKTEST_START_DATE", "2025-01-01")
    end_date: str = os.getenv("BACKTEST_END_DATE", "2025-08-31")
    initial_capital: float = float(os.getenv("INITIAL_CAPITAL", "1000000"))


@dataclass(frozen=True)
class AppConfig:
    llm: LLMConfig = field(default_factory=LLMConfig)
    alpaca: AlpacaConfig = field(default_factory=AlpacaConfig)
    risk: RiskConfig = field(default_factory=RiskConfig)
    backtest: BacktestConfig = field(default_factory=BacktestConfig)
    news_api_key: str = os.getenv("NEWS_API_KEY", "")


CONFIG = AppConfig()
