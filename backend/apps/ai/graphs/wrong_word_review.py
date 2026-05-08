import json
import os
from functools import lru_cache
from typing import Any, Dict, TypedDict

from ..compat import END, START, LANGGRAPH_AVAILABLE, StateGraph, build_runtime_capabilities
from ..providers.deepseek import chat_json, is_provider_ready
from ..tools.study_tools import build_wrong_words_review_bundle

PROMPT_VERSION = "wrong_word_review_v1"


class WrongWordReviewState(TypedDict, total=False):
    user: Any
    limit: int
    review_bundle: Dict[str, Any]
    review: Dict[str, Any]
    runtime: Dict[str, Any]


def _build_review_fallback(bundle):
    total_wrong_words = int(bundle.get("total_wrong_words") or 0)
    priority_words = bundle.get("priority_words") or []
    wrong_patterns = bundle.get("wrong_patterns") or []
    adaptive = bundle.get("adaptive_snapshot") or {}

    if total_wrong_words <= 0:
        return {
            "headline": "当前错词本已经清空",
            "summary": "这说明你最近的回收效果不错，接下来更适合把精力放回新词和稳定复习上。",
            "mistake_patterns": [],
            "priority_words": [],
            "action_plan": ["继续保持每日复习节奏", "学完新词后及时回看例句", "每次复习后再检查一遍错词本"],
            "coach_line": "错词本空了不代表结束，而是说明你可以把注意力放到下一轮稳定输出上。",
        }

    headline = f"当前有 {total_wrong_words} 个活跃错词，先处理最常重复的那一批"
    summary = adaptive.get("focus_tip") or "先回收高频错词，再推进新的学习内容，整体效率会更高。"

    mistake_patterns = [
        f"{item.get('label', '某类词')} 相关错词风险更高，当前累计权重 {item.get('weight', 0)}。"
        for item in wrong_patterns[:3]
    ]
    if not mistake_patterns:
        mistake_patterns = ["当前错词较分散，建议按最近出错次数和例句理解优先级来回收。"]

    action_plan = [
        "先复习重复出错次数最多的 3 个词。",
        "每个词先看中文义项，再看英文例句，最后自己口头造句。",
        "复习后立刻做一轮小测，把新记住的词巩固住。",
    ]
    if priority_words:
        action_plan[0] = f"先处理 {priority_words[0]['word']} 等高频错词。"

    return {
        "headline": headline,
        "summary": summary,
        "mistake_patterns": mistake_patterns,
        "priority_words": priority_words[:4],
        "action_plan": action_plan,
        "coach_line": "错词本最有价值的地方不是记录你错过什么，而是告诉你下一步应该先救哪里。",
    }


def _generate_review_with_ai(state):
    bundle = state["review_bundle"]
    payload = {
        "wrong_word_snapshot": bundle,
        "task": "Summarize the user's wrong-word notebook in Chinese and provide a concrete recovery plan. Return strict JSON only.",
        "output_schema": {
            "headline": "string",
            "summary": "string",
            "mistake_patterns": ["string"],
            "priority_words": [
                {
                    "word": "string",
                    "meaning_cn": "string",
                    "wrong_count": 0,
                    "reason": "string",
                }
            ],
            "action_plan": ["string"],
            "coach_line": "string",
        },
    }
    result = chat_json(
        [
            {
                "role": "system",
                "content": (
                    "You are an English learning review coach for Chinese learners. "
                    "Stay grounded in the wrong-word snapshot and return strict JSON only."
                ),
            },
            {"role": "user", "content": json.dumps(payload, ensure_ascii=False, default=str)},
        ],
        temperature=0.25,
    )
    review = _build_review_fallback(bundle)
    review.update(
        {
            "headline": result.get("headline") or review["headline"],
            "summary": result.get("summary") or review["summary"],
            "mistake_patterns": result.get("mistake_patterns") or review["mistake_patterns"],
            "priority_words": result.get("priority_words") or review["priority_words"],
            "action_plan": result.get("action_plan") or review["action_plan"],
            "coach_line": result.get("coach_line") or review["coach_line"],
        }
    )
    return review


def _node_load_bundle(state):
    return {"review_bundle": build_wrong_words_review_bundle(state["user"], state.get("limit", 12))}


def _node_generate_result(state):
    runtime = build_runtime_capabilities()
    review = _generate_review_with_ai(state) if is_provider_ready() else _build_review_fallback(state["review_bundle"])
    return {
        "runtime": runtime,
        "review": review,
    }


@lru_cache(maxsize=1)
def _build_graph():
    graph = StateGraph(WrongWordReviewState)
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


def build_wrong_words_review_detail(user, limit=12):
    state = _run_graph(
        {
            "user": user,
            "limit": limit,
        }
    )
    return {
        "headline": state.get("review", {}).get("headline", ""),
        "summary": state.get("review", {}).get("summary", ""),
        "review": state.get("review", {}),
        "snapshot": state.get("review_bundle", {}),
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
