"""
Trading Graph - LangGraph编排核心

这是整个多Agent系统的"中枢神经"，定义了Agent间的执行拓扑和数据流向。

编排模式：Parallel Fan-out → Fan-in → Sequential Pipeline
    标的股票 → [Fundamental + Technical + Sentiment] (并行)
    → Debate Agent (牛熊辩论)
    → Risk Agent (风控守门, 一票否决权)
    → Execution Agent (执行下单) / Reject (拒绝)

面试要点：
- StateGraph vs MessageGraph：StateGraph支持结构化状态，适合复杂业务流
- Annotated[list, operator.add]：reducer模式，并行节点结果自动合并
- 条件边(conditional_edge)：Risk Agent输出决定走向Execution还是Reject
- 检查点(checkpointer)：可回放任意步骤，便于调试和审计
"""
from __future__ import annotations

import operator
from typing import Annotated, Any, TypedDict

from langgraph.graph import StateGraph, END

from agents.fundamental_agent import FundamentalAgent
from agents.technical_agent import TechnicalAgent
from agents.sentiment_agent import SentimentAgent
from agents.debate_agent import DebateAgent
from agents.risk_agent import RiskAgent
from agents.execution_agent import ExecutionAgent


class TradingState(TypedDict):
    """
    全局状态定义 - 所有Agent共享的数据结构

    Annotated[list, operator.add] 是LangGraph的reducer模式：
    当多个并行节点同时写入 analyses 字段时，结果会自动 append 而非覆盖。
    这就是Fan-in的核心机制。
    """
    ticker: str
    analyses: Annotated[list[dict[str, Any]], operator.add]
    debate_result: dict[str, Any]
    risk_assessment: dict[str, Any]
    execution_result: dict[str, Any]
    portfolio_value: float
    portfolio_state: dict[str, Any] | None


def should_execute(state: TradingState) -> str:
    """
    条件路由函数：Risk Agent审批通过 → execute，否则 → reject

    这就是"一票否决权"的实现：Risk Agent的approved字段直接决定流向。
    """
    risk = state.get("risk_assessment", {})
    if risk.get("approved", False):
        return "execute"
    return "reject"


def reject_node(state: TradingState) -> dict[str, Any]:
    """风控否决后的终止节点"""
    return {
        "execution_result": {
            "order_id": "",
            "ticker": state["ticker"],
            "side": "none",
            "quantity": 0,
            "status": "RISK_REJECTED",
            "message": f"风控否决: {state.get('risk_assessment', {}).get('reasoning', '')}",
            "slippage": 0.0,
        }
    }


def build_trading_graph(dry_run: bool = True) -> StateGraph:
    """
    构建交易决策图

    图结构:
    START → [fundamental, technical, sentiment] (并行)
    → debate → risk → (execute | reject) → END

    Args:
        dry_run: True=模拟交易, False=真实下单(需配置Alpaca)
    """
    fundamental = FundamentalAgent()
    technical = TechnicalAgent()
    sentiment = SentimentAgent()
    debate = DebateAgent()
    risk = RiskAgent()
    execution = ExecutionAgent(dry_run=dry_run)

    graph = StateGraph(TradingState)

    graph.add_node("fundamental", fundamental.run)
    graph.add_node("technical", technical.run)
    graph.add_node("sentiment", sentiment.run)
    graph.add_node("debate", debate.run)
    graph.add_node("risk", risk.run)
    graph.add_node("execute", execution.run)
    graph.add_node("reject", reject_node)

    # --- 并行 Fan-out ---
    # START同时触发三个分析节点（LangGraph自动并行执行无依赖节点）
    graph.set_entry_point("fundamental")
    graph.add_edge("__start__", "technical")
    graph.add_edge("__start__", "sentiment")

    # --- Fan-in ---
    # 三个分析节点完成后，都汇入debate节点
    graph.add_edge("fundamental", "debate")
    graph.add_edge("technical", "debate")
    graph.add_edge("sentiment", "debate")

    # --- 串行 Pipeline ---
    graph.add_edge("debate", "risk")

    # --- 条件路由：风控守门 ---
    graph.add_conditional_edges(
        "risk",
        should_execute,
        {"execute": "execute", "reject": "reject"},
    )

    graph.add_edge("execute", END)
    graph.add_edge("reject", END)

    return graph


def create_app(dry_run: bool = True):
    """编译图为可执行应用"""
    graph = build_trading_graph(dry_run=dry_run)
    return graph.compile()


def run_analysis(ticker: str, portfolio_value: float = 1_000_000,
                 dry_run: bool = True) -> dict[str, Any]:
    """
    运行完整的投资决策流程

    Args:
        ticker: 股票代码，如 "AAPL", "MSFT"
        portfolio_value: 组合总市值
        dry_run: 是否模拟交易

    Returns:
        完整的决策结果状态
    """
    app = create_app(dry_run=dry_run)

    initial_state: TradingState = {
        "ticker": ticker,
        "analyses": [],
        "debate_result": {},
        "risk_assessment": {},
        "execution_result": {},
        "portfolio_value": portfolio_value,
        "portfolio_state": None,
    }

    result = app.invoke(initial_state)
    return result


if __name__ == "__main__":
    import json

    print("=" * 60)
    print("多Agent量化交易决策系统")
    print("=" * 60)

    ticker = input("请输入股票代码 (默认 AAPL): ").strip() or "AAPL"
    print(f"\n正在分析 {ticker}...\n")

    result = run_analysis(ticker)

    print("\n📊 分析结果:")
    for analysis in result.get("analyses", []):
        print(f"  [{analysis['agent']}] 评分: {analysis['score']}/10 | 信号: {analysis['signal']}")
        print(f"    理由: {analysis['reasoning']}")

    debate = result.get("debate_result", {})
    print(f"\n🗣️ 辩论结论: {debate.get('final_signal', 'N/A')} (置信度: {debate.get('confidence', 0):.0%})")
    print(f"  理由: {debate.get('reasoning', 'N/A')}")

    risk = result.get("risk_assessment", {})
    print(f"\n🛡️ 风控: {'通过' if risk.get('approved') else '否决'}")
    print(f"  VaR(95%): {risk.get('var_95', 0):.2%}")
    if risk.get("hard_rule_violations"):
        print(f"  硬规则违规: {risk['hard_rule_violations']}")

    exec_result = result.get("execution_result", {})
    print(f"\n💰 执行: {exec_result.get('status', 'N/A')}")
    print(f"  {exec_result.get('message', '')}")
