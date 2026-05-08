import json
import os
from functools import lru_cache
from typing import Any, Dict, TypedDict

from ..compat import END, START, LANGGRAPH_AVAILABLE, StateGraph, build_runtime_capabilities
from ..providers.deepseek import chat_json, is_provider_ready
from ..tools.word_tools import build_word_tutor_bundle

PROMPT_VERSION = "vocab_tutor_v1"


class VocabTutorState(TypedDict, total=False):
    user: Any
    word_id: int
    word_bundle: Dict[str, Any]
    tutor: Dict[str, Any]
    runtime: Dict[str, Any]


def _build_quiz(word_detail):
    related_words = word_detail.get("related_words") or []
    meaning_options = [word_detail.get("meaning_cn", "")]
    for item in related_words[:3]:
        if item.get("meaning_cn"):
            meaning_options.append(item["meaning_cn"])

    options = []
    seen = set()
    for item in meaning_options:
        text = (item or "").strip()
        if not text or text in seen:
            continue
        seen.add(text)
        options.append(text)

    return {
        "prompt": f"下面哪个中文释义最贴近 {word_detail.get('word', '这个词')}？",
        "options": options[:4],
        "answer": (word_detail.get("meaning_cn") or "").strip(),
        "explanation": "先把核心中文义项记稳，再回到例句里确认这个词在真实语境中的作用。",
    }


def _build_synonym_compare(word_detail):
    result = []
    for item in (word_detail.get("related_words") or [])[:3]:
        result.append(
            {
                "word": item.get("word", ""),
                "meaning_cn": item.get("meaning_cn", ""),
                "difference": item.get("reason", "") or "和当前词词性接近，适合放在一起辨析。",
            }
        )
    return result


def _build_tutor_fallback(bundle):
    word_detail = bundle["word_detail"]
    user_profile = bundle["user_profile"]
    examples_preview = word_detail.get("examples_preview") or []
    example_sentence = ""
    example_translation = ""
    if examples_preview:
        example_sentence = examples_preview[0].get("sentence", "")
        example_translation = examples_preview[0].get("translation", "")

    simple_explanation_cn = word_detail.get("meaning_cn") or "先看这个词在当前词书里的核心含义。"
    if word_detail.get("part_of_speech"):
        simple_explanation_cn = f"{simple_explanation_cn}，这里主要按 {word_detail['part_of_speech']} 来理解。"

    memory_tip = f"把“{word_detail.get('word', '')} = {word_detail.get('meaning_cn', '')}”先配对记住。"
    if example_sentence:
        memory_tip = f"先背住例句里的“{example_sentence}”，这个词会更容易和真实语境绑定起来。"

    usage_tip = "先看例句，再模仿它的词性和位置自己造一个短句。"
    if example_translation:
        usage_tip = f"这句例句的中文是“{example_translation}”，建议对照中英文一起看它在句中的作用。"

    confusing_points = []
    for item in (word_detail.get("related_words") or [])[:3]:
        confusing_points.append(
            f"{word_detail.get('word', '')} 和 {item.get('word', '')} 都常见于 {item.get('part_of_speech', '相近')} 场景，但含义侧重点不完全一样。"
        )
    if not confusing_points and word_detail.get("synonym_list"):
        confusing_points.append(
            f"它和 {word_detail['synonym_list'][0]} 看起来接近，但还是要回到例句里区分具体语气和搭配。"
        )

    followups = [
        "给我再举一个更简单的例句。",
        "这个词最容易和哪个词混淆？",
        "帮我出一道同义词辨析题。",
    ]

    return {
        "simple_explanation_cn": simple_explanation_cn,
        "memory_tip": memory_tip,
        "usage_tip": usage_tip,
        "confusing_points": confusing_points[:3],
        "synonym_compare": _build_synonym_compare(word_detail),
        "why_recommended": user_profile.get("why_recommended", ""),
        "mini_quiz": _build_quiz(word_detail),
        "followup_questions": followups,
    }


def _generate_tutor_with_ai(state):
    bundle = state["word_bundle"]
    word_detail = bundle["word_detail"]
    payload = {
        "word_detail": {
            "word": word_detail.get("word", ""),
            "phonetic": word_detail.get("phonetic", ""),
            "part_of_speech": word_detail.get("part_of_speech", ""),
            "meaning_cn": word_detail.get("meaning_cn", ""),
            "example_sentence": word_detail.get("example_sentence", ""),
            "example_translation": word_detail.get("example_translation", ""),
            "synonym_list": word_detail.get("synonym_list", []),
            "example_phrases": word_detail.get("example_phrases", []),
            "related_words": word_detail.get("related_words", []),
            "book": word_detail.get("book", {}),
        },
        "user_profile": bundle.get("user_profile", {}),
        "task": "Explain the word for a Chinese learner and generate one tiny vocabulary quiz. Return strict JSON only.",
        "output_schema": {
            "simple_explanation_cn": "string",
            "memory_tip": "string",
            "usage_tip": "string",
            "confusing_points": ["string"],
            "synonym_compare": [
                {
                    "word": "string",
                    "meaning_cn": "string",
                    "difference": "string",
                }
            ],
            "why_recommended": "string",
            "mini_quiz": {
                "prompt": "string",
                "options": ["string"],
                "answer": "string",
                "explanation": "string",
            },
            "followup_questions": ["string"],
        },
    }
    result = chat_json(
        [
            {
                "role": "system",
                "content": (
                    "You are an expert English vocabulary tutor for Chinese learners. "
                    "Stay grounded in the provided word data and return strict JSON only."
                ),
            },
            {"role": "user", "content": json.dumps(payload, ensure_ascii=False, default=str)},
        ],
        temperature=0.2,
    )
    tutor = _build_tutor_fallback(bundle)
    tutor.update(
        {
            "simple_explanation_cn": result.get("simple_explanation_cn") or tutor["simple_explanation_cn"],
            "memory_tip": result.get("memory_tip") or tutor["memory_tip"],
            "usage_tip": result.get("usage_tip") or tutor["usage_tip"],
            "confusing_points": result.get("confusing_points") or tutor["confusing_points"],
            "synonym_compare": result.get("synonym_compare") or tutor["synonym_compare"],
            "why_recommended": result.get("why_recommended") or tutor["why_recommended"],
            "mini_quiz": result.get("mini_quiz") or tutor["mini_quiz"],
            "followup_questions": result.get("followup_questions") or tutor["followup_questions"],
        }
    )
    return tutor


def _node_load_bundle(state):
    return {"word_bundle": build_word_tutor_bundle(state["user"], state["word_id"])}


def _node_generate_result(state):
    runtime = build_runtime_capabilities()
    tutor = _generate_tutor_with_ai(state) if is_provider_ready() else _build_tutor_fallback(state["word_bundle"])
    return {
        "runtime": runtime,
        "tutor": tutor,
    }


@lru_cache(maxsize=1)
def _build_graph():
    graph = StateGraph(VocabTutorState)
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


def build_word_tutor_detail(user, word_id):
    state = _run_graph(
        {
            "user": user,
            "word_id": word_id,
        }
    )
    return {
        "headline": f"AI 讲词：{(state.get('word_bundle') or {}).get('word_detail', {}).get('word', '')}",
        "summary": state.get("tutor", {}).get("simple_explanation_cn", ""),
        "word_id": word_id,
        "tutor": state.get("tutor", {}),
        "snapshot": state["word_bundle"],
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
