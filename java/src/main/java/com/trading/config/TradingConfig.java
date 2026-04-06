package com.trading.config;

import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.context.annotation.Configuration;

/**
 * 交易系统配置
 *
 * 面试要点：
 * - @ConfigurationProperties: 类型安全的配置绑定
 * - 所有敏感信息从环境变量注入，不硬编码
 */
@Configuration
@ConfigurationProperties(prefix = "trading")
public class TradingConfig {

    private double maxPositionSize = 0.10;
    private double maxDrawdownLimit = 0.08;
    private double stopLossPct = 0.05;
    private double takeProfitPct = 0.15;
    private double maxPortfolioRisk = 0.02;

    public double getMaxPositionSize() { return maxPositionSize; }
    public void setMaxPositionSize(double v) { this.maxPositionSize = v; }
    public double getMaxDrawdownLimit() { return maxDrawdownLimit; }
    public void setMaxDrawdownLimit(double v) { this.maxDrawdownLimit = v; }
    public double getStopLossPct() { return stopLossPct; }
    public void setStopLossPct(double v) { this.stopLossPct = v; }
    public double getTakeProfitPct() { return takeProfitPct; }
    public void setTakeProfitPct(double v) { this.takeProfitPct = v; }
    public double getMaxPortfolioRisk() { return maxPortfolioRisk; }
    public void setMaxPortfolioRisk(double v) { this.maxPortfolioRisk = v; }
}
