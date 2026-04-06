package com.trading.model;

/**
 * 执行结果
 */
public record ExecutionResult(
    String orderId,
    String ticker,
    String side,
    int quantity,
    String status,
    Double filledPrice,
    double slippage,
    String message
) {}
