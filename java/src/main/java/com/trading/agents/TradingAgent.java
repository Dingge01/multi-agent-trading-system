package com.trading.agents;

import com.trading.model.TradingState;

/**
 * Agent统一接口 - 所有Agent实现此接口
 *
 * 面试要点：
 * - 接口隔离原则(ISP)：每个Agent只需实现process方法
 * - 策略模式(Strategy Pattern)：运行时可替换Agent实现
 */
public interface TradingAgent {

    /**
     * 处理当前状态并更新
     * @param state 全局交易状态（线程安全）
     */
    void process(TradingState state);

    /**
     * Agent名称
     */
    String name();
}
