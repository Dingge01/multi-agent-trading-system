package main

import (
	"context"
	"fmt"
	"os"

	openai "github.com/sashabaranov/go-openai"
	"github.com/joho/godotenv"

	"github.com/multi-agent-trading/golang/internal/agents"
	"github.com/multi-agent-trading/golang/internal/graph"
)

func main() {
	godotenv.Load("../.env")

	apiKey := os.Getenv("OPENAI_API_KEY")
	if apiKey == "" {
		fmt.Println("请设置 OPENAI_API_KEY 环境变量")
		os.Exit(1)
	}

	model := os.Getenv("OPENAI_MODEL")
	if model == "" {
		model = "gpt-4"
	}

	client := openai.NewClient(apiKey)

	analysisAgents := []agents.Agent{
		agents.NewFundamentalAgent(client, model),
		agents.NewTechnicalAgent(client, model),
		agents.NewSentimentAgent(client, model),
	}

	debateAgent := &agents.BaseLLMAgent{Client: client, Model: model}

	riskCfg := graph.RiskConfig{
		MaxPositionSize:  0.10,
		MaxDrawdownLimit: 0.08,
		StopLossPct:      0.05,
		MaxPortfolioRisk: 0.02,
	}

	orchestrator := graph.NewOrchestrator(analysisAgents, debateAgent, riskCfg)

	ticker := "AAPL"
	if len(os.Args) > 1 {
		ticker = os.Args[1]
	}

	fmt.Printf("========================================\n")
	fmt.Printf("  多Agent量化交易决策系统 (Go版)\n")
	fmt.Printf("  分析标的: %s\n", ticker)
	fmt.Printf("========================================\n\n")

	ctx := context.Background()
	state, err := orchestrator.Execute(ctx, ticker, 1_000_000)
	if err != nil {
		fmt.Printf("执行失败: %v\n", err)
		os.Exit(1)
	}

	fmt.Println("--- 分析结果 ---")
	for _, a := range state.Analyses {
		fmt.Printf("  [%s] 评分: %.1f/10 | 信号: %s\n", a.Agent, a.Score, a.Signal)
		fmt.Printf("    理由: %s\n", a.Reasoning)
	}

	if state.DebateResult != nil {
		fmt.Printf("\n--- 辩论结论 ---\n")
		fmt.Printf("  信号: %s (置信度: %.0f%%)\n", state.DebateResult.FinalSignal, state.DebateResult.Confidence*100)
		fmt.Printf("  理由: %s\n", state.DebateResult.Reasoning)
	}

	if state.RiskAssessment != nil {
		status := "否决"
		if state.RiskAssessment.Approved {
			status = "通过"
		}
		fmt.Printf("\n--- 风控 ---\n")
		fmt.Printf("  状态: %s\n", status)
		fmt.Printf("  理由: %s\n", state.RiskAssessment.Reasoning)
	}

	if state.ExecutionResult != nil {
		fmt.Printf("\n--- 执行 ---\n")
		fmt.Printf("  状态: %s\n", state.ExecutionResult.Status)
		fmt.Printf("  %s\n", state.ExecutionResult.Message)
	}
}
