# Python 实现 - 多Agent量化交易系统

## 技术栈

- **LangGraph** - Agent编排（Fan-out/Fan-in + 条件路由）
- **LangChain** + **OpenAI GPT-4** - LLM调用
- **yfinance** - 免费市场数据
- **pandas_ta** - 技术指标计算
- **TextBlob** - 新闻情绪NLP分析

## 快速开始

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 配置环境变量
cp ../.env.example ../.env
# 编辑 ../.env，填入 OPENAI_API_KEY

# 3. 运行完整决策流程
python -m graph.trading_graph

# 4. 运行回测
python -m backtest.backtester
```

## 核心代码导读

### 1. LangGraph 编排 (`graph/trading_graph.py`)

这是整个系统的核心。关键代码段：

```python
# 全局状态：Annotated[list, operator.add] 是并行合并的关键
class TradingState(TypedDict):
    ticker: str
    analyses: Annotated[list[dict], operator.add]  # reducer!
    debate_result: dict
    risk_assessment: dict
    execution_result: dict

# 并行Fan-out：三个节点从同一起点出发
graph.set_entry_point("fundamental")
graph.add_edge("__start__", "technical")
graph.add_edge("__start__", "sentiment")

# 条件路由：风控Agent决定走向
graph.add_conditional_edges("risk", should_execute,
    {"execute": "execute", "reject": "reject"})
```

### 2. 辩论Agent (`agents/debate_agent.py`)

2轮辩论 + Judge裁决的完整实现。

### 3. 风控Agent (`agents/risk_agent.py`)

硬规则 + LLM 双层门控。

## 目录结构

```
python/
├── config/settings.py          # 集中配置
├── agents/
│   ├── fundamental_agent.py    # 基本面 (PE/PB/ROE)
│   ├── technical_agent.py      # 技术面 (MACD/RSI/布林带)
│   ├── sentiment_agent.py      # 情绪面 (新闻NLP/持仓)
│   ├── debate_agent.py         # 牛熊辩论
│   ├── risk_agent.py           # 风控守门
│   └── execution_agent.py      # 执行下单
├── graph/
│   └── trading_graph.py        # LangGraph编排（核心）
├── tools/
│   ├── market_data.py          # 数据层（带缓存）
│   ├── technical_indicators.py # 指标计算
│   └── sentiment_tools.py      # 情绪工具
├── backtest/
│   └── backtester.py           # 回测引擎
└── tests/
```
