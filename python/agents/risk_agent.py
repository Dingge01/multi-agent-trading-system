"""
Risk Agent - 风控守门Agent

职责：仓位控制、最大回撤限制、VaR计算、止损止盈检查。拥有一票否决权。

面试要点（核心亮点）：
- 一票否决权：即使Debate Agent给出BUY信号，Risk Agent也能因风控原因拒绝
- 双层门控：硬规则（确定性，不依赖LLM）+ LLM判断（软规则，处理边界情况）
- VaR（Value at Risk）：基于历史波动率计算在给定置信度下的最大损失
- 为什么风控不能全靠LLM？因为LLM可能被prompt注入或产生幻觉，硬规则保证底线
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

import numpy as np
import yfinance as yf
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage

from config.settings import CONFIG, parse_llm_json, get_yf_session


@dataclass
class RiskAssessment:
    approved: bool
    risk_score: float
    var_95: float
    max_position_allowed: float
    hard_rule_violations: list[str]
    soft_warnings: list[str]
    adjusted_position_pct: float
    stop_loss: float
    take_profit: float
    reasoning: str


class RiskAgent:
    """
    风控Agent：硬规则检查 → VaR计算 → LLM软判断 → 通过/否决

    硬规则（确定性，不可绕过）：
    1. 单票仓位不超过总资产的10%
    2. 组合最大回撤不超过8%
    3. VaR(95%)不超过组合2%
    4. 止损线5%

    软规则（LLM判断）：
    1. 市场极端波动时建议降低仓位
    2. 关联股票集中度风险
    3. 流动性不足警告

    架构角色：Debate Agent下游的守门员，有一票否决权。只有通过才传递给Execution Agent。
    """

    SYSTEM_PROMPT = """你是一位严格的风控官。你已经看到了辩论结果和硬规则检查结果。
你的任务是做最终的风控判断。

即使硬规则都通过了，如果你认为存在未被量化的风险，你仍然可以建议降低仓位或否决交易。
你是最后一道防线。

请输出JSON:
{
    "approved": <true/false>,
    "adjusted_position_pct": <调整后的建议仓位，0-1>,
    "soft_warnings": ["警告1", "警告2"],
    "reasoning": "<100字以内的风控判断理由>"
}"""

    def __init__(self):
        kwargs = dict(
            model=CONFIG.llm.model,
            temperature=0.1,
            api_key=CONFIG.llm.api_key,
        )
        if CONFIG.llm.base_url:
            kwargs["base_url"] = CONFIG.llm.base_url
        self.llm = ChatOpenAI(**kwargs)
        self.risk_config = CONFIG.risk

    def _calculate_var(self, ticker: str, confidence: float = 0.95, period: str = "1y") -> float:
        """历史模拟法VaR: 基于过去一年日收益率分布，计算95%置信度下的单日最大损失"""
        try:
            stock = yf.Ticker(ticker, session=get_yf_session())
            df = stock.history(period=period)
            if df.empty or len(df) < 30:
                return 0.05

            daily_returns = df["Close"].pct_change().dropna()
            var = np.percentile(daily_returns, (1 - confidence) * 100)
            return abs(float(var))
        except Exception:
            return 0.05

    def _check_hard_rules(self, ticker: str, proposed_position: float,
                          portfolio_drawdown: float = 0.0) -> list[str]:
        """硬规则检查 - 确定性逻辑，不依赖LLM"""
        violations = []

        if proposed_position > self.risk_config.max_position_size:
            violations.append(
                f"单票仓位{proposed_position:.1%}超过限制{self.risk_config.max_position_size:.1%}"
            )

        if portfolio_drawdown > self.risk_config.max_drawdown_limit:
            violations.append(
                f"组合回撤{portfolio_drawdown:.1%}超过限制{self.risk_config.max_drawdown_limit:.1%}"
            )

        var = self._calculate_var(ticker)
        if var * proposed_position > self.risk_config.max_portfolio_risk:
            violations.append(
                f"VaR风险敞口{var * proposed_position:.2%}超过限制{self.risk_config.max_portfolio_risk:.2%}"
            )

        return violations

    def assess(self, ticker: str, debate_result: dict, portfolio_state: dict | None = None) -> RiskAssessment:
        proposed_position = debate_result.get("target_position_pct", 0.0)
        portfolio_drawdown = (portfolio_state or {}).get("current_drawdown", 0.0)

        print(f"    └─ 输入参数:")
        print(f"       建议仓位: {proposed_position:.1%}")
        print(f"       当前组合回撤: {portfolio_drawdown:.1%}")
        print(f"       辩论结论: {debate_result.get('final_signal', 'HOLD')}")

        print(f"    └─ 计算 VaR(95%)...")
        var_95 = self._calculate_var(ticker)
        print(f"       VaR(95%): {var_95:.2%}")

        print(f"    └─ 检查硬规则...")
        hard_violations = self._check_hard_rules(ticker, proposed_position, portfolio_drawdown)
        if hard_violations:
            print(f"       ⚠️ 硬规则违规:")
            for v in hard_violations:
                print(f"         • {v}")
        else:
            print(f"       ✅ 硬规则全部通过")

        if hard_violations:
            return RiskAssessment(
                approved=False,
                risk_score=9.0,
                var_95=var_95,
                max_position_allowed=self.risk_config.max_position_size,
                hard_rule_violations=hard_violations,
                soft_warnings=[],
                adjusted_position_pct=0.0,
                stop_loss=0.0,
                take_profit=0.0,
                reasoning=f"硬规则否决: {'; '.join(hard_violations)}",
            )

        user_prompt = f"""请对以下交易决策做风控评估：

标的: {ticker}
辩论结论: {debate_result.get('final_signal', 'HOLD')}
建议仓位: {proposed_position:.1%}
辩论置信度: {debate_result.get('confidence', 0):.1%}
VaR(95%): {var_95:.2%}
辩论理由: {debate_result.get('reasoning', '')}
当前组合回撤: {portfolio_drawdown:.1%}"""

        print(f"    └─ 调用 LLM 进行软规则风控评估...")
        response = self.llm.invoke([
            SystemMessage(content=self.SYSTEM_PROMPT),
            HumanMessage(content=user_prompt),
        ])
        print(f"    └─ LLM 原始返回:\n{response.content}")

        result = parse_llm_json(
            response.content,
            default={
                "approved": False,
                "adjusted_position_pct": 0.0,
                "soft_warnings": ["LLM输出解析失败，保守否决"],
                "reasoning": "解析失败，安全起见否决",
            }
        )

        adjusted_pos = min(
            result.get("adjusted_position_pct", 0.0),
            self.risk_config.max_position_size,
        )

        try:
            stock = yf.Ticker(ticker, session=get_yf_session())
            current_price = stock.info.get("currentPrice", stock.info.get("regularMarketPrice", 0))
        except Exception:
            current_price = 0
        stop_loss = current_price * (1 - self.risk_config.stop_loss_pct) if current_price else 0
        take_profit = current_price * (1 + self.risk_config.take_profit_pct) if current_price else 0

        print(f"    └─ 风控计算结果:")
        print(f"       批准状态: {'通过' if result.get('approved', False) else '否决'}")
        print(f"       调整后仓位: {adjusted_pos:.1%}")
        print(f"       止损价: ${stop_loss:.2f}" if stop_loss else "       止损价: N/A")
        print(f"       止盈价: ${take_profit:.2f}" if take_profit else "       止盈价: N/A")
        soft_warnings = result.get("soft_warnings", [])
        if soft_warnings:
            print(f"       软警告:")
            for w in soft_warnings:
                print(f"         • {w}")

        return RiskAssessment(
            approved=result.get("approved", False),
            risk_score=var_95 * 100,
            var_95=var_95,
            max_position_allowed=self.risk_config.max_position_size,
            hard_rule_violations=[],
            soft_warnings=result.get("soft_warnings", []),
            adjusted_position_pct=adjusted_pos,
            stop_loss=stop_loss,
            take_profit=take_profit,
            reasoning=result.get("reasoning", ""),
        )

    def run(self, state: dict[str, Any]) -> dict[str, Any]:
        """LangGraph节点入口"""
        ticker = state["ticker"]
        debate_result = state.get("debate_result", {})
        portfolio_state = state.get("portfolio_state")

        print(f"\n{'═'*50}")
        print(f"  [Risk Agent] 开始对 {ticker} 进行风控审查...")
        assessment = self.assess(ticker, debate_result, portfolio_state)
        status = "通过" if assessment.approved else "否决"
        print(f"\n  [Risk Agent] 完成 → {status} (VaR: {assessment.var_95:.2%})")
        print(f"    └─ 风控理由: {assessment.reasoning}")
        print(f"{'═'*50}")
        return {
            "risk_assessment": {
                "approved": assessment.approved,
                "risk_score": assessment.risk_score,
                "var_95": assessment.var_95,
                "hard_rule_violations": assessment.hard_rule_violations,
                "soft_warnings": assessment.soft_warnings,
                "adjusted_position_pct": assessment.adjusted_position_pct,
                "stop_loss": assessment.stop_loss,
                "take_profit": assessment.take_profit,
                "reasoning": assessment.reasoning,
            }
        }
