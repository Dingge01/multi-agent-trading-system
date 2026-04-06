# Java 实现 - 多Agent量化交易系统

## 技术栈

- **Java 21** + Virtual Threads (Project Loom)
- **Spring Boot 3.3** + Spring AI
- **StructuredTaskScope** 结构化并发
- **Maven** 构建

## 核心亮点（面试必说）

### 1. Virtual Thread 并行 Fan-out

```java
// Java 21 结构化并发 - 对应 Python LangGraph 的并行节点
try (var scope = new StructuredTaskScope.ShutdownOnFailure()) {
    for (TradingAgent agent : analysisAgents) {
        scope.fork(() -> {
            agent.process(state);  // 每个Agent在独立的Virtual Thread中执行
            return null;
        });
    }
    scope.join();           // 等待所有Agent完成（Fan-in）
    scope.throwIfFailed();  // 任一失败则抛出异常
}
```

**为什么用Virtual Thread而不是线程池？**
- LLM API调用是IO密集型，Virtual Thread自动在阻塞时让出载体线程
- 无需调优线程池大小，系统自动管理
- 对比 `ExecutorService`：代码更简洁，且保证结构化（不会泄露线程）

### 2. CopyOnWriteArrayList 保证并发写入安全

```java
// TradingState中的analyses用CopyOnWriteArrayList
// 三个Agent并行写入时不会发生竞态条件
private final CopyOnWriteArrayList<AnalysisResult> analyses;
```

### 3. Record 类型替代 POJO

```java
// Java 21 record: 不可变、自带equals/hashCode/toString
public record AnalysisResult(
    String agent, String ticker, double score,
    String signal, String reasoning
) {}
```

## 运行方式

```bash
# 设置环境变量
export SPRING_AI_OPENAI_API_KEY=your-key

# 编译运行
mvn clean package
java -jar target/multi-agent-trading-1.0.0.jar

# 或直接
mvn spring-boot:run
```

## 目录结构

```
java/
├── pom.xml
└── src/main/java/com/trading/
    ├── TradingApplication.java      # 启动类
    ├── agents/
    │   ├── TradingAgent.java        # Agent接口
    │   └── FundamentalAgent.java    # 基本面Agent示例
    ├── config/
    │   └── TradingConfig.java       # 风控配置
    ├── graph/
    │   └── TradingOrchestrator.java # 编排器（核心）
    └── model/
        ├── AnalysisResult.java
        ├── DebateResult.java
        ├── RiskAssessment.java
        ├── ExecutionResult.java
        └── TradingState.java
```

## 与 Python 版对照

| 概念 | Python (LangGraph) | Java (Spring AI) |
|------|-------------------|-----------------|
| 并行执行 | `StateGraph` 自动并行 | `StructuredTaskScope` + Virtual Thread |
| 状态合并 | `Annotated[list, operator.add]` | `CopyOnWriteArrayList` |
| 条件路由 | `add_conditional_edges()` | `if (riskAssessment.approved())` |
| DI | 手动实例化 | Spring `@Component` 自动注入 |
| 配置 | `.env` + python-dotenv | `application.yml` + `@ConfigurationProperties` |
