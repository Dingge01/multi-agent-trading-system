package agents

import (
	"context"
	"encoding/json"
	"fmt"

	openai "github.com/sashabaranov/go-openai"

	"github.com/multi-agent-trading/golang/internal/model"
)

// Agent 接口 - 所有Agent实现此接口
// 面试要点：Go的接口是隐式实现（duck typing），比Java的显式implements更灵活
type Agent interface {
	Name() string
	Analyze(ctx context.Context, ticker string) (*model.AnalysisResult, error)
}

// BaseLLMAgent 提供共享的LLM调用能力
type BaseLLMAgent struct {
	Client *openai.Client
	Model  string
}

func (b *BaseLLMAgent) CallLLM(ctx context.Context, systemPrompt, userPrompt string) (string, error) {
	resp, err := b.Client.CreateChatCompletion(ctx, openai.ChatCompletionRequest{
		Model: b.Model,
		Messages: []openai.ChatCompletionMessage{
			{Role: openai.ChatMessageRoleSystem, Content: systemPrompt},
			{Role: openai.ChatMessageRoleUser, Content: userPrompt},
		},
		Temperature: 0.3,
	})
	if err != nil {
		return "", fmt.Errorf("LLM调用失败: %w", err)
	}
	if len(resp.Choices) == 0 {
		return "", fmt.Errorf("LLM返回空结果")
	}
	return resp.Choices[0].Message.Content, nil
}

// FundamentalAgent 基本面分析
type FundamentalAgent struct {
	BaseLLMAgent
}

func NewFundamentalAgent(client *openai.Client, model string) *FundamentalAgent {
	return &FundamentalAgent{BaseLLMAgent{Client: client, Model: model}}
}

func (a *FundamentalAgent) Name() string { return "fundamental" }

func (a *FundamentalAgent) Analyze(ctx context.Context, ticker string) (*model.AnalysisResult, error) {
	systemPrompt := `你是基本面分析师。分析给定股票的PE/PB/ROE/营收增长。
输出JSON: {"score": <1-10>, "signal": "<BUY/SELL/HOLD>", "reasoning": "<理由>"}`

	userPrompt := fmt.Sprintf("请分析 %s 的基本面", ticker)

	content, err := a.CallLLM(ctx, systemPrompt, userPrompt)
	if err != nil {
		return &model.AnalysisResult{Agent: a.Name(), Ticker: ticker, Score: 5, Signal: "HOLD", Reasoning: err.Error()}, nil
	}

	var result struct {
		Score     float64 `json:"score"`
		Signal    string  `json:"signal"`
		Reasoning string  `json:"reasoning"`
	}
	if err := json.Unmarshal([]byte(content), &result); err != nil {
		return &model.AnalysisResult{Agent: a.Name(), Ticker: ticker, Score: 5, Signal: "HOLD", Reasoning: "JSON解析失败"}, nil
	}

	return &model.AnalysisResult{
		Agent: a.Name(), Ticker: ticker,
		Score: result.Score, Signal: result.Signal, Reasoning: result.Reasoning,
	}, nil
}

// TechnicalAgent 技术面分析
type TechnicalAgent struct {
	BaseLLMAgent
}

func NewTechnicalAgent(client *openai.Client, model string) *TechnicalAgent {
	return &TechnicalAgent{BaseLLMAgent{Client: client, Model: model}}
}

func (a *TechnicalAgent) Name() string { return "technical" }

func (a *TechnicalAgent) Analyze(ctx context.Context, ticker string) (*model.AnalysisResult, error) {
	systemPrompt := `你是技术分析师。分析给定股票的MACD/RSI/布林带/均线系统。
输出JSON: {"score": <1-10>, "signal": "<BUY/SELL/HOLD>", "reasoning": "<理由>"}`

	content, err := a.CallLLM(ctx, systemPrompt, fmt.Sprintf("请分析 %s 的技术指标", ticker))
	if err != nil {
		return &model.AnalysisResult{Agent: a.Name(), Ticker: ticker, Score: 5, Signal: "HOLD"}, nil
	}

	var result struct {
		Score     float64 `json:"score"`
		Signal    string  `json:"signal"`
		Reasoning string  `json:"reasoning"`
	}
	json.Unmarshal([]byte(content), &result)

	return &model.AnalysisResult{
		Agent: a.Name(), Ticker: ticker,
		Score: result.Score, Signal: result.Signal, Reasoning: result.Reasoning,
	}, nil
}

// SentimentAgent 情绪面分析
type SentimentAgent struct {
	BaseLLMAgent
}

func NewSentimentAgent(client *openai.Client, model string) *SentimentAgent {
	return &SentimentAgent{BaseLLMAgent{Client: client, Model: model}}
}

func (a *SentimentAgent) Name() string { return "sentiment" }

func (a *SentimentAgent) Analyze(ctx context.Context, ticker string) (*model.AnalysisResult, error) {
	systemPrompt := `你是市场情绪分析师。分析给定股票的新闻情绪、机构持仓、分析师评级。
输出JSON: {"score": <1-10>, "signal": "<BUY/SELL/HOLD>", "reasoning": "<理由>"}`

	content, err := a.CallLLM(ctx, systemPrompt, fmt.Sprintf("请分析 %s 的市场情绪", ticker))
	if err != nil {
		return &model.AnalysisResult{Agent: a.Name(), Ticker: ticker, Score: 5, Signal: "HOLD"}, nil
	}

	var result struct {
		Score     float64 `json:"score"`
		Signal    string  `json:"signal"`
		Reasoning string  `json:"reasoning"`
	}
	json.Unmarshal([]byte(content), &result)

	return &model.AnalysisResult{
		Agent: a.Name(), Ticker: ticker,
		Score: result.Score, Signal: result.Signal, Reasoning: result.Reasoning,
	}, nil
}
