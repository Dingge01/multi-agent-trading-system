package model

// AnalysisResult 所有Agent的统一输出格式
type AnalysisResult struct {
	Agent     string  `json:"agent"`
	Ticker    string  `json:"ticker"`
	Score     float64 `json:"score"`
	Signal    string  `json:"signal"`
	Reasoning string  `json:"reasoning"`
}

// DebateResult 辩论Agent输出
type DebateResult struct {
	BullArguments    []string `json:"bull_arguments"`
	BearArguments    []string `json:"bear_arguments"`
	FinalSignal      string   `json:"final_signal"`
	Confidence       float64  `json:"confidence"`
	Reasoning        string   `json:"reasoning"`
	RecommendedAction string  `json:"recommended_action"`
	TargetPositionPct float64 `json:"target_position_pct"`
}

// RiskAssessment 风控评估
type RiskAssessment struct {
	Approved           bool     `json:"approved"`
	RiskScore          float64  `json:"risk_score"`
	Var95              float64  `json:"var_95"`
	HardRuleViolations []string `json:"hard_rule_violations"`
	SoftWarnings       []string `json:"soft_warnings"`
	AdjustedPositionPct float64 `json:"adjusted_position_pct"`
	StopLoss           float64  `json:"stop_loss"`
	TakeProfit         float64  `json:"take_profit"`
	Reasoning          string   `json:"reasoning"`
}

// ExecutionResult 执行结果
type ExecutionResult struct {
	OrderID     string  `json:"order_id"`
	Ticker      string  `json:"ticker"`
	Side        string  `json:"side"`
	Quantity    int     `json:"quantity"`
	Status      string  `json:"status"`
	FilledPrice float64 `json:"filled_price"`
	Slippage    float64 `json:"slippage"`
	Message     string  `json:"message"`
}

// TradingState 全局交易状态
type TradingState struct {
	Ticker          string
	Analyses        []AnalysisResult
	DebateResult    *DebateResult
	RiskAssessment  *RiskAssessment
	ExecutionResult *ExecutionResult
	PortfolioValue  float64
}
