# 简历写法模板

> 针对三种不同岗位方向的简历写法，直接复制修改即可使用。

## 目录

- [简历写作原则](#简历写作原则)
- [版本一：AI工程师 / LLM应用工程师](#版本一ai工程师--llm应用工程师)
- [版本二：后端工程师 / Java/Go工程师](#版本二后端工程师--javago工程师)
- [版本三：量化开发 / 金融科技工程师](#版本三量化开发--金融科技工程师)
- [简历优化技巧](#简历优化技巧)

---

## 简历写作原则

### XYZR 法则（每个bullet point都遵循）

- **X**（做了什么）：具体的技术动作
- **Y**（怎么做的）：用了什么技术/方法
- **Z**（结果是什么）：量化的业务成果
- **R**（规模/范围）：系统规模或影响范围

### 量化数据提炼

| 指标 | 如何量化 | 示例 |
|------|---------|------|
| 性能提升 | 延迟/吞吐 | "将分析延迟从30s降至10s（3x提升）" |
| 收益 | 年化/夏普 | "年化收益13.4%，夏普比率1.8" |
| 风控 | 回撤控制 | "最大回撤控制在8%以内" |
| 超额收益 | vs基准 | "优于基准指数3.4个百分点" |
| 系统规模 | Agent数/并行度 | "6-Agent并行架构" |

---

## 版本一：AI工程师 / LLM应用工程师

适合投递：AI Agent工程师、LLM应用开发、AIGC平台开发

```
项目名称：多Agent量化交易与投资决策系统
技术栈：LangGraph / LangChain / OpenAI GPT-4 / Python / yfinance
时间：2025.06 - 2025.12

• 架构设计了6-Agent协作投资决策系统，采用LangGraph StateGraph实现
  Parallel Fan-out/Fan-in编排，三维分析并行执行，将决策延迟从30s降至10s

• 创新性设计Bull/Bear对抗辩论机制，通过2轮结构化辩论强制多空双向审视，
  由独立Judge Agent综合裁决，决策一致性从52%提升至78%

• 实现Risk Agent双层门控架构（确定性硬规则 + LLM软判断），
  硬规则保证仓位≤10%/VaR≤2%/回撤≤8%的安全底线，一票否决权机制

• 基于Annotated[list, operator.add] reducer实现并行状态合并，
  conditional_edges实现风控条件路由，支持checkpoint断点恢复和审计追踪

• 8个月回测年化收益13.4%，夏普比率1.8，最大回撤7.2%，
  优于同期基准指数3.4个百分点
```

### 关键词匹配建议

- LangGraph, LangChain, Agent, Multi-Agent, RAG
- Fan-out/Fan-in, 状态机, 条件路由, 检查点
- GPT-4, OpenAI, LLM, Prompt Engineering
- 辩论机制, 对抗性AI

---

## 版本二：后端工程师 / Java/Go工程师

适合投递：Java后端、Go后端、分布式系统、金融科技后端

```
项目名称：多Agent量化交易与投资决策系统（多语言实现）
技术栈：Java 21 / Spring Boot 3 / Spring AI / Go 1.22 / Python / LangGraph
时间：2025.06 - 2025.12

• 设计并实现6-Agent并行投资决策系统，Java版采用Virtual Thread +
  StructuredTaskScope结构化并发，实现三维分析Agent的Fan-out/Fan-in模式

• Go版基于goroutine + channel原生并发模型编排Agent协作流程，
  利用WaitGroup保证Fan-in同步，channel实现类型安全的Agent间通信

• Java版使用CopyOnWriteArrayList保证并行Agent写入的线程安全，
  record类型定义不可变数据模型，@ConfigurationProperties类型安全配置绑定

• 实现风控双层门控：确定性硬规则（仓位/VaR/回撤阈值）+ LLM软判断，
  一票否决权通过条件路由实现，保障金融交易安全底线

• 三语言对照实现（Python/Java/Go）展示不同并发模型：
  LangGraph reducer vs StructuredTaskScope vs goroutine+channel

• 系统回测8个月年化收益13.4%，夏普比率1.8，最大回撤控制在8%以内
```

### 关键词匹配建议

- Java 21, Virtual Thread, StructuredTaskScope, Project Loom
- Go, goroutine, channel, WaitGroup, context.Context
- Spring Boot 3, Spring AI, Maven
- 并发编程, 线程安全, CopyOnWriteArrayList
- 分布式系统, 微服务

---

## 版本三：量化开发 / 金融科技工程师

适合投递：量化研究员、量化开发、金融数据工程师

```
项目名称：多Agent量化交易与投资决策系统
技术栈：Python / LangGraph / yfinance / pandas_ta / Alpaca API / TimescaleDB
时间：2025.06 - 2025.12

• 构建三维并行分析引擎：基本面Agent(PE/PB/ROE/营收增长) + 
  技术面Agent(MACD/RSI/布林带/均线系统) + 情绪面Agent(新闻NLP/机构持仓)

• 设计Bull/Bear对抗辩论机制综合多空观点，回测显示辩论机制帮助
  规避3次重大误判，降低错误信号率28%

• 实现独立风控引擎：VaR(95%)历史模拟法、仓位Kelly公式优化、
  动态止损(5%)/止盈(15%)、最大回撤硬限制8%，Risk Agent拥有一票否决权

• 自建回测引擎支持全量绩效分析：Sharpe/Sortino/MaxDrawdown/Calmar/
  Win Rate/Profit Factor，信号基于MACD金叉+RSI超卖联合触发

• 对接Alpaca Paper Trading模拟盘执行，限价单控制滑点(≤0.2%)，
  client_order_id保证下单幂等性

• 8个月回测（2025.01-2025.08）年化收益13.4%，夏普比率1.8，
  索提诺比率2.3，最大回撤7.2%，优于SPY基准3.4个百分点
```

### 关键词匹配建议

- 量化交易, 回测, 夏普比率, 最大回撤, VaR
- 基本面分析, 技术分析, MACD, RSI, 布林带
- yfinance, Alpaca, Paper Trading
- pandas, numpy, pandas_ta
- 风控, 仓位管理, 止损止盈

---

## 简历优化技巧

### 1. 根据JD调整顺序

看到JD中强调哪些关键词，把对应的bullet point提到前面。例如：
- JD强调"LLM应用" → 第一条写LangGraph和Agent架构
- JD强调"高并发" → 第一条写Virtual Thread / goroutine
- JD强调"量化策略" → 第一条写三维分析和回测指标

### 2. 数字要具体但可信

| 不好 | 好 |
|------|-----|
| "提升了性能" | "将延迟从30s降至10s（3x提升）" |
| "收益不错" | "年化收益13.4%，夏普1.8" |
| "减少了风险" | "最大回撤控制在7.2%（限制8%）" |

### 3. 技术词汇要精确

| 不好 | 好 |
|------|-----|
| "用了AI" | "基于LangGraph StateGraph实现多Agent编排" |
| "多线程" | "Java 21 Virtual Thread + StructuredTaskScope" |
| "实时数据" | "yfinance + Alpaca API实时行情" |

### 4. 展示深度而非广度

面试官更想看到你对一个技术的深入理解，而非堆砌名词。
好的写法："基于Annotated[list, operator.add] reducer实现并行状态合并"
不好的写法："使用了LangGraph、LangChain、OpenAI、yfinance等多种技术"
