"""
Debate Agent - 牛熊辩论Agent

职责：接收三维分析结果，分别从看多(Bull)和看空(Bear)角度辩论，综合生成最终决策。

面试要点（核心亮点）：
- 创新性辩论机制：强制从多空双方角度审视，避免单一偏见
- 辩论轮数限制（默认2轮）防止死循环
- 最终由"裁判"角色综合双方论点，而非简单投票
- 结构化输出：明确的信号+置信度+理由
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage

from config.settings import CONFIG, parse_llm_json

MAX_DEBATE_ROUNDS = 2


@dataclass
class DebateResult:
    bull_arguments: list[str]
    bear_arguments: list[str]
    final_signal: str
    confidence: float
    reasoning: str
    recommended_action: str
    target_position_pct: float


class DebateAgent:
    """
    辩论Agent：Bull方陈述 → Bear方反驳 → 多轮交锋 → Judge裁决

    这是本系统最大的创新点。通过强制对抗性辩论，确保决策考虑了多空双方的观点，
    避免"确认偏误"（只看到自己想看到的信号）。

    架构角色：Fan-in聚合后的核心决策节点，上游是三个并行分析Agent，下游是Risk Agent。
    """

    BULL_PROMPT = """你是一位坚定的看多分析师(Bull)。你的任务是基于以下分析数据，尽全力为"买入"找理由。
即使数据不完美，也要挖掘正面因素。但不要编造数据。

{previous_bear_argument}

请输出JSON:
{{"arguments": ["论点1", "论点2", "论点3"], "confidence": <0-1的看多信心>}}"""

    BEAR_PROMPT = """你是一位谨慎的看空分析师(Bear)。你的任务是基于以下分析数据，尽全力为"卖出/不买"找理由。
找出风险点和被忽视的负面因素。但不要编造数据。

{previous_bull_argument}

请输出JSON:
{{"arguments": ["论点1", "论点2", "论点3"], "confidence": <0-1的看空信心>}}"""

    JUDGE_PROMPT = """你是一位中立的投资决策裁判。你刚刚听完了Bull方和Bear方的辩论。

Bull方论点: {bull_args}
Bear方论点: {bear_args}

基于双方论点和原始分析数据，做出最终裁决。

请输出JSON:
{{
    "final_signal": "<BUY/SELL/HOLD>",
    "confidence": <0-1的决策信心>,
    "reasoning": "<200字以内的综合裁决理由>",
    "recommended_action": "<具体建议，如'建仓30%'或'观望等待RSI回落'>",
    "target_position_pct": <建议仓位百分比，0-1>
}}"""

    def __init__(self):
        kwargs = dict(
            model=CONFIG.llm.model,
            temperature=0.5,
            api_key=CONFIG.llm.api_key,
        )
        if CONFIG.llm.base_url:
            kwargs["base_url"] = CONFIG.llm.base_url
        self.llm = ChatOpenAI(**kwargs)

    def _format_analyses(self, analyses: list[dict]) -> str:
        lines = []
        for a in analyses:
            lines.append(f"【{a['agent']}分析】评分: {a['score']}/10, 信号: {a['signal']}")
            lines.append(f"  理由: {a['reasoning']}")
            if a.get("data"):
                lines.append(f"  数据: {json.dumps(a['data'], ensure_ascii=False)}")
        return "\n".join(lines)

    def _run_bull(self, data_summary: str, bear_rebuttal: str = "") -> dict:
        prev = f"\nBear方刚才的论点: {bear_rebuttal}\n请反驳并强化你的看多立场。" if bear_rebuttal else ""
        prompt = self.BULL_PROMPT.format(previous_bear_argument=prev)

        response = self.llm.invoke([
            SystemMessage(content=prompt),
            HumanMessage(content=f"分析数据:\n{data_summary}"),
        ])
        return parse_llm_json(
            response.content,
            default={"arguments": ["数据整体偏正面"], "confidence": 0.5}
        )

    def _run_bear(self, data_summary: str, bull_rebuttal: str = "") -> dict:
        prev = f"\nBull方刚才的论点: {bull_rebuttal}\n请反驳并强化你的看空立场。" if bull_rebuttal else ""
        prompt = self.BEAR_PROMPT.format(previous_bull_argument=prev)

        response = self.llm.invoke([
            SystemMessage(content=prompt),
            HumanMessage(content=f"分析数据:\n{data_summary}"),
        ])
        return parse_llm_json(
            response.content,
            default={"arguments": ["存在潜在风险"], "confidence": 0.5}
        )

    def _run_judge(self, data_summary: str, bull_args: list[str], bear_args: list[str]) -> dict:
        prompt = self.JUDGE_PROMPT.format(
            bull_args=json.dumps(bull_args, ensure_ascii=False),
            bear_args=json.dumps(bear_args, ensure_ascii=False),
        )
        response = self.llm.invoke([
            SystemMessage(content=prompt),
            HumanMessage(content=f"原始分析数据:\n{data_summary}"),
        ])
        return parse_llm_json(
            response.content,
            default={
                "final_signal": "HOLD",
                "confidence": 0.3,
                "reasoning": "辩论结果解析失败，保守持有",
                "recommended_action": "观望",
                "target_position_pct": 0.0,
            }
        )

    def debate(self, analyses: list[dict]) -> DebateResult:
        data_summary = self._format_analyses(analyses)
        print(f"    └─ 综合输入分析数据:\n{data_summary}")

        all_bull_args = []
        all_bear_args = []

        print(f"\n    ┌─ [辩论第 1 轮] Bull 方陈述")
        bull_result = self._run_bull(data_summary)
        print(f"    │  Bull 信心: {bull_result.get('confidence', 0):.0%}")
        for arg in bull_result.get("arguments", []):
            print(f"    │  • {arg}")
        all_bull_args.extend(bull_result.get("arguments", []))

        print(f"\n    ┌─ [辩论第 1 轮] Bear 方反驳")
        bear_result = self._run_bear(data_summary, str(all_bull_args))
        print(f"    │  Bear 信心: {bear_result.get('confidence', 0):.0%}")
        for arg in bear_result.get("arguments", []):
            print(f"    │  • {arg}")
        all_bear_args.extend(bear_result.get("arguments", []))

        for round_idx in range(MAX_DEBATE_ROUNDS - 1):
            r = round_idx + 2
            print(f"\n    ┌─ [辩论第 {r} 轮] Bull 方再反驳")
            bull_result = self._run_bull(data_summary, str(all_bear_args))
            print(f"    │  Bull 信心: {bull_result.get('confidence', 0):.0%}")
            for arg in bull_result.get("arguments", []):
                print(f"    │  • {arg}")
            all_bull_args.extend(bull_result.get("arguments", []))

            print(f"\n    ┌─ [辩论第 {r} 轮] Bear 方再反驳")
            bear_result = self._run_bear(data_summary, str(all_bull_args))
            print(f"    │  Bear 信心: {bear_result.get('confidence', 0):.0%}")
            for arg in bear_result.get("arguments", []):
                print(f"    │  • {arg}")
            all_bear_args.extend(bear_result.get("arguments", []))

        print(f"\n    ┌─ [Judge 裁决]")
        judge_result = self._run_judge(data_summary, all_bull_args, all_bear_args)
        print(f"    │  最终信号: {judge_result.get('final_signal', 'HOLD')}")
        print(f"    │  置信度: {judge_result.get('confidence', 0):.0%}")
        print(f"    │  建议操作: {judge_result.get('recommended_action', '观望')}")
        print(f"    │  目标仓位: {judge_result.get('target_position_pct', 0):.1%}")
        print(f"    │  裁决理由: {judge_result.get('reasoning', 'N/A')}")

        return DebateResult(
            bull_arguments=all_bull_args,
            bear_arguments=all_bear_args,
            final_signal=judge_result.get("final_signal", "HOLD"),
            confidence=judge_result.get("confidence", 0.3),
            reasoning=judge_result.get("reasoning", ""),
            recommended_action=judge_result.get("recommended_action", "观望"),
            target_position_pct=judge_result.get("target_position_pct", 0.0),
        )

    def run(self, state: dict[str, Any]) -> dict[str, Any]:
        """LangGraph节点入口"""
        analyses = state.get("analyses", [])
        print(f"\n{'═'*50}")
        print(f"  [Debate Agent] 开始对 {len(analyses)} 份分析进行牛熊辩论...")
        result = self.debate(analyses)
        print(f"\n  [Debate Agent] 完成 → 结论: {result.final_signal} (置信度: {result.confidence:.0%})")
        print(f"    └─ 建议操作: {result.recommended_action} | 目标仓位: {result.target_position_pct:.1%}")
        print(f"{'═'*50}")
        return {
            "debate_result": {
                "bull_arguments": result.bull_arguments,
                "bear_arguments": result.bear_arguments,
                "final_signal": result.final_signal,
                "confidence": result.confidence,
                "reasoning": result.reasoning,
                "recommended_action": result.recommended_action,
                "target_position_pct": result.target_position_pct,
            }
        }
