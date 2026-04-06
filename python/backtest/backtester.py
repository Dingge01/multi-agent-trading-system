"""
回测引擎 - 验证多Agent策略的历史表现

核心指标：
- 年化收益率 (Annualized Return)
- 夏普比率 (Sharpe Ratio): 风险调整后收益，>1好，>2优秀
- 最大回撤 (Maximum Drawdown): 峰值到谷值的最大跌幅
- 索提诺比率 (Sortino Ratio): 只考虑下行风险的夏普比率
- 胜率 (Win Rate): 盈利交易占比

面试要点：
- 夏普比率 = (策略年化收益 - 无风险利率) / 策略年化波动率
- 最大回撤 = max(peak - trough) / peak
- 回测陷阱：过拟合、前瞻偏差(look-ahead bias)、幸存者偏差
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

import numpy as np
import pandas as pd
import yfinance as yf


@dataclass
class Trade:
    date: str
    ticker: str
    side: str
    quantity: int
    price: float
    value: float
    signal_source: str = ""


@dataclass
class BacktestResult:
    initial_capital: float
    final_value: float
    total_return: float
    annualized_return: float
    sharpe_ratio: float
    sortino_ratio: float
    max_drawdown: float
    win_rate: float
    total_trades: int
    winning_trades: int
    losing_trades: int
    avg_win: float
    avg_loss: float
    profit_factor: float
    trades: list[Trade] = field(default_factory=list)
    equity_curve: list[float] = field(default_factory=list)
    benchmark_return: float = 0.0


class SimpleBacktester:
    """
    简化回测引擎

    流程：
    1. 按日遍历历史数据
    2. 每个交易日用简化版信号生成逻辑（代替完整Agent调用，节省API成本）
    3. 根据信号执行交易
    4. 计算绩效指标

    注意：完整Agent回测需要大量LLM API调用，生产环境用此简化版做快速验证，
    关键日期再用完整Agent做决策。
    """

    def __init__(self, initial_capital: float = 1_000_000,
                 risk_free_rate: float = 0.04,
                 max_position_pct: float = 0.10,
                 stop_loss_pct: float = 0.05):
        self.initial_capital = initial_capital
        self.risk_free_rate = risk_free_rate
        self.max_position_pct = max_position_pct
        self.stop_loss_pct = stop_loss_pct

    def _generate_signal(self, row: pd.Series, indicators: pd.DataFrame,
                          idx: int) -> str:
        """
        简化版信号生成（模拟多Agent决策结果）

        规则：
        - RSI<30 且 MACD金叉 → BUY
        - RSI>70 且 MACD死叉 → SELL
        - 其他 → HOLD
        """
        if idx < 1:
            return "HOLD"

        rsi = row.get("RSI_14")
        macd_hist = row.get("MACDh_12_26_9")
        prev_macd_hist = indicators.iloc[idx - 1].get("MACDh_12_26_9")

        if rsi is None or macd_hist is None or prev_macd_hist is None:
            return "HOLD"
        if pd.isna(rsi) or pd.isna(macd_hist) or pd.isna(prev_macd_hist):
            return "HOLD"

        macd_cross_up = prev_macd_hist < 0 and macd_hist >= 0
        macd_cross_down = prev_macd_hist > 0 and macd_hist <= 0

        if rsi < 35 and macd_cross_up:
            return "BUY"
        if rsi > 65 and macd_cross_down:
            return "SELL"
        if rsi < 30:
            return "BUY"
        if rsi > 75:
            return "SELL"
        return "HOLD"

    def run(self, ticker: str, start_date: str, end_date: str) -> BacktestResult:
        stock = yf.Ticker(ticker)
        df = stock.history(start=start_date, end=end_date)
        if df.empty:
            raise ValueError(f"无法获取 {ticker} 在 {start_date} 到 {end_date} 的数据")

        import pandas_ta as ta
        df.ta.macd(append=True)
        df.ta.rsi(append=True)
        df.ta.bbands(length=20, append=True)
        df.ta.sma(length=20, append=True)
        df.ta.sma(length=50, append=True)

        cash = self.initial_capital
        position = 0
        entry_price = 0.0
        trades: list[Trade] = []
        equity_curve = []
        wins = []
        losses = []

        for idx in range(len(df)):
            row = df.iloc[idx]
            current_price = row["Close"]
            date_str = df.index[idx].strftime("%Y-%m-%d")

            portfolio_value = cash + position * current_price
            equity_curve.append(portfolio_value)

            if position > 0 and entry_price > 0:
                pnl_pct = (current_price - entry_price) / entry_price
                if pnl_pct <= -self.stop_loss_pct:
                    sell_value = position * current_price
                    cash += sell_value
                    trades.append(Trade(date_str, ticker, "sell_stop", position,
                                        current_price, sell_value, "stop_loss"))
                    loss = (current_price - entry_price) * position
                    losses.append(loss)
                    position = 0
                    entry_price = 0
                    continue

            signal = self._generate_signal(row, df, idx)

            if signal == "BUY" and position == 0:
                max_invest = portfolio_value * self.max_position_pct
                quantity = int(max_invest / current_price)
                if quantity > 0:
                    cost = quantity * current_price
                    cash -= cost
                    position = quantity
                    entry_price = current_price
                    trades.append(Trade(date_str, ticker, "buy", quantity,
                                        current_price, cost, "signal"))

            elif signal == "SELL" and position > 0:
                sell_value = position * current_price
                cash += sell_value
                pnl = (current_price - entry_price) * position
                if pnl > 0:
                    wins.append(pnl)
                else:
                    losses.append(pnl)
                trades.append(Trade(date_str, ticker, "sell", position,
                                    current_price, sell_value, "signal"))
                position = 0
                entry_price = 0

        final_value = cash + position * df.iloc[-1]["Close"]
        equity_curve.append(final_value) if len(equity_curve) < len(df) else None

        equity_series = pd.Series(equity_curve)
        daily_returns = equity_series.pct_change().dropna()

        total_return = (final_value - self.initial_capital) / self.initial_capital
        trading_days = len(df)
        annualized_return = (1 + total_return) ** (252 / max(trading_days, 1)) - 1

        annual_vol = daily_returns.std() * np.sqrt(252) if len(daily_returns) > 1 else 0.01
        sharpe = (annualized_return - self.risk_free_rate) / annual_vol if annual_vol > 0 else 0

        downside = daily_returns[daily_returns < 0]
        downside_vol = downside.std() * np.sqrt(252) if len(downside) > 1 else 0.01
        sortino = (annualized_return - self.risk_free_rate) / downside_vol if downside_vol > 0 else 0

        peak = equity_series.expanding().max()
        drawdown = (equity_series - peak) / peak
        max_drawdown = abs(drawdown.min())

        total_wins = len(wins)
        total_losses = len(losses)
        total_trades_count = total_wins + total_losses
        win_rate = total_wins / total_trades_count if total_trades_count > 0 else 0

        avg_win = np.mean(wins) if wins else 0
        avg_loss = abs(np.mean(losses)) if losses else 0.01
        profit_factor = (sum(wins) / abs(sum(losses))) if losses and sum(losses) != 0 else float("inf")

        benchmark = stock.history(start=start_date, end=end_date)
        bench_return = 0.0
        if not benchmark.empty:
            bench_return = (benchmark["Close"].iloc[-1] - benchmark["Close"].iloc[0]) / benchmark["Close"].iloc[0]

        return BacktestResult(
            initial_capital=self.initial_capital,
            final_value=round(final_value, 2),
            total_return=round(total_return, 4),
            annualized_return=round(annualized_return, 4),
            sharpe_ratio=round(sharpe, 2),
            sortino_ratio=round(sortino, 2),
            max_drawdown=round(max_drawdown, 4),
            win_rate=round(win_rate, 4),
            total_trades=len(trades),
            winning_trades=total_wins,
            losing_trades=total_losses,
            avg_win=round(avg_win, 2),
            avg_loss=round(avg_loss, 2),
            profit_factor=round(profit_factor, 2),
            trades=trades,
            equity_curve=equity_curve,
            benchmark_return=round(bench_return, 4),
        )


def print_backtest_report(result: BacktestResult):
    """打印回测报告"""
    print("=" * 60)
    print("             回测绩效报告")
    print("=" * 60)
    print(f"  初始资金:        ${result.initial_capital:,.0f}")
    print(f"  最终市值:        ${result.final_value:,.0f}")
    print(f"  总收益率:        {result.total_return:.2%}")
    print(f"  年化收益率:      {result.annualized_return:.2%}")
    print(f"  基准收益率:      {result.benchmark_return:.2%}")
    print(f"  超额收益:        {result.annualized_return - result.benchmark_return:.2%}")
    print("-" * 60)
    print(f"  夏普比率:        {result.sharpe_ratio}")
    print(f"  索提诺比率:      {result.sortino_ratio}")
    print(f"  最大回撤:        {result.max_drawdown:.2%}")
    print(f"  盈亏比:          {result.profit_factor}")
    print("-" * 60)
    print(f"  总交易次数:      {result.total_trades}")
    print(f"  胜率:            {result.win_rate:.2%}")
    print(f"  盈利交易:        {result.winning_trades}")
    print(f"  亏损交易:        {result.losing_trades}")
    print(f"  平均盈利:        ${result.avg_win:,.2f}")
    print(f"  平均亏损:        ${result.avg_loss:,.2f}")
    print("=" * 60)


if __name__ == "__main__":
    bt = SimpleBacktester(initial_capital=1_000_000)
    result = bt.run("AAPL", "2025-01-01", "2025-08-31")
    print_backtest_report(result)
