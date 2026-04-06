package com.trading.agents;

import com.trading.model.AnalysisResult;
import com.trading.model.TradingState;
import org.springframework.ai.chat.client.ChatClient;
import org.springframework.stereotype.Component;

/**
 * 基本面分析Agent - Java实现
 *
 * 面试要点：
 * - Spring AI ChatClient 统一了LLM调用接口
 * - @Component + 构造器注入：Spring DI最佳实践
 */
@Component
public class FundamentalAgent implements TradingAgent {

    private final ChatClient chatClient;

    public FundamentalAgent(ChatClient.Builder builder) {
        this.chatClient = builder.build();
    }

    @Override
    public String name() { return "fundamental"; }

    @Override
    public void process(TradingState state) {
        String prompt = """
            分析 %s 的基本面。请评估PE/PB/ROE/营收增长等指标，
            给出1-10的评分和BUY/SELL/HOLD信号。
            返回JSON: {"score": <分数>, "signal": "<信号>", "reasoning": "<理由>"}
            """.formatted(state.getTicker());

        String response = chatClient.prompt()
            .user(prompt)
            .call()
            .content();

        // 简化的JSON解析（生产环境应使用Jackson）
        var result = new AnalysisResult(
            name(),
            state.getTicker(),
            parseScore(response),
            parseSignal(response),
            parseReasoning(response)
        );
        state.addAnalysis(result);
    }

    private double parseScore(String json) {
        try {
            int idx = json.indexOf("\"score\"");
            if (idx < 0) return 5.0;
            String sub = json.substring(idx + 8).trim();
            sub = sub.replaceFirst("^:\\s*", "");
            StringBuilder num = new StringBuilder();
            for (char c : sub.toCharArray()) {
                if (Character.isDigit(c) || c == '.') num.append(c);
                else if (!num.isEmpty()) break;
            }
            return num.isEmpty() ? 5.0 : Double.parseDouble(num.toString());
        } catch (Exception e) { return 5.0; }
    }

    private String parseSignal(String json) {
        if (json.contains("BUY")) return "BUY";
        if (json.contains("SELL")) return "SELL";
        return "HOLD";
    }

    private String parseReasoning(String json) {
        try {
            int idx = json.indexOf("\"reasoning\"");
            if (idx < 0) return "";
            String sub = json.substring(idx);
            int start = sub.indexOf('"', 12) + 1;
            int end = sub.indexOf('"', start);
            return end > start ? sub.substring(start, end) : "";
        } catch (Exception e) { return ""; }
    }
}
