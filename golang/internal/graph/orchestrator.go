package graph

import (
	"context"
	"fmt"
	"sync"

	"github.com/multi-agent-trading/golang/internal/agents"
	"github.com/multi-agent-trading/golang/internal/model"
)

/*
TradingOrchestrator - Go语言交易编排器

面试要点（重要！）：
  - goroutine + channel 实现 Fan-out/Fan-in，比 Python/Java 更轻量
  - sync.WaitGroup 确保所有并行Agent完成
  - channel 是 Go 的核心并发原语，类型安全、无需锁
  - 对比 Python LangGraph: Go 版更底层但性能更高
  - errgroup 可替代 WaitGroup 实现错误传播

架构：
  START → [goroutine: Fundamental + Technical + Sentiment] → channel Fan-in
  → Debate → Risk → Execute/Reject → END
*/
type TradingOrchestrator struct {
	AnalysisAgents []agents.Agent
	DebateAgent    *agents.BaseLLMAgent
	RiskConfig     RiskConfig
}

type RiskConfig struct {
	MaxPositionSize  float64
	MaxDrawdownLimit float64
	StopLossPct      float64
	MaxPortfolioRisk float64
}

func NewOrchestrator(analysisAgents []agents.Agent, debateAgent *agents.BaseLLMAgent, riskCfg RiskConfig) *TradingOrchestrator {
	return &TradingOrchestrator{
		AnalysisAgents: analysisAgents,
		DebateAgent:    debateAgent,
		RiskConfig:     riskCfg,
	}
}

// Execute 运行完整决策流程
func (o *TradingOrchestrator) Execute(ctx context.Context, ticker string, portfolioValue float64) (*model.TradingState, error) {
	state := &model.TradingState{
		Ticker:         ticker,
		PortfolioValue: portfolioValue,
	}

	// ===== Step 1: 并行 Fan-out =====
	// 每个Agent在独立的goroutine中执行，结果通过channel汇聚
	resultCh := make(chan *model.AnalysisResult, len(o.AnalysisAgents))
	errCh := make(chan error, len(o.AnalysisAgents))
	var wg sync.WaitGroup

	for _, agent := range o.AnalysisAgents {
		wg.Add(1)
		go func(a agents.Agent) {
			defer wg.Done()
			result, err := a.Analyze(ctx, ticker)
			if err != nil {
				errCh <- fmt.Errorf("[%s] %w", a.Name(), err)
				return
			}
			resultCh <- result
		}(agent)
	}

	// 等待所有goroutine完成后关闭channel
	go func() {
		wg.Wait()
		close(resultCh)
		close(errCh)
	}()

	// ===== Step 2: Fan-in 收集结果 =====
	for result := range resultCh {
		state.Analyses = append(state.Analyses, *result)
	}

	// 检查是否有错误
	for err := range errCh {
		fmt.Printf("警告: %v\n", err)
	}

	if len(state.Analyses) == 0 {
		return state, fmt.Errorf("所有分析Agent都失败了")
	}

	// ===== Step 3: 辩论（简化版） =====
	state.DebateResult = o.simpleDebate(state.Analyses)

	// ===== Step 4: 风控检查 =====
	state.RiskAssessment = o.checkRisk(state)

	// ===== Step 5: 条件执行 =====
	if state.RiskAssessment.Approved {
		state.ExecutionResult = &model.ExecutionResult{
			OrderID:  fmt.Sprintf("GO-%s", ticker),
			Ticker:   ticker,
			Side:     state.DebateResult.FinalSignal,
			Status:   "FILLED_DRY_RUN",
			Message:  fmt.Sprintf("[模拟] %s %s", state.DebateResult.FinalSignal, ticker),
		}
	} else {
		state.ExecutionResult = &model.ExecutionResult{
			Ticker:  ticker,
			Status:  "RISK_REJECTED",
			Message: fmt.Sprintf("风控否决: %s", state.RiskAssessment.Reasoning),
		}
	}

	return state, nil
}

func (o *TradingOrchestrator) simpleDebate(analyses []model.AnalysisResult) *model.DebateResult {
	var totalScore float64
	buyCount, sellCount := 0, 0
	var bullArgs, bearArgs []string

	for _, a := range analyses {
		totalScore += a.Score
		switch a.Signal {
		case "BUY":
			buyCount++
			bullArgs = append(bullArgs, fmt.Sprintf("[%s] %s (评分%.1f)", a.Agent, a.Reasoning, a.Score))
		case "SELL":
			sellCount++
			bearArgs = append(bearArgs, fmt.Sprintf("[%s] %s (评分%.1f)", a.Agent, a.Reasoning, a.Score))
		}
	}

	avgScore := totalScore / float64(len(analyses))
	signal := "HOLD"
	confidence := 0.5
	positionPct := 0.0

	if buyCount > sellCount && avgScore >= 6 {
		signal = "BUY"
		confidence = avgScore / 10.0
		positionPct = 0.05 + (avgScore-5)*0.01
	} else if sellCount > buyCount && avgScore <= 4 {
		signal = "SELL"
		confidence = (10 - avgScore) / 10.0
		positionPct = 0.0
	}

	return &model.DebateResult{
		BullArguments:     bullArgs,
		BearArguments:     bearArgs,
		FinalSignal:       signal,
		Confidence:        confidence,
		Reasoning:         fmt.Sprintf("综合评分%.1f, 多方%d/空方%d", avgScore, buyCount, sellCount),
		TargetPositionPct: positionPct,
	}
}

func (o *TradingOrchestrator) checkRisk(state *model.TradingState) *model.RiskAssessment {
	debate := state.DebateResult
	var violations []string

	if debate.TargetPositionPct > o.RiskConfig.MaxPositionSize {
		violations = append(violations, fmt.Sprintf(
			"仓位%.1f%%超限%.1f%%",
			debate.TargetPositionPct*100,
			o.RiskConfig.MaxPositionSize*100,
		))
	}

	if len(violations) > 0 {
		return &model.RiskAssessment{
			Approved:           false,
			HardRuleViolations: violations,
			Reasoning:          fmt.Sprintf("硬规则否决: %v", violations),
		}
	}

	approved := debate.Confidence >= 0.5
	return &model.RiskAssessment{
		Approved:            approved,
		RiskScore:           (1 - debate.Confidence) * 10,
		AdjustedPositionPct: debate.TargetPositionPct,
		Reasoning:           fmt.Sprintf("置信度%.0f%%, 风控%s", debate.Confidence*100, map[bool]string{true: "通过", false: "否决"}[approved]),
	}
}
