package com.trading.model;

/**
 * 分析结果 - 所有Agent统一的输出格式
 *
 * 面试要点：Java 21 record 替代传统POJO，不可变、自带equals/hashCode/toString
 */
public record AnalysisResult(
    String agent,
    String ticker,
    double score,
    String signal,
    String reasoning
) {
    public enum Signal {
        BUY, SELL, HOLD
    }

    public Signal signalEnum() {
        return switch (signal.toUpperCase()) {
            case "BUY" -> Signal.BUY;
            case "SELL" -> Signal.SELL;
            default -> Signal.HOLD;
        };
    }
}
