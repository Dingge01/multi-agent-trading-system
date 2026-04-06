package com.trading.model;

import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.CopyOnWriteArrayList;

/**
 * 交易流程全局状态 - 线程安全版本
 *
 * 面试要点：
 * - CopyOnWriteArrayList 保证并行Fan-out写入安全
 * - 对应Python版的 Annotated[list, operator.add] reducer
 */
public class TradingState {
    private final String ticker;
    private final CopyOnWriteArrayList<AnalysisResult> analyses = new CopyOnWriteArrayList<>();
    private volatile DebateResult debateResult;
    private volatile RiskAssessment riskAssessment;
    private volatile ExecutionResult executionResult;
    private final double portfolioValue;

    public TradingState(String ticker, double portfolioValue) {
        this.ticker = ticker;
        this.portfolioValue = portfolioValue;
    }

    public String getTicker() { return ticker; }
    public double getPortfolioValue() { return portfolioValue; }
    public List<AnalysisResult> getAnalyses() { return List.copyOf(analyses); }

    public void addAnalysis(AnalysisResult result) { analyses.add(result); }

    public DebateResult getDebateResult() { return debateResult; }
    public void setDebateResult(DebateResult r) { this.debateResult = r; }

    public RiskAssessment getRiskAssessment() { return riskAssessment; }
    public void setRiskAssessment(RiskAssessment r) { this.riskAssessment = r; }

    public ExecutionResult getExecutionResult() { return executionResult; }
    public void setExecutionResult(ExecutionResult r) { this.executionResult = r; }
}
