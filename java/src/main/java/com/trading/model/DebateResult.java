package com.trading.model;

import java.util.List;

/**
 * 辩论结果
 */
public record DebateResult(
    List<String> bullArguments,
    List<String> bearArguments,
    String finalSignal,
    double confidence,
    String reasoning,
    String recommendedAction,
    double targetPositionPct
) {}
