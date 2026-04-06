# Agent 设计模式详解

> 本文档讲解多Agent系统中常见的设计模式，配合代码示例，面试时能体现你的架构设计能力。

## 目录

- [1. 并行Fan-out/Fan-in模式](#1-并行fan-outfan-in模式)
- [2. 辩论模式（Debate Pattern）](#2-辩论模式debate-pattern)
- [3. 守门员模式（Gatekeeper Pattern）](#3-守门员模式gatekeeper-pattern)
- [4. 管道模式（Pipeline Pattern）](#4-管道模式pipeline-pattern)
- [5. 观察者模式在Agent中的应用](#5-观察者模式在agent中的应用)
- [6. 设计模式对比与选型](#6-设计模式对比与选型)

---

## 1. 并行Fan-out/Fan-in模式

### 适用场景
多个独立的分析任务，彼此没有数据依赖，可以同时执行。

### 关键设计决策

**Q: 如何保证并行写入的数据一致性？**

| 语言 | 方案 | 原理 |
|------|------|------|
| Python (LangGraph) | `Annotated[list, operator.add]` | reducer函数，框架保证原子合并 |
| Java | `CopyOnWriteArrayList` | 写时复制，读多写少场景最优 |
| Go | `channel` + 单一消费者 | channel本身保证线程安全 |

**Q: 如果一个Agent失败了怎么办？**

策略一：**降级继续**（本项目采用）
```python
# Agent失败时返回默认值，不影响其他Agent
try:
    result = json.loads(response.content)
except json.JSONDecodeError:
    result = {"score": 5.0, "signal": "HOLD", "reasoning": "解析失败"}
```

策略二：**全部取消** (适合强一致性场景)
```java
// Java: ShutdownOnFailure - 任一失败就取消所有
try (var scope = new StructuredTaskScope.ShutdownOnFailure()) { ... }
```

### 性能分析

```
串行执行: T = T_fundamental + T_technical + T_sentiment ≈ 10s + 10s + 10s = 30s
并行执行: T = max(T_fundamental, T_technical, T_sentiment) ≈ 10s
加速比: 3x
```

## 2. 辩论模式（Debate Pattern）

### 核心思想
强制从对立角度审视同一组数据，避免确认偏误（Confirmation Bias）。

### 流程设计

```
Round 1:
  Bull: "基于PE=15和营收增长20%，该股被低估" → arguments_bull_r1
  Bear: "但RSI>70已超买，且机构在减持"       → arguments_bear_r1

Round 2 (看到对方论点后):
  Bull: "超买只是短期现象，基本面支撑长期上涨" → arguments_bull_r2
  Bear: "高估值+减持=聪明钱在离场，下跌风险大" → arguments_bear_r2

Judge:
  综合所有论点 → "BUY，但建议小仓位(5%)，置信度65%"
```

### 防死循环设计

```python
MAX_DEBATE_ROUNDS = 2  # 硬限制辩论轮数

# 面试常问：为什么是2轮而不是更多？
# 答：实验发现2轮后论点开始重复，更多轮数只增加成本不增加信息量。
# 类似于辩论赛的正方一辩→反方一辩→正方二辩→反方二辩，共2轮交锋。
```

### 变体

| 变体 | 描述 | 适用场景 |
|------|------|---------|
| 双方辩论 | Bull vs Bear | 投资决策 |
| 红蓝对抗 | 攻击方 vs 防守方 | 安全审计 |
| 多方圆桌 | 3+个Agent讨论 | 复杂政策制定 |
| 层级辩论 | 初级分析→高级复核 | 分层决策 |

## 3. 守门员模式（Gatekeeper Pattern）

### 核心思想
关键决策节点设置独立的审批Agent，拥有一票否决权。

### 双层门控架构

```
                    ┌──────────────────┐
                    │   辩论结果        │
                    │   Signal: BUY    │
                    │   Position: 8%   │
                    └────────┬─────────┘
                             │
                    ┌────────▼─────────┐
                    │  第一层: 硬规则   │ ← 确定性代码，不可绕过
                    │  • 仓位 ≤ 10%    │
                    │  • VaR ≤ 2%      │
                    │  • 回撤 ≤ 8%     │
                    └────────┬─────────┘
                             │ 通过
                    ┌────────▼─────────┐
                    │  第二层: LLM判断  │ ← 处理边界case
                    │  • 市场环境评估   │
                    │  • 流动性检查     │
                    │  • 关联风险       │
                    └────┬────────┬────┘
                         │        │
                  ┌──────▼─┐  ┌───▼─────┐
                  │ 执行    │  │ 否决    │
                  └────────┘  └─────────┘
```

### 为什么硬规则在前？

```python
# 硬规则检查：O(1)时间，零成本
def _check_hard_rules(self, ticker, proposed_position, portfolio_drawdown):
    violations = []
    if proposed_position > self.risk_config.max_position_size:
        violations.append("仓位超限")
    # ... 更多规则
    return violations

# 如果硬规则就否决了，就不需要调LLM（省钱省时间）
if hard_violations:
    return RiskAssessment(approved=False, ...)

# 只有硬规则通过了，才需要LLM做进一步判断
llm_result = self.llm.invoke(...)
```

## 4. 管道模式（Pipeline Pattern）

### 本系统的混合管道

```
并行阶段:        [F] [T] [S]    ← Fan-out
                  ↓   ↓   ↓
聚合点:           [Debate]       ← Fan-in + 处理
                     ↓
串行阶段:         [Risk]         ← 守门员
                     ↓
条件分支:      [Execute/Reject]  ← 条件路由
```

这实际上是**混合编排模式**：并行 + 串行 + 条件路由的组合。

## 5. 观察者模式在Agent中的应用

### Agent间事件通知（扩展设计）

```python
# 生产环境中，可以用事件驱动解耦Agent
class AgentEventBus:
    """Agent间的事件总线，用于异步通知"""
    
    def __init__(self):
        self._subscribers = defaultdict(list)
    
    def subscribe(self, event_type, handler):
        self._subscribers[event_type].append(handler)
    
    def publish(self, event_type, data):
        for handler in self._subscribers[event_type]:
            handler(data)

# 使用示例
bus = AgentEventBus()
bus.subscribe("analysis_complete", debate_agent.on_analysis_ready)
bus.subscribe("risk_rejected", alert_manager.on_risk_event)
```

## 6. 设计模式对比与选型

| 模式 | 优势 | 劣势 | 适用场景 |
|------|------|------|---------|
| 并行Fan-out | 速度快，独立性好 | 无法处理依赖关系 | 多维度独立分析 |
| 辩论 | 避免偏见，决策质量高 | LLM成本高 | 重大投资决策 |
| 守门员 | 安全可靠 | 可能过于保守 | 金融风控 |
| 管道 | 清晰线性 | 不灵活 | 固定流程 |
| 层级(Hierarchical) | 管理复杂度 | 可能瓶颈 | 大团队协作 |

### 面试回答模板

> "我们选择了**并行+辩论+风控守门的混合编排模式**。并行Fan-out让三个分析Agent同时工作，将延迟从30秒降到10秒。辩论机制通过Bull/Bear对抗避免了确认偏误。风控Agent作为守门员，用硬规则+LLM双层门控，确保即使前面的Agent全部'看多'，也不会因为忽视风险而酿成大亏。"
