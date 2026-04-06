package com.trading.graph;

import com.trading.agents.TradingAgent;
import com.trading.model.TradingState;
import org.springframework.stereotype.Service;

import java.util.List;
import java.util.concurrent.StructuredTaskScope;

/**
 * 交易编排器 - 核心流程控制
 *
 * 面试要点（重要！）：
 * - Java 21 Virtual Threads: 轻量级线程，适合IO密集的LLM调用
 * - StructuredTaskScope: 结构化并发，确保所有子任务完成或全部取消
 * - 对应Python LangGraph的 Fan-out/Fan-in 模式
 *
 * 架构模式：
 *   START → [Fundamental + Technical + Sentiment] (Virtual Thread并行)
 *   → Debate → Risk → Execute/Reject → END
 */
@Service
public class TradingOrchestrator {

    private final List<TradingAgent> analysisAgents;
    private final TradingAgent debateAgent;
    private final TradingAgent riskAgent;
    private final TradingAgent executionAgent;

    public TradingOrchestrator(
            List<TradingAgent> analysisAgents,
            TradingAgent debateAgent,
            TradingAgent riskAgent,
            TradingAgent executionAgent
    ) {
        // 通过Spring DI注入不同角色的Agent
        this.analysisAgents = analysisAgents;
        this.debateAgent = debateAgent;
        this.riskAgent = riskAgent;
        this.executionAgent = executionAgent;
    }

    /**
     * 执行完整的投资决策流程
     *
     * 步骤：
     * 1. 并行执行三个分析Agent（Virtual Thread）
     * 2. 等待所有分析完成（Fan-in）
     * 3. 辩论Agent综合分析
     * 4. 风控Agent审批
     * 5. 条件执行：通过→下单，否决→终止
     */
    public TradingState execute(String ticker, double portfolioValue) {
        var state = new TradingState(ticker, portfolioValue);

        // --- Step 1: 并行Fan-out (Java 21 Structured Concurrency) ---
        try (var scope = new StructuredTaskScope.ShutdownOnFailure()) {
            for (TradingAgent agent : analysisAgents) {
                scope.fork(() -> {
                    agent.process(state);
                    return null;
                });
            }
            scope.join();
            scope.throwIfFailed();
        } catch (Exception e) {
            throw new RuntimeException("并行分析阶段失败: " + e.getMessage(), e);
        }

        // --- Step 2: 辩论 ---
        debateAgent.process(state);

        // --- Step 3: 风控 ---
        riskAgent.process(state);

        // --- Step 4: 条件执行 ---
        if (state.getRiskAssessment() != null && state.getRiskAssessment().approved()) {
            executionAgent.process(state);
        }
        // 否则 executionResult 保持 null，表示被风控否决

        return state;
    }
}
