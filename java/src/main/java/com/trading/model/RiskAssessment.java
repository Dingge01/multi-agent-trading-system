package com.trading.model;

import java.util.List;

/**
 * 风控评估结果
 */
public record RiskAssessment(
    boolean approved,
    double riskScore,
    double var95,
    List<String> hardRuleViolations,
    List<String> softWarnings,
    double adjustedPositionPct,
    double stopLoss,
    double takeProfit,
    String reasoning
) {}
