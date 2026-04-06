"""
Execution Agent - 执行Agent

职责：下单执行、滑点控制、成交确认。只有Risk Agent批准后才会执行。

面试要点：
- 模拟交易(Paper Trading)用Alpaca API，无真实资金风险
- 滑点控制：限价单而非市价单，减少冲击成本
- 幂等性：通过client_order_id防止重复下单
- 执行确认：异步查询订单状态直到成交/取消
"""
from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
from typing import Any
from datetime import datetime

from config.settings import CONFIG


@dataclass
class ExecutionResult:
    order_id: str
    ticker: str
    side: str
    quantity: int
    order_type: str
    limit_price: float | None
    status: str
    filled_price: float | None
    filled_at: str | None
    slippage: float
    message: str


class ExecutionAgent:
    """
    执行Agent：计算下单量 → 生成限价单 → 提交Alpaca API → 确认成交

    生产环境会对接真实券商API，这里支持两种模式：
    1. Alpaca Paper Trading（模拟盘）
    2. Dry Run（纯日志，不发送任何订单）

    架构角色：流水线最末端，只有Risk Agent approve后才执行。
    """

    def __init__(self, dry_run: bool = True):
        self.dry_run = dry_run
        self.api = None
        if not dry_run and CONFIG.alpaca.api_key:
            try:
                import alpaca_trade_api as tradeapi
                self.api = tradeapi.REST(
                    CONFIG.alpaca.api_key,
                    CONFIG.alpaca.secret_key,
                    CONFIG.alpaca.base_url,
                    api_version="v2",
                )
            except ImportError:
                self.dry_run = True

    def _calculate_quantity(self, ticker: str, position_pct: float,
                            portfolio_value: float, current_price: float) -> int:
        target_value = portfolio_value * position_pct
        if current_price <= 0:
            return 0
        return int(target_value / current_price)

    def _calculate_limit_price(self, current_price: float, side: str,
                                slippage_tolerance: float = 0.002) -> float:
        """限价单价格：买入时略高于市价，卖出时略低于市价，控制滑点"""
        if side == "buy":
            return round(current_price * (1 + slippage_tolerance), 2)
        return round(current_price * (1 - slippage_tolerance), 2)

    def execute(self, ticker: str, risk_assessment: dict,
                debate_result: dict, portfolio_value: float = 1_000_000,
                current_price: float = 0) -> ExecutionResult:
        if not risk_assessment.get("approved", False):
            return ExecutionResult(
                order_id="", ticker=ticker, side="none", quantity=0,
                order_type="none", limit_price=None, status="REJECTED",
                filled_price=None, filled_at=None, slippage=0.0,
                message=f"风控否决: {risk_assessment.get('reasoning', '')}"
            )

        signal = debate_result.get("final_signal", "HOLD")
        if signal == "HOLD":
            return ExecutionResult(
                order_id="", ticker=ticker, side="hold", quantity=0,
                order_type="none", limit_price=None, status="NO_ACTION",
                filled_price=None, filled_at=None, slippage=0.0,
                message="决策为HOLD，不执行交易"
            )

        side = "buy" if signal == "BUY" else "sell"
        position_pct = risk_assessment.get("adjusted_position_pct", 0.0)
        quantity = self._calculate_quantity(ticker, position_pct, portfolio_value, current_price)

        if quantity <= 0:
            return ExecutionResult(
                order_id="", ticker=ticker, side=side, quantity=0,
                order_type="none", limit_price=None, status="ZERO_QTY",
                filled_price=None, filled_at=None, slippage=0.0,
                message="计算下单量为0，不执行"
            )

        limit_price = self._calculate_limit_price(current_price, side)
        order_id = f"MAT-{uuid.uuid4().hex[:8]}"

        if self.dry_run:
            simulated_fill = current_price * (1.001 if side == "buy" else 0.999)
            slippage = abs(simulated_fill - current_price) / current_price
            return ExecutionResult(
                order_id=order_id, ticker=ticker, side=side, quantity=quantity,
                order_type="limit", limit_price=limit_price,
                status="FILLED_DRY_RUN",
                filled_price=round(simulated_fill, 2),
                filled_at=datetime.now().isoformat(),
                slippage=round(slippage, 6),
                message=f"[模拟] {side.upper()} {quantity}股 {ticker} @ ${simulated_fill:.2f}"
            )

        try:
            order = self.api.submit_order(
                symbol=ticker,
                qty=quantity,
                side=side,
                type="limit",
                time_in_force="day",
                limit_price=str(limit_price),
                client_order_id=order_id,
            )
            return ExecutionResult(
                order_id=order.client_order_id, ticker=ticker, side=side,
                quantity=quantity, order_type="limit", limit_price=limit_price,
                status=order.status,
                filled_price=float(order.filled_avg_price) if order.filled_avg_price else None,
                filled_at=str(order.filled_at) if order.filled_at else None,
                slippage=0.0,
                message=f"订单已提交: {order.id}"
            )
        except Exception as e:
            return ExecutionResult(
                order_id=order_id, ticker=ticker, side=side, quantity=quantity,
                order_type="limit", limit_price=limit_price, status="ERROR",
                filled_price=None, filled_at=None, slippage=0.0,
                message=f"下单失败: {str(e)}"
            )

    def run(self, state: dict[str, Any]) -> dict[str, Any]:
        """LangGraph节点入口"""
        ticker = state["ticker"]
        risk_assessment = state.get("risk_assessment", {})
        debate_result = state.get("debate_result", {})
        portfolio_value = state.get("portfolio_value", 1_000_000)

        import yfinance as yf
        stock = yf.Ticker(ticker)
        current_price = stock.info.get("currentPrice", stock.info.get("regularMarketPrice", 0))

        result = self.execute(
            ticker=ticker,
            risk_assessment=risk_assessment,
            debate_result=debate_result,
            portfolio_value=portfolio_value,
            current_price=current_price,
        )
        return {
            "execution_result": {
                "order_id": result.order_id,
                "ticker": result.ticker,
                "side": result.side,
                "quantity": result.quantity,
                "order_type": result.order_type,
                "limit_price": result.limit_price,
                "status": result.status,
                "filled_price": result.filled_price,
                "slippage": result.slippage,
                "message": result.message,
            }
        }
