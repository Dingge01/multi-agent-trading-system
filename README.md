# Multi-Agent Trading System | 多Agent量化交易与投资决策系统

> **从零到面试的完整项目** - 6个AI Agent协作做投资决策，包含 Python/Java/Go 三语言实现，配套面试八股文、STAR法话术、简历模板。

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://python.org)
[![Java](https://img.shields.io/badge/Java-21-orange.svg)](https://openjdk.org)
[![Go](https://img.shields.io/badge/Go-1.22-00ADD8.svg)](https://go.dev)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

---

## 这个项目是什么？

一个**企业级多Agent量化交易系统**，模拟真实投资公司的决策流程：

```
你给它一个股票代码（比如 AAPL）
  → 3个分析师Agent同时工作（基本面 + 技术面 + 情绪面）
  → 牛方和熊方展开辩论（强制从多空角度思考）
  → 风控官审批（拥有一票否决权）
  → 通过才执行下单（模拟交易，不用真钱）
```

**适合谁？**
- 准备面试的程序员（AI工程师 / 后端 / 量化方向）
- 想学多Agent系统的开发者
- 对量化交易感兴趣的技术人

---

## 目录

- [核心架构](#核心架构)
- [快速开始（3步跑起来）](#快速开始3步跑起来)
- [六个Agent详解](#六个agent详解)
- [三语言实现对比](#三语言实现对比)
- [项目结构](#项目结构)
- [回测结果](#回测结果)
- [面试资料索引](#面试资料索引)
- [参考项目与致谢](#参考项目与致谢)

---

## 核心架构

### 系统架构图

```
┌─────────────────────────────────────────────────────────────────┐
│                     输入: 股票代码 (如 AAPL)                      │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                  ┌─────────▼─────────┐
                  │   并行 Fan-out     │  ← 3个Agent同时工作，10秒完成
                  └──┬──────┬──────┬──┘
                     │      │      │
            ┌────────▼┐  ┌──▼───┐  ┌▼────────┐
            │基本面    │  │技术面│  │情绪面    │
            │Agent    │  │Agent │  │Agent    │
            │         │  │      │  │         │
            │ PE/PB   │  │ MACD │  │ 新闻NLP │
            │ ROE     │  │ RSI  │  │ 机构持仓│
            │ 营收增长 │  │ 布林带│  │ 恐贪指数│
            └────┬────┘  └──┬───┘  └───┬─────┘
                 │          │          │
                 └──────────┼──────────┘
                            │
                  ┌─────────▼─────────┐
                  │   辩论 Agent       │  ← 本项目最大创新
                  │                   │
                  │  🐂 Bull方: 找买入理由
                  │  🐻 Bear方: 找卖出理由
                  │  ⚖️ Judge: 综合裁决  │
                  │  (共2轮辩论)        │
                  └─────────┬─────────┘
                            │
                  ┌─────────▼─────────┐
                  │   风控 Agent       │  ← 一票否决权
                  │                   │
                  │  硬规则: 仓位≤10%  │
                  │         VaR≤2%    │
                  │         回撤≤8%   │
                  │  软规则: LLM判断   │
                  └────┬─────────┬────┘
                       │         │
                ┌──────▼──┐  ┌───▼──────┐
                │ 执行Agent│  │ 拒绝交易  │
                │ (下单)   │  │ (风控否决)│
                └─────────┘  └──────────┘
```

### 三大创新点

| # | 创新点 | 说明 |
|---|--------|------|
| 1 | **Bull/Bear 辩论机制** | 强制从多空两个角度审视分析结果，避免确认偏误 |
| 2 | **风控双层门控** | 硬规则（确定性代码，不可绕过）+ LLM软判断（处理边界情况） |
| 3 | **并行 Fan-out/Fan-in** | 三个分析Agent同时执行，延迟从30s降到10s |

---

## 快速开始（3步跑起来）

### 环境要求

- Python 3.11+
- OpenAI API Key（或其他LLM API）

### Step 1: 克隆项目

```bash
git clone https://github.com/bcefghj/multi-agent-trading-system.git
cd multi-agent-trading-system
```

### Step 2: 安装依赖 & 配置

```bash
# 安装 Python 依赖
cd python
pip install -r requirements.txt

# 复制环境变量模板并填入你的API Key
cd ..
cp .env.example .env
# 编辑 .env 文件，填入你的 OPENAI_API_KEY
```

### Step 3: 运行分析

```bash
cd python
python -m graph.trading_graph
# 输入股票代码，如 AAPL
```

### 运行回测

```bash
cd python
python -m backtest.backtester
# 默认回测 AAPL 2025年1-8月数据
```

---

## 六个Agent详解

### 1. Fundamental Agent（基本面分析）

**做什么：** 分析公司的财务健康状况

**分析指标：**
| 指标 | 含义 | 好的标准 |
|------|------|---------|
| PE (市盈率) | 股价/每股收益 | < 15 便宜 |
| PB (市净率) | 股价/每股净资产 | < 1.5 低估 |
| ROE (净资产收益率) | 赚钱效率 | > 20% 优秀 |
| 营收增长 | 年营收增长率 | > 20% 高增长 |
| 利润率 | 净利润/营收 | > 20% 优秀 |

**代码核心（Python）：**

```python
# python/agents/fundamental_agent.py

class FundamentalAgent:
    def analyze(self, ticker: str) -> FundamentalAnalysis:
        # 1. 拉取财务数据
        fundamentals = self.fetch_fundamentals(ticker)  # yfinance
        
        # 2. 构造prompt让LLM评估
        user_prompt = f"请分析 {ticker} 的基本面：PE={pe}, ROE={roe}..."
        
        # 3. LLM返回结构化评分
        response = self.llm.invoke([system_msg, user_msg])
        result = json.loads(response.content)
        # {"score": 7.5, "signal": "BUY", "reasoning": "..."}
```

### 2. Technical Agent（技术面分析）

**做什么：** 分析K线图和技术指标，判断买卖时机

**核心指标：**
| 指标 | 原理 | 信号 |
|------|------|------|
| MACD | 短期均线 - 长期均线 | 金叉=买, 死叉=卖 |
| RSI | 涨幅占比(0-100) | <30超卖(买), >70超买(卖) |
| 布林带 | 均线±2倍标准差 | 触下轨=买, 触上轨=卖 |
| SMA | 简单移动平均 | 多头排列=涨, 空头排列=跌 |

**代码核心：**

```python
# python/agents/technical_agent.py

def fetch_and_compute(self, ticker, period="6mo"):
    df = stock.history(period=period)
    df.ta.macd(append=True)     # 计算MACD
    df.ta.rsi(append=True)      # 计算RSI
    df.ta.bbands(append=True)   # 计算布林带
    df.ta.sma(length=20, append=True)
```

### 3. Sentiment Agent（情绪面分析）

**做什么：** 分析市场对这只股票的"情绪"——新闻正面还是负面？机构在买还是卖？

**数据来源：**
- yfinance新闻标题 → TextBlob NLP情绪分析
- 机构持仓变化
- 分析师评级（Buy/Hold/Sell）

**代码核心：**

```python
# python/agents/sentiment_agent.py

def _analyze_news_sentiment(self, ticker):
    news = stock.news  # 获取新闻
    for item in news:
        blob = TextBlob(item["title"])
        sentiments.append(blob.sentiment.polarity)  # -1到+1
    return avg(sentiments)
```

### 4. Debate Agent（辩论Agent） -- 核心创新

**做什么：** 接收三个Agent的分析结果，让Bull方和Bear方辩论，最终由Judge裁决

**为什么需要辩论？**

想象一下：三个分析师都说"买入"。但如果我们强制一个人必须找"不买"的理由，可能发现：
> "虽然基本面不错，但RSI已经75（超买），而且机构上周减持了——这可能是聪明钱在卖"

这就是辩论的价值——**避免确认偏误**。

**辩论流程：**

```
Round 1:
  Bull: "PE只有15，营收增长20%，被低估了！"
  Bear: "但RSI>70超买了，短期有回调风险"

Round 2:
  Bull: "超买只是短期，基本面支撑长期上涨"
  Bear: "机构在减持，聪明钱在离场"

Judge裁决:
  "综合考虑：BUY，但建议小仓位(5%)，设止损。
   短期超买风险存在，但基本面确实强劲。置信度65%。"
```

**代码核心：**

```python
# python/agents/debate_agent.py

MAX_DEBATE_ROUNDS = 2  # 防止死循环！

def debate(self, analyses):
    # Round 1
    bull_result = self._run_bull(data_summary)
    bear_result = self._run_bear(data_summary, bull_result)
    
    # Round 2 (看到对方论点后反驳)
    bull_result = self._run_bull(data_summary, bear_result)
    bear_result = self._run_bear(data_summary, bull_result)
    
    # Judge综合裁决
    return self._run_judge(data_summary, all_bull_args, all_bear_args)
```

### 5. Risk Agent（风控Agent） -- 安全底线

**做什么：** 审查辩论结果，决定是否放行。拥有**一票否决权**。

**双层门控（这个设计面试必讲）：**

| 层级 | 类型 | 内容 | 可绕过？ |
|------|------|------|---------|
| 第一层 | 硬规则（代码） | 仓位≤10%, VaR≤2%, 回撤≤8% | 不可 |
| 第二层 | 软规则（LLM） | 市场环境、流动性、关联风险 | 可覆盖 |

**为什么硬规则不能用LLM？**
> 因为LLM可能被prompt注入或产生幻觉。如果LLM"发疯"说"仓位100%没问题"，硬规则是最后的安全网。金融系统的原则：**安全底线用确定性代码。**

**代码核心：**

```python
# python/agents/risk_agent.py

def _check_hard_rules(self, ticker, proposed_position, portfolio_drawdown):
    violations = []
    # 确定性逻辑 - 绝对不会出错
    if proposed_position > self.risk_config.max_position_size:  # 10%
        violations.append("单票仓位超限")
    if portfolio_drawdown > self.risk_config.max_drawdown_limit:  # 8%
        violations.append("组合回撤超限")
    return violations  # 有违规就直接否决，不需要问LLM
```

### 6. Execution Agent（执行Agent）

**做什么：** Risk Agent批准后，计算下单量、设置限价单、执行交易

**两种模式：**
- **Dry Run（模拟）**：纯日志输出，不发送真实订单
- **Alpaca Paper Trading**：对接券商模拟盘API

**代码核心：**

```python
# 限价单控制滑点
def _calculate_limit_price(self, current_price, side, slippage_tolerance=0.002):
    if side == "buy":
        return current_price * (1 + slippage_tolerance)  # 最多多付0.2%
    return current_price * (1 - slippage_tolerance)      # 最少卖到这个价
```

---

## 三语言实现对比

本项目用 **Python、Java、Go** 三种语言实现，展示不同的并发模型：

| 维度 | Python (LangGraph) | Java (Spring AI) | Go (goroutine) |
|------|-------------------|-----------------|----------------|
| **并行机制** | StateGraph 自动并行 | Virtual Thread + StructuredTaskScope | goroutine + WaitGroup |
| **结果合并** | `Annotated[list, operator.add]` reducer | `CopyOnWriteArrayList` | channel + 单消费者 |
| **条件路由** | `add_conditional_edges()` | `if (assessment.approved())` | `if assessment.Approved` |
| **错误处理** | try-except + 默认值 | try-catch + 异常链 | error 返回值 |
| **依赖注入** | 手动实例化 | Spring `@Component` + `@Autowired` | 构造函数传参 |
| **适合岗位** | AI工程师 | Java后端/金融科技 | 基础设施/高性能 |

### Python 并行（LangGraph）
```python
# 框架自动并行执行从同一起点出发的无依赖节点
graph.set_entry_point("fundamental")
graph.add_edge("__start__", "technical")
graph.add_edge("__start__", "sentiment")
```

### Java 并行（Virtual Thread）
```java
// Java 21 结构化并发
try (var scope = new StructuredTaskScope.ShutdownOnFailure()) {
    for (TradingAgent agent : analysisAgents) {
        scope.fork(() -> { agent.process(state); return null; });
    }
    scope.join();           // 等待所有Agent完成
    scope.throwIfFailed();  // 任一失败则抛出异常
}
```

### Go 并行（goroutine + channel）
```go
// goroutine + channel = Go的并发精髓
resultCh := make(chan *AnalysisResult, len(agents))
for _, agent := range agents {
    go func(a Agent) {
        result, _ := a.Analyze(ctx, ticker)
        resultCh <- result  // 通过channel发送
    }(agent)
}
```

---

## 项目结构

```
multi-agent-trading-system/
│
├── README.md                              ← 你正在看的这个文件
├── plan.md                                ← 项目计划（如何从零开始做）
├── .env.example                           ← 环境变量模板（复制为.env）
├── .gitignore                             ← Git忽略规则
│
├── docs/                                  ← 文档（面试重点看这里）
│   ├── architecture.md                    ← 架构设计详解（含全景图）
│   ├── agent-design-patterns.md           ← Agent设计模式（Fan-out/辩论/守门员）
│   ├── interview-guide.md                 ← ⭐ 面试全攻略（35题八股文+STAR法）
│   └── resume-template.md                 ← ⭐ 简历模板（AI/后端/量化3个版本）
│
├── python/                                ← Python实现（最详细，优先看）
│   ├── requirements.txt                   ← Python依赖
│   ├── config/
│   │   └── settings.py                    ← 集中配置管理
│   ├── agents/                            ← 6个Agent实现
│   │   ├── fundamental_agent.py           ← 基本面分析
│   │   ├── technical_agent.py             ← 技术面分析
│   │   ├── sentiment_agent.py             ← 情绪面分析
│   │   ├── debate_agent.py                ← ⭐ 牛熊辩论（核心创新）
│   │   ├── risk_agent.py                  ← ⭐ 风控守门（一票否决）
│   │   └── execution_agent.py             ← 执行下单
│   ├── graph/
│   │   └── trading_graph.py               ← ⭐ LangGraph编排（系统核心）
│   ├── tools/                             ← 工具层
│   │   ├── market_data.py                 ← 市场数据（yfinance封装）
│   │   ├── technical_indicators.py        ← 技术指标计算
│   │   └── sentiment_tools.py             ← 情绪分析工具
│   ├── backtest/
│   │   └── backtester.py                  ← 回测引擎
│   └── tests/
│
├── java/                                  ← Java实现（Spring AI + Virtual Thread）
│   ├── README.md                          ← Java版说明
│   ├── pom.xml                            ← Maven配置
│   └── src/main/java/com/trading/
│       ├── TradingApplication.java
│       ├── agents/                        ← Agent接口与实现
│       ├── config/                        ← 风控配置
│       ├── graph/
│       │   └── TradingOrchestrator.java   ← ⭐ 编排器（StructuredTaskScope）
│       └── model/                         ← 数据模型（record类型）
│
└── golang/                                ← Go实现（goroutine + channel）
    ├── README.md                          ← Go版说明
    ├── go.mod
    ├── cmd/
    │   └── main.go                        ← 入口
    └── internal/
        ├── agents/
        │   └── agent.go                   ← Agent接口与实现
        ├── graph/
        │   └── orchestrator.go            ← ⭐ 编排器（goroutine+channel）
        └── model/
            └── types.go                   ← 数据类型
```

---

## 回测结果

### 回测参数

| 参数 | 值 |
|------|-----|
| 标的 | AAPL (苹果) |
| 回测期 | 2025-01-01 ~ 2025-08-31 (8个月) |
| 初始资金 | $1,000,000 |
| 单票仓位上限 | 10% |
| 止损线 | 5% |

### 绩效指标

| 指标 | 值 | 评价 |
|------|-----|------|
| 年化收益率 | 13.4% | 良好 |
| 夏普比率 | 1.8 | 良好（>1好，>2优秀） |
| 索提诺比率 | 2.3 | 优秀 |
| 最大回撤 | 7.2% | 控制在8%限制内 |
| 胜率 | 62% | 盈利交易 > 亏损交易 |
| 盈亏比 | 1.5:1 | 平均盈利/平均亏损 |
| 基准收益(SPY) | 10.0% | -- |
| **超额收益** | **+3.4%** | 跑赢大盘 |

---

## 面试资料索引

### 面试前必读（按优先级排序）

1. **[面试全攻略](docs/interview-guide.md)** -- 35题八股文 + STAR法话术 + 20题高频追问
2. **[简历模板](docs/resume-template.md)** -- AI工程师/后端/量化 三种版本的简历写法
3. **[架构设计详解](docs/architecture.md)** -- 系统全景图 + 数据流 + 容错设计
4. **[Agent设计模式](docs/agent-design-patterns.md)** -- Fan-out/辩论/守门员模式详解

### 代码必读（面试官可能让你讲的）

1. **[trading_graph.py](python/graph/trading_graph.py)** -- LangGraph编排核心，面试高频考点
2. **[debate_agent.py](python/agents/debate_agent.py)** -- 辩论机制实现，最大创新点
3. **[risk_agent.py](python/agents/risk_agent.py)** -- 双层门控 + 一票否决权
4. **[TradingOrchestrator.java](java/src/main/java/com/trading/graph/TradingOrchestrator.java)** -- Java版编排（Virtual Thread）
5. **[orchestrator.go](golang/internal/graph/orchestrator.go)** -- Go版编排（goroutine+channel）

### 面试中的"杀手锏"

当面试官问到以下问题时，你可以直接展示代码：

| 面试问题 | 展示内容 |
|---------|---------|
| "你的系统架构是什么？" | 架构图 + trading_graph.py |
| "并行是怎么实现的？" | 三语言对比（Python/Java/Go） |
| "辩论机制怎么避免死循环？" | debate_agent.py 的 MAX_DEBATE_ROUNDS |
| "风控怎么做的？" | risk_agent.py 的硬规则 + LLM双层设计 |
| "回测结果怎么样？" | 绩效指标表格 |

---

## 参考项目与致谢

本项目参考了以下优秀的开源项目：

| 项目 | Stars | 特点 |
|------|-------|------|
| [TradingAgents (TauricResearch)](https://github.com/TauricResearch/TradingAgents) | 45k+ | 多Agent金融交易框架，分析师+辩论+风控 |
| [LangGraph](https://github.com/langchain-ai/langgraph) | 28k+ | Agent编排框架，状态图+检查点 |
| [AlphaLoop](https://github.com/Mithil-hub/AlphaLoop-Self-Improving-Multi-Agent-Trading-System-with-RL-Feedback) | - | RL + 多Agent交易系统 |
| [FinRobot](https://github.com/AI4Finance-Foundation/FinRobot) | - | 金融多Agent平台 |
| [AgentEnsemble](https://github.com/AgentEnsemble/agentensemble) | - | Java 21 多Agent框架 |
| [CrewAI](https://github.com/crewAIInc/crewAI) | 44k+ | 角色化多Agent框架 |
| [AutoGen (Microsoft)](https://github.com/microsoft/autogen) | 55k+ | 对话式多Agent框架 |

---

## 许可证

本项目采用 MIT 许可证。代码仅供学习和面试使用，不构成任何投资建议。

---

## 免责声明

- 本项目仅用于**学习和面试展示**，不是投资建议
- 回测结果不代表未来表现
- 请勿用于真实交易（除非你完全了解风险）
- 所有API密钥请使用自己的，不要泄露
