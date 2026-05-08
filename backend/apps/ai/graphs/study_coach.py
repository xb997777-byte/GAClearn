import json
import os
from functools import lru_cache
from typing import Any, Dict, TypedDict

from ..compat import END, START, LANGGRAPH_AVAILABLE, StateGraph, build_runtime_capabilities
from ..profile_memory import get_or_refresh_profile_memory, serialize_profile_memory
from ..providers.deepseek import chat_json, is_provider_ready
from ..tools.study_tools import build_study_coach_bundle

PROMPT_VERSION = "study_coach_v1"


class StudyCoachState(TypedDict, total=False):
    user: Any
    trend_days: int
    coach_bundle: Dict[str, Any]
    profile_memory: Dict[str, Any]
    coach: Dict[str, Any]
    runtime: Dict[str, Any]


def _build_focus_items(bundle):
    adaptive = bundle.get("adaptive") or {}
    overview = bundle.get("overview") or {}
    result = []

    result.append(
        {
            "title": "今日任务节奏",
            "detail": adaptive.get("focus_tip") or "先把今日任务拆成小步推进。",
        }
    )

    wrong_words = bundle.get("priority_wrong_words") or []
    if wrong_words:
        result.append(
            {
                "title": "错词回收",
                "detail": f"优先处理 {wrong_words[0]['word']} 等高频错词，减少重复出错。",
            }
        )

    result.append(
        {
            "title": "连续学习",
            "detail": f"当前连续学习 {overview.get('streak_days', 0)} 天，保持稳定节奏比一次冲太猛更重要。",
        }
    )
    return result[:3]


def _build_coach_fallback(bundle):
    today_task = bundle.get("today_task") or {}
    plan = today_task.get("plan")
    adaptive = bundle.get("adaptive") or {}
    overview = bundle.get("overview") or {}
    summary = today_task.get("summary") or {}

    if not plan:
        return {
            "headline": "今天先建立学习主线",
            "today_strategy": "你还没有激活词书计划，先选一本词书并设定每日目标，后面的 AI 建议才会更准确。",
            "coach_tip": "先把主航道搭起来，再谈强度和提速。",
            "recommended_order": ["选择词书", "设置每日目标", "开始第一组新词", "完成一次复习"],
            "focus_items": [
                {"title": "先建计划", "detail": "没有当前计划时，首页建议会偏泛化。"},
                {"title": "先学后调优", "detail": "先完成一轮学习记录，AI 才能根据你的真实状态做推荐。"},
            ],
            "next_action": "先去词书页选择一本适合当前阶段的词书。",
            "motivation_line": "先把今天的第一步走出来，后面就会顺很多。",
        }

    mode_label = adaptive.get("mode_label") or "保持稳定推进"
    new_remaining = summary.get("new_words_remaining", 0)
    review_remaining = summary.get("review_words_remaining", 0)

    return {
        "headline": f"今天建议按“{mode_label}”推进",
        "today_strategy": adaptive.get("focus_tip") or "先完成高优先级任务，再推进新词。",
        "coach_tip": (
            f"当前还有 {review_remaining} 个复习任务、{new_remaining} 个新词任务。"
            " 先稳住正确率，再决定要不要加快节奏。"
        ),
        "recommended_order": ["先复习到期词", "再学今日新词", "再看错词本", "最后用语法例句巩固"],
        "focus_items": _build_focus_items(bundle),
        "next_action": "先点“开始复习”或“继续学习”，把今天最容易拖延的部分先清掉。",
        "motivation_line": f"你已经累计学过 {overview.get('learned_word_count', 0)} 个词，今天只需要把节奏续上。",
    }


def _generate_coach_with_ai(state):
    bundle = state["coach_bundle"]
    profile_memory = state.get("profile_memory") or {}
    payload = {
        "study_snapshot": bundle,
        "profile_memory": profile_memory,
        "task": "Create a compact Chinese study coach briefing for today's English learning plan. Return strict JSON only.",
        "output_schema": {
            "headline": "string",
            "today_strategy": "string",
            "coach_tip": "string",
            "recommended_order": ["string"],
            "focus_items": [
                {
                    "title": "string",
                    "detail": "string",
                }
            ],
            "next_action": "string",
            "motivation_line": "string",
        },
    }
    result = chat_json(
        [
            {
                "role": "system",
                "content": (
                    "You are an English learning coach for Chinese learners. "
                    "Base every suggestion on the provided study snapshot and return strict JSON only."
                ),
            },
            {"role": "user", "content": json.dumps(payload, ensure_ascii=False, default=str)},
        ],
        temperature=0.25,
    )
    coach = _build_coach_fallback(bundle)
    coach.update(
        {
            "headline": result.get("headline") or coach["headline"],
            "today_strategy": result.get("today_strategy") or coach["today_strategy"],
            "coach_tip": result.get("coach_tip") or coach["coach_tip"],
            "recommended_order": result.get("recommended_order") or coach["recommended_order"],
            "focus_items": result.get("focus_items") or coach["focus_items"],
            "next_action": result.get("next_action") or coach["next_action"],
            "motivation_line": result.get("motivation_line") or coach["motivation_line"],
        }
    )
    return coach


def _node_load_bundle(state):
    memory = get_or_refresh_profile_memory(state["user"], source="study_coach")
    return {
        "coach_bundle": build_study_coach_bundle(state["user"], state.get("trend_days", 7)),
        "profile_memory": serialize_profile_memory(memory),
    }


def _node_generate_result(state):
    runtime = build_runtime_capabilities()
    coach = _generate_coach_with_ai(state) if is_provider_ready() else _build_coach_fallback(state["coach_bundle"])
    return {
        "runtime": runtime,
        "coach": coach,
    }


@lru_cache(maxsize=1)
def _build_graph():
    graph = StateGraph(StudyCoachState)
    graph.add_node("load_bundle", _node_load_bundle)
    graph.add_node("generate_result", _node_generate_result)
    graph.add_edge(START, "load_bundle")
    graph.add_edge("load_bundle", "generate_result")
    graph.add_edge("generate_result", END)
    return graph.compile()


def _run_pipeline(initial_state):
    state = dict(initial_state)
    state.update(_node_load_bundle(state))
    state.update(_node_generate_result(state))
    return state


def _run_graph(initial_state):
    if LANGGRAPH_AVAILABLE:
        return _build_graph().invoke(initial_state)
    return _run_pipeline(initial_state)


def build_study_coach_detail(user, trend_days=7):
    state = _run_graph(
        {
            "user": user,
            "trend_days": trend_days,
        }
    )
    data = {
        "headline": state.get("coach", {}).get("headline", ""),
        "summary": state.get("coach", {}).get("today_strategy", "") or state.get("coach", {}).get("coach_tip", ""),
        "coach": state.get("coach", {}),
        "snapshot": state.get("coach_bundle", {}),
        "profile_memory": state.get("profile_memory", {}),
        "langchain_trace": [],
        "runtime_stack": {},
        "ai_strategy": {
            "engine": "langgraph" if LANGGRAPH_AVAILABLE else "pipeline",
            "rag_enabled": True,
            "ai_enabled": is_provider_ready(),
            "prompt_version": PROMPT_VERSION,
            "model_name": os.getenv("AI_MODEL", "").strip(),
        },
        "runtime": state.get("runtime", build_runtime_capabilities()),
    }
    return data
