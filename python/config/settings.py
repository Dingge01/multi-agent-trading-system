"""
全局配置：从环境变量加载所有配置项，集中管理。
"""
import os
from dataclasses import dataclass, field
from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class LLMConfig:
    api_key: str = os.getenv("API_KEY", "")
    base_url: str = os.getenv("LLM_BASE_URL", "")
    model: str = os.getenv("MODEL", "")
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


def parse_llm_json(content: str, default: dict | None = None) -> dict:
    """
    解析 LLM 返回的 JSON，自动处理 markdown 代码块包裹、多余文本等。
    Minimax / GPT 等模型常将 JSON 包裹在 ```json ... ``` 中。
    """
    import json
    import re

    text = content.strip() if hasattr(content, "strip") else str(content).strip()

    # 1. 尝试直接解析
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # 2. 提取 ```json ... ``` 或 ``` ... ``` 代码块
    code_block = re.search(r"```(?:json)?\s*(.*?)\s*```", text, re.DOTALL)
    if code_block:
        try:
            return json.loads(code_block.group(1))
        except json.JSONDecodeError:
            pass

    # 3. 提取最外层的大括号/方括号内容
    brace_match = re.search(r"(\{.*\})", text, re.DOTALL)
    if brace_match:
        try:
            return json.loads(brace_match.group(1))
        except json.JSONDecodeError:
            pass

    # 4. 全部失败，返回默认值
    return default if default is not None else {}


def get_yf_session():
    """创建带代理和重试的 requests.Session，供 yfinance 使用"""
    import requests
    from requests.adapters import HTTPAdapter
    from urllib3.util.retry import Retry

    # 同时修改 yfinance 内部使用的 headers，注入完整浏览器特征
    import yfinance as yf
    yf.data.YfData.user_agent_headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "Referer": "https://finance.yahoo.com/",
    }

    session = requests.Session()

    # 同步 session 默认 headers
    session.headers.update(yf.data.YfData.user_agent_headers)

    # 配置代理（Clash 默认端口 7897）
    proxy = os.getenv("HTTPS_PROXY") or os.getenv("HTTP_PROXY") or "http://127.0.0.1:7897"
    session.proxies = {"http": proxy, "https": proxy}

    # 配置自动重试：最多5次，指数退避，遇到429/5xx自动重试
    retry = Retry(
        total=3,
        backoff_factor=3,  # 重试间隔: 5s, 10s, 20s, 40s, 80s
        status_forcelist=[429, 500, 502, 503, 504],
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("https://", adapter)
    session.mount("http://", adapter)

    return session
