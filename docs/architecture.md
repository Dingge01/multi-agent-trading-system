# 架构设计详解

> 本文档详细讲解多Agent量化交易系统的架构设计，面向零基础读者，适合面试前深度理解。

## 目录

- [1. 系统全景图](#1-系统全景图)
- [2. 为什么需要多Agent架构](#2-为什么需要多agent架构)
- [3. 编排模式详解](#3-编排模式详解)
- [4. 六个Agent的职责与设计](#4-六个agent的职责与设计)
- [5. 数据流与状态管理](#5-数据流与状态管理)
- [6. 容错与异常处理](#6-容错与异常处理)
- [7. 生产环境扩展](#7-生产环境扩展)

---

## 1. 系统全景图

```
┌─────────────────────────────────────────────────────────────┐
│                    用户输入: 股票代码 (如 AAPL)                │
└─────────────────────────┬───────────────────────────────────┘
                          │
                ┌─────────▼─────────┐
                │   并行 Fan-out     │
                └──┬──────┬──────┬──┘
                   │      │      │
          ┌────────▼┐  ┌──▼───┐  ┌▼────────┐
          │基本面    │  │技术面│  │情绪面    │
          │Agent    │  │Agent │  │Agent    │
          │         │  │      │  │         │
          │• PE/PB  │  │• MACD│  │• 新闻   │
          │• ROE    │  │• RSI │  │• 持仓   │
          │• 营收   │  │• 布林│  │• 评级   │
          └────────┬┘  └──┬───┘  └┬────────┘
                   │      │      │
                ┌──▼──────▼──────▼──┐
                │   Fan-in 聚合      │
                │   (reducer合并)    │
                └─────────┬─────────┘
                          │
                ┌─────────▼─────────┐
                │   辩论 Agent       │
                │                   │
                │  Bull方 ←→ Bear方  │
                │  (2轮辩论)         │
                │  → Judge裁决       │
                └─────────┬─────────┘
                          │
                ┌─────────▼─────────┐
                │   风控 Agent       │
                │                   │
                │  硬规则检查 (确定性)│
                │  + LLM软判断      │
                │  → 一票否决权      │
                └────┬─────────┬────┘
                     │         │
              ┌──────▼──┐  ┌───▼──────┐
              │ 执行Agent│  │ 拒绝交易  │
              │ (下单)   │  │          │
              └─────────┘  └──────────┘
```

## 2. 为什么需要多Agent架构

### 单模型 vs 多Agent对比

| 维度 | 单一大模型 | 多Agent系统 |
|------|----------|------------|
| **专业性** | 一个模型做所有事，什么都不精 | 每个Agent专精一个领域 |
| **可解释性** | 黑盒决策，不知道为什么买 | 每个Agent输出明确理由 |
| **可靠性** | 一个模型挂了全挂 | 单个Agent失败不影响整体 |
| **可审计** | 无法追踪决策过程 | 每个步骤都有记录 |
| **可扩展** | 加功能=改prompt | 加功能=加Agent |

### 面试话术

> "我们选择多Agent架构而不是单一大模型，核心原因有三：第一，**专业化分工**——就像投资公司里基本面分析师和技术分析师是不同的人，我们的Agent也各有专长；第二，**可审计性**——金融系统必须能解释每个决策的依据，多Agent架构天然支持链路追踪；第三，**容错性**——情绪分析Agent失败不影响基本面和技术面的判断。"

## 3. 编排模式详解

### 3.1 并行 Fan-out（扇出）

**什么是Fan-out？**
一个入口同时触发多个并行任务。就像一个经理同时把任务分配给三个下属。

**为什么要并行？**
三个分析Agent互相独立，没有数据依赖。串行执行需要30秒（10秒×3），并行只需10秒。

**Python实现原理：**
```python
# LangGraph自动并行执行从同一起点出发的无依赖节点
graph.set_entry_point("fundamental")
graph.add_edge("__start__", "technical")   # 与fundamental并行
graph.add_edge("__start__", "sentiment")   # 与上面两个并行
```

**Java实现原理：**
```java
// Java 21 Virtual Thread + StructuredTaskScope
try (var scope = new StructuredTaskScope.ShutdownOnFailure()) {
    for (Agent agent : agents) {
        scope.fork(() -> { agent.process(state); return null; });
    }
    scope.join();  // 等所有Agent完成
}
```

**Go实现原理：**
```go
// goroutine + channel
for _, agent := range agents {
    go func(a Agent) {
        result, _ := a.Analyze(ctx, ticker)
        resultCh <- result  // 通过channel发送
    }(agent)
}
```

### 3.2 Fan-in（扇入/聚合）

**什么是Fan-in？**
多个并行任务的结果汇聚到一个点。就像三个分析师的报告交给一个人汇总。

**Python中的reducer机制：**
```python
class TradingState(TypedDict):
    # Annotated[list, operator.add] 是关键
    # 多个节点同时写入analyses时，结果自动append而非覆盖
    analyses: Annotated[list[dict], operator.add]
```

### 3.3 辩论机制（Debate）

**这是本系统最大创新点。**

辩论流程：
1. **Bull方**（看多）：基于分析数据，尽全力找买入理由
2. **Bear方**（看空）：基于分析数据，尽全力找卖出理由
3. **第二轮**：双方看到对方论点后，反驳并强化自己立场
4. **Judge**（裁判）：综合双方论点，做出最终裁决

**为什么需要辩论而不是简单投票？**
- 投票只看结论，不看推理过程
- 辩论强制从两个角度思考，避免"确认偏误"
- 如果三个Agent都说BUY，但Bear方找到了一个致命风险点，这是简单投票发现不了的

### 3.4 风控守门（Risk Gating）

**双层门控设计：**

| 层级 | 类型 | 可绕过？ | 例子 |
|------|------|---------|------|
| 硬规则 | 确定性代码 | 不可 | 单票仓位≤10%，VaR≤2% |
| 软规则 | LLM判断 | 可覆盖 | "市场波动异常，建议降低仓位" |

**为什么硬规则不能用LLM？**
> LLM可能被prompt注入攻击，也可能产生幻觉。如果风控的底线依赖LLM，一旦LLM"发疯"说"仓位100%没问题"，后果不堪设想。所以硬规则必须用确定性代码实现。

## 4. 六个Agent的职责与设计

### 4.1 Fundamental Agent（基本面）

| 项目 | 说明 |
|------|------|
| 输入 | 股票代码 |
| 数据源 | yfinance (免费) |
| 分析维度 | PE, PB, ROE, 营收增长, 利润率, 负债率, 自由现金流 |
| 输出 | 评分(1-10), 信号(BUY/SELL/HOLD), 推理 |
| LLM角色 | 综合多个财务指标给出人类可读的判断 |

### 4.2 Technical Agent（技术面）

| 项目 | 说明 |
|------|------|
| 输入 | 股票代码 |
| 数据源 | yfinance历史K线 |
| 分析维度 | MACD, RSI, 布林带, SMA(20/50), 成交量 |
| 输出 | 评分(1-10), 信号, 推理 |
| 关键逻辑 | MACD金叉+RSI超卖→强烈BUY信号 |

### 4.3 Sentiment Agent（情绪面）

| 项目 | 说明 |
|------|------|
| 输入 | 股票代码 |
| 数据源 | yfinance新闻, TextBlob NLP |
| 分析维度 | 新闻情绪极性, 机构持仓, 分析师评级 |
| 输出 | 评分(1-10), 信号, 推理 |
| 工具 | TextBlob: polarity ∈ [-1, +1] |

### 4.4 Debate Agent（辩论）

| 项目 | 说明 |
|------|------|
| 输入 | 三个Agent的分析结果 |
| 流程 | Bull陈述→Bear反驳→2轮交锋→Judge裁决 |
| 输出 | 最终信号, 置信度, 建议仓位, 推理 |
| 防死循环 | MAX_DEBATE_ROUNDS=2 硬限制 |

### 4.5 Risk Agent（风控）

| 项目 | 说明 |
|------|------|
| 输入 | 辩论结果 + 组合状态 |
| 硬规则 | 仓位≤10%, 回撤≤8%, VaR≤2% |
| 软规则 | LLM评估市场环境、流动性等 |
| 输出 | 通过/否决, 调整后仓位, 止损止盈价 |
| 特权 | **一票否决权** |

### 4.6 Execution Agent（执行）

| 项目 | 说明 |
|------|------|
| 前置条件 | Risk Agent 必须 approved=true |
| 模式 | Dry Run(模拟) / Alpaca Paper Trading |
| 下单类型 | 限价单（控制滑点） |
| 幂等性 | client_order_id 防重复下单 |

## 5. 数据流与状态管理

### 全局State流转

```
初始State:
  ticker="AAPL", analyses=[], debate_result={}, risk_assessment={}, execution_result={}

→ Fundamental Agent 写入:
  analyses=[{agent:"fundamental", score:7.5, signal:"BUY", ...}]

→ Technical Agent 写入 (并行，reducer自动合并):
  analyses=[{fundamental...}, {agent:"technical", score:6.0, signal:"HOLD", ...}]

→ Sentiment Agent 写入 (并行):
  analyses=[{fundamental...}, {technical...}, {agent:"sentiment", score:8.0, signal:"BUY", ...}]

→ Debate Agent 写入:
  debate_result={final_signal:"BUY", confidence:0.72, ...}

→ Risk Agent 写入:
  risk_assessment={approved:true, adjusted_position_pct:0.08, stop_loss:170.5, ...}

→ Execution Agent 写入:
  execution_result={status:"FILLED_DRY_RUN", side:"buy", quantity:47, ...}
```

## 6. 容错与异常处理

| 故障场景 | 处理策略 |
|---------|---------|
| LLM返回非JSON | 解析失败默认HOLD，不会崩溃 |
| yfinance数据为空 | 返回空指标，Agent评分默认5分 |
| 单个分析Agent超时 | 不影响其他Agent（并行独立） |
| 风控LLM"发疯" | 硬规则保底，LLM只做软判断 |
| 下单API失败 | 返回ERROR状态，不重试（避免重复下单） |

## 7. 生产环境扩展

从demo到生产需要考虑：

1. **数据持久化**：State写入TimescaleDB/PostgreSQL，便于审计
2. **可观测性**：LangSmith/Prometheus监控每个Agent的延迟和成功率
3. **异步执行**：Celery/Kafka解耦Agent，支持大规模并行
4. **AB测试**：不同LLM模型的Agent同时运行，比较效果
5. **人工介入**：大额交易增加human-in-the-loop审批步骤
