import json
import os
from functools import lru_cache
from typing import Any, Dict, TypedDict

from apps.grammar.analyzer import analyze_sentence_input

from ..compat import END, START, LANGGRAPH_AVAILABLE, StateGraph, build_runtime_capabilities
from ..providers.deepseek import chat_json, is_provider_ready
from ..rag.retrievers import as_langchain_documents, build_grammar_retrieval_bundle
from ..tools.grammar_tools import build_grammar_user_profile

PROMPT_VERSION = "grammar_tutor_v1"


class GrammarTutorState(TypedDict, total=False):
    user: Any
    sentence: str
    question: str
    detail: Dict[str, Any]
    user_profile: Dict[str, Any]
    retrieval: Dict[str, Any]
    tutor: Dict[str, Any]
    question_payload: Dict[str, Any]
    runtime: Dict[str, Any]


def _fallback_mini_quiz(detail):
    predicate = ""
    for chunk in detail.get("chunk_breakdown") or []:
        if chunk.get("role_type") == "predicate":
            predicate = chunk.get("en", "")
            break

    return {
        "type": "choice",
        "prompt": "这句话的谓语核心是哪一部分？",
        "options": [chunk.get("en", "") for chunk in (detail.get("chunk_breakdown") or [])[:4] if chunk.get("en")],
        "answer": predicate,
        "explanation": "谓语通常承担动作、状态和时态信息，先找到它，整句就更容易读清楚。",
    }


def _build_tutor_fallback(detail, retrieval, user_profile):
    focus_items = []
    for tag in detail.get("grammar_tags") or []:
        if tag not in focus_items:
            focus_items.append(tag)
    for item in user_profile.get("weak_points") or []:
        title = item.get("title")
        if title and title not in focus_items:
            focus_items.append(title)

    followups = [
        "这句话的主语和谓语分别是什么？",
        "这里为什么会出现这个语法结构？",
        "给我一个结构相近但更简单的例句。",
    ]
    if detail.get("main_structure"):
        explanation = (
            f"先把主干读成“{detail.get('main_structure')}”，"
            f"再回填 { '、'.join(detail.get('grammar_tags') or ['补充结构']) } 这些附加层。"
        )
    else:
        explanation = detail.get("analysis") or detail.get("summary") or "先抓句子主干，再看补充信息。"

    coach_tip = detail.get("point_detail", {}).get("learning_tip") or "先抓主语和谓语，再看修饰层。"
    if user_profile.get("weak_points"):
        coach_tip = f"你最近在“{user_profile['weak_points'][0]['title']}”上更容易卡住，建议这次先看主干再回填细节。"

    return {
        "explanation_cn": explanation,
        "coach_tip": coach_tip,
        "recommended_focus": focus_items[:4],
        "followup_questions": followups,
        "mini_quiz": _fallback_mini_quiz(detail),
        "references": [item["title"] for item in retrieval.get("related_points") or []][:3],
    }


def _build_question_fallback(detail, retrieval, question):
    answer = detail.get("analysis") or detail.get("summary") or "建议先看句子主干，再结合附加结构理解。"
    if question and "主语" in question:
        subject = next((chunk.get("en") for chunk in detail.get("chunk_breakdown") or [] if chunk.get("role_type") in {"subject", "gerund", "infinitive"}), "")
        if subject:
            answer = f"这句话的主语核心是“{subject}”。先锁定它，再去找谓语和宾语会更轻松。"
    elif question and "谓语" in question:
        predicate = next((chunk.get("en") for chunk in detail.get("chunk_breakdown") or [] if chunk.get("role_type") == "predicate"), "")
        if predicate:
            answer = f"这句话的谓语核心是“{predicate}”，它承担了动作和时态信息。"

    return {
        "answer": answer,
        "references": [item["title"] for item in retrieval.get("related_points") or []][:3],
        "followup_questions": [
            "请继续告诉我这句话的宾语在哪里。",
            "把这句话改成更简单的表达。",
        ],
    }


def _generate_tutor_with_ai(state):
    detail = state["detail"]
    retrieval = state["retrieval"]
    user_profile = state["user_profile"]
    payload = {
        "sentence": state["sentence"],
        "rule_detail": {
            "translation_cn": detail.get("translation_cn", ""),
            "summary": detail.get("summary", ""),
            "analysis": detail.get("analysis", ""),
            "main_structure": detail.get("main_structure", ""),
            "grammar_tags": detail.get("grammar_tags", []),
            "chunk_breakdown": detail.get("chunk_breakdown", []),
        },
        "user_profile": user_profile,
        "retrieval": retrieval,
        "task": "Explain the sentence for Chinese learners and create a tiny targeted quiz.",
        "output_schema": {
            "explanation_cn": "string",
            "coach_tip": "string",
            "recommended_focus": ["string"],
            "followup_questions": ["string"],
            "mini_quiz": {
                "type": "choice",
                "prompt": "string",
                "options": ["string"],
                "answer": "string",
                "explanation": "string",
            },
        },
    }
    result = chat_json(
        [
            {
                "role": "system",
                "content": (
                    "You are an expert English grammar tutor for Chinese learners. "
                    "Use the provided retrieval context and return strict JSON only."
                ),
            },
            {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
        ],
        temperature=0.2,
    )
    tutor = _build_tutor_fallback(detail, retrieval, user_profile)
    tutor.update(
        {
            "explanation_cn": result.get("explanation_cn") or tutor["explanation_cn"],
            "coach_tip": result.get("coach_tip") or tutor["coach_tip"],
            "recommended_focus": result.get("recommended_focus") or tutor["recommended_focus"],
            "followup_questions": result.get("followup_questions") or tutor["followup_questions"],
            "mini_quiz": result.get("mini_quiz") or tutor["mini_quiz"],
        }
    )
    return tutor


def _generate_question_with_ai(state):
    detail = state["detail"]
    retrieval = state["retrieval"]
    payload = {
        "sentence": state["sentence"],
        "question": state["question"],
        "detail": {
            "translation_cn": detail.get("translation_cn", ""),
            "summary": detail.get("summary", ""),
            "analysis": detail.get("analysis", ""),
            "main_structure": detail.get("main_structure", ""),
            "grammar_tags": detail.get("grammar_tags", []),
        },
        "retrieval": retrieval,
        "task": "Answer the user's grammar question in concise Chinese and return strict JSON only.",
        "output_schema": {
            "answer": "string",
            "references": ["string"],
            "followup_questions": ["string"],
        },
    }
    result = chat_json(
        [
            {
                "role": "system",
                "content": (
                    "You are an expert English grammar tutor for Chinese learners. "
                    "Answer with clear teaching language and strict JSON only."
                ),
            },
            {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
        ],
        temperature=0.3,
    )
    fallback = _build_question_fallback(detail, retrieval, state["question"])
    fallback.update(
        {
            "answer": result.get("answer") or fallback["answer"],
            "references": result.get("references") or fallback["references"],
            "followup_questions": result.get("followup_questions") or fallback["followup_questions"],
        }
    )
    return fallback


def _node_load_detail(state):
    if state.get("detail"):
        return {}
    return {"detail": analyze_sentence_input(state["sentence"], enable_ai_enrichment=False)}


def _node_load_profile(state):
    user = state.get("user")
    return {"user_profile": build_grammar_user_profile(user) if user else {}}


def _node_retrieve_context(state):
    retrieval = build_grammar_retrieval_bundle(state["detail"], question=state.get("question", ""))
    retrieval["langchain_documents_count"] = len(as_langchain_documents(retrieval))
    return {"retrieval": retrieval}


def _node_generate_result(state):
    runtime = build_runtime_capabilities()
    if state.get("question"):
        if is_provider_ready():
            question_payload = _generate_question_with_ai(state)
        else:
            question_payload = _build_question_fallback(state["detail"], state["retrieval"], state["question"])
        return {
            "runtime": runtime,
            "question_payload": question_payload,
        }

    if is_provider_ready():
        tutor = _generate_tutor_with_ai(state)
    else:
        tutor = _build_tutor_fallback(state["detail"], state["retrieval"], state["user_profile"])

    return {
        "runtime": runtime,
        "tutor": tutor,
    }


@lru_cache(maxsize=1)
def _build_graph():
    graph = StateGraph(GrammarTutorState)
    graph.add_node("load_detail", _node_load_detail)
    graph.add_node("load_profile", _node_load_profile)
    graph.add_node("retrieve_context", _node_retrieve_context)
    graph.add_node("generate_result", _node_generate_result)
    graph.add_edge(START, "load_detail")
    graph.add_edge("load_detail", "load_profile")
    graph.add_edge("load_profile", "retrieve_context")
    graph.add_edge("retrieve_context", "generate_result")
    graph.add_edge("generate_result", END)
    return graph.compile()


def _run_pipeline(initial_state):
    state = dict(initial_state)
    state.update(_node_load_detail(state))
    state.update(_node_load_profile(state))
    state.update(_node_retrieve_context(state))
    state.update(_node_generate_result(state))
    return state


def _run_graph(initial_state):
    if LANGGRAPH_AVAILABLE:
        return _build_graph().invoke(initial_state)
    return _run_pipeline(initial_state)


def build_grammar_tutor_detail(user, sentence, detail=None):
    state = _run_graph(
        {
            "user": user,
            "sentence": sentence,
            "question": "",
            "detail": detail,
        }
    )
    result = dict(state["detail"])
    result["analysis_mode"] = "ai" if is_provider_ready() else result.get("analysis_mode", "rule")
    result["sentence"] = sentence
    result["headline"] = "AI 语法讲解"
    result["summary"] = (state.get("tutor") or {}).get("explanation_cn", "")
    result["ai_strategy"] = {
        "engine": "langgraph" if LANGGRAPH_AVAILABLE else "pipeline",
        "rag_enabled": True,
        "ai_enabled": is_provider_ready(),
        "prompt_version": PROMPT_VERSION,
        "model_name": os.getenv("AI_MODEL", "").strip(),
    }
    result["retrieval"] = state.get("retrieval", {})
    result["tutor"] = state.get("tutor", {})
    result["runtime"] = state.get("runtime", build_runtime_capabilities())
    result["langchain_trace"] = []
    result["runtime_stack"] = {}
    return result


def build_grammar_tutor_answer(user, sentence, question, detail=None):
    state = _run_graph(
        {
            "user": user,
            "sentence": sentence,
            "question": question,
            "detail": detail,
        }
    )
    payload = state.get("question_payload", {})
    payload["sentence"] = sentence
    payload["question"] = question
    payload["headline"] = "AI 语法问答"
    payload["summary"] = payload.get("answer", "")
    payload["ai_enabled"] = is_provider_ready()
    payload["ai_strategy"] = {
        "engine": "langgraph" if LANGGRAPH_AVAILABLE else "pipeline",
        "rag_enabled": True,
        "ai_enabled": is_provider_ready(),
        "prompt_version": PROMPT_VERSION,
        "model_name": os.getenv("AI_MODEL", "").strip(),
    }
    payload["runtime"] = state.get("runtime", build_runtime_capabilities())
    payload["retrieval"] = state.get("retrieval", {})
    payload["langchain_trace"] = []
    payload["runtime_stack"] = {}
    return payload
