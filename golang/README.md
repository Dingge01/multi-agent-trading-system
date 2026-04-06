# Go 实现 - 多Agent量化交易系统

## 技术栈

- **Go 1.22**
- **goroutine + channel** 原生并发
- **go-openai** LLM客户端
- **godotenv** 环境变量

## 核心亮点（面试必说）

### 1. goroutine + channel 实现 Fan-out/Fan-in

```go
// 每个Agent在独立goroutine中并行执行
resultCh := make(chan *model.AnalysisResult, len(agents))
var wg sync.WaitGroup

for _, agent := range agents {
    wg.Add(1)
    go func(a Agent) {
        defer wg.Done()
        result, _ := a.Analyze(ctx, ticker)
        resultCh <- result  // 通过channel发送结果
    }(agent)
}

// Fan-in: 从channel收集所有结果
go func() { wg.Wait(); close(resultCh) }()
for result := range resultCh {
    state.Analyses = append(state.Analyses, *result)
}
```

**为什么Go的并发模型适合多Agent？**
- goroutine 比 OS 线程轻量 1000 倍（初始栈仅 2KB）
- channel 提供类型安全的通信，无需显式加锁
- 天然适合 IO 密集的 LLM API 调用场景

### 2. 接口隐式实现（Duck Typing）

```go
// 只要实现了这两个方法，就自动满足 Agent 接口
type Agent interface {
    Name() string
    Analyze(ctx context.Context, ticker string) (*AnalysisResult, error)
}
// 无需 `implements` 关键字
```

### 3. context.Context 超时与取消

```go
// 可以为整个决策流程设置超时
ctx, cancel := context.WithTimeout(context.Background(), 60*time.Second)
defer cancel()
state, err := orchestrator.Execute(ctx, ticker, portfolioValue)
```

## 运行方式

```bash
export OPENAI_API_KEY=your-key
cd golang
go run cmd/main.go AAPL
```

## 与 Python/Java 对照

| 概念 | Python (LangGraph) | Java (Spring AI) | Go (goroutine) |
|------|-------------------|-----------------|----------------|
| 并行执行 | StateGraph | StructuredTaskScope | goroutine + WaitGroup |
| 结果收集 | reducer | CopyOnWriteArrayList | channel |
| 条件路由 | conditional_edges | if-else | if-else |
| 错误处理 | try-except | try-catch | error返回值 |
| 依赖注入 | 手动 | Spring DI | 构造函数 |
