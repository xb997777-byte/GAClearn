from __future__ import annotations

from typing import Any, Dict, List


def _string(value: Any, default: str = "") -> str:
    text = str(value or "").strip()
    return text or default


def _list(value: Any) -> List[Any]:
    return value if isinstance(value, list) else []


def _dict(value: Any) -> Dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _build_runtime_summary(payload: Dict[str, Any], feature_runtime: Dict[str, Any]) -> Dict[str, Any]:
    observability = _dict(payload.get("ai_observability"))
    retrieval_strategy = _dict(payload.get("retrieval_strategy"))
    runtime = _dict(payload.get("runtime"))
    ai_strategy = _dict(payload.get("ai_strategy"))
    run_id = _string(observability.get("run_id"))
    latency_ms = int(observability.get("latency_ms") or 0)
    cache_hit = bool(observability.get("cache_hit"))
    status = _string(observability.get("status"), "success")
    ai_enabled = bool(ai_strategy.get("ai_enabled", runtime.get("ai_model_env_ready", False)))
    degraded = bool(feature_runtime.get("fallback")) or bool(retrieval_strategy.get("degraded")) or not ai_enabled
    degraded_reason = ""
    if retrieval_strategy.get("backend") == "in_process_counter_cosine":
        degraded_reason = "当前未使用标准向量库，已回退到本地轻量检索。"
    elif feature_runtime.get("fallback"):
        degraded_reason = "当前功能已走回退链路，返回的是可用结果而不是完整 AI 链路。"
    elif not ai_enabled:
        degraded_reason = "当前未连接可用模型，结果由本地规则或回退逻辑生成。"
    if status == "failed":
        status_text = "本次执行失败"
    elif status == "rate_limited":
        status_text = "请求过于频繁"
    elif degraded:
        status_text = "已完成，当前结果为降级模式"
    elif cache_hit:
        status_text = "已完成，本次命中缓存"
    else:
        status_text = "已完成"
    summary_parts = [status_text]
    if latency_ms > 0:
        summary_parts.append(f"{latency_ms}ms")
    if degraded_reason:
        summary_parts.append(degraded_reason)
    return {
        "run_id": run_id,
        "status": status,
        "status_text": status_text,
        "summary": " · ".join(summary_parts),
        "latency_ms": latency_ms,
        "cache_hit": cache_hit,
        "degraded": degraded,
        "degraded_reason": degraded_reason,
        "retryable": status in {"failed", "rate_limited"} or degraded,
        "retry_after": 60 if status == "rate_limited" else 0,
        "endpoint": _string(observability.get("endpoint")),
    }


def _build_context_sources(feature_type: str, payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    if feature_type == "study_coach":
        snapshot = _dict(payload.get("snapshot"))
        overview = _dict(snapshot.get("overview"))
        plan = _dict(_dict(_dict(snapshot.get("today_task")).get("plan")))
        wrong_words = _list(snapshot.get("priority_wrong_words"))
        profile_memory = _dict(payload.get("profile_memory"))
        return [
            {
                "key": "plan",
                "label": "当前计划",
                "status": "ready" if plan else "empty",
                "detail": _string(_dict(plan.get("book")).get("name"), "未创建学习计划"),
            },
            {
                "key": "learned_words",
                "label": "已学词汇",
                "status": "ready",
                "detail": f"{int(overview.get('learned_word_count') or 0)} 个",
            },
            {
                "key": "wrong_words",
                "label": "错词本",
                "status": "ready",
                "detail": f"{len(wrong_words)} 个高优先词",
            },
            {
                "key": "trend",
                "label": "近期趋势",
                "status": "ready",
                "detail": "最近 7 天学习快照",
            },
            {
                "key": "profile_memory",
                "label": "学习画像",
                "status": "ready" if profile_memory else "empty",
                "detail": _string(profile_memory.get("profile_summary"), "尚未生成画像"),
            },
            {
                "key": "personalized_rag",
                "label": "个性化 RAG",
                "status": "ready" if profile_memory else "pending",
                "detail": "基于计划、错词和画像补充个性化上下文",
            },
        ]
    if feature_type == "plan_replan":
        context_bundle = _dict(payload.get("context_bundle"))
        return [
            {
                "key": "plan",
                "label": "当前计划",
                "status": "ready",
                "detail": _string(_dict(_dict(_dict(context_bundle.get("plan_ctx")).get("plan")).get("book")).get("name"), "未读取到计划"),
            },
            {
                "key": "today_task",
                "label": "今日任务",
                "status": "ready",
                "detail": "读取今日新词和复习压力",
            },
            {
                "key": "wrong_words",
                "label": "错词本",
                "status": "ready",
                "detail": f"{len(_list(_dict(context_bundle.get('wrong_words')).get('list')))} 条",
            },
            {
                "key": "rag",
                "label": "RAG 证据",
                "status": "ready",
                "detail": "structured + vector 召回已参与重规划",
            },
            {
                "key": "profile_memory",
                "label": "学习画像",
                "status": "ready" if _dict(payload.get("profile_memory")) else "empty",
                "detail": "最近偏好、弱项和重点词",
            },
        ]
    if feature_type == "word_tutor":
        snapshot = _dict(payload.get("snapshot"))
        word_detail = _dict(snapshot.get("word_detail"))
        return [
            {"key": "word", "label": "词条详情", "status": "ready", "detail": _string(word_detail.get("word"), "当前单词")},
            {"key": "example", "label": "例句上下文", "status": "ready", "detail": "例句和翻译已参与讲词"},
            {
                "key": "related_words",
                "label": "易混近义词",
                "status": "ready",
                "detail": f"{len(_list(word_detail.get('related_words')))} 条",
            },
        ]
    if feature_type == "wrong_words_review":
        snapshot = _dict(payload.get("snapshot"))
        return [
            {
                "key": "wrong_words",
                "label": "错词本",
                "status": "ready",
                "detail": f"{int(snapshot.get('total_wrong_words') or 0)} 个活跃错词",
            },
            {
                "key": "adaptive",
                "label": "学习快照",
                "status": "ready",
                "detail": "当前复习压力和重点错因已参与复盘",
            },
        ]
    if feature_type == "grammar_tutor":
        retrieval = _dict(payload.get("retrieval"))
        return [
            {"key": "sentence", "label": "当前句子", "status": "ready", "detail": _string(payload.get("sentence"), "已读取句子")},
            {
                "key": "grammar_points",
                "label": "相关语法点",
                "status": "ready",
                "detail": f"{len(_list(retrieval.get('related_points')))} 条",
            },
            {
                "key": "similar_sentences",
                "label": "相似例句",
                "status": "ready",
                "detail": f"{len(_list(retrieval.get('similar_sentences')))} 条",
            },
        ]
    return []


def _build_feature_runtime(feature_type: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    ai_strategy = _dict(payload.get("ai_strategy"))
    runtime = _dict(payload.get("runtime"))
    retrieval_strategy = _dict(payload.get("retrieval_strategy"))
    runtime_stack = _dict(payload.get("runtime_stack"))
    tool_trace = _list(payload.get("tool_trace"))
    langchain_trace = _list(payload.get("langchain_trace"))

    generation_mode = "fallback"
    if langchain_trace:
        generation_mode = "langchain_explicit"
    elif ai_strategy.get("ai_enabled"):
        generation_mode = "direct"

    orchestrator = ai_strategy.get("engine") or ("langgraph" if runtime.get("langgraph_available") else "pipeline")
    primary_path = "fallback"
    if langchain_trace:
        primary_path = "langchain_explicit"
    elif orchestrator == "langgraph":
        primary_path = "langgraph"
    elif ai_strategy.get("ai_enabled"):
        primary_path = "direct"

    tags: List[str] = [primary_path]
    if runtime.get("langgraph_available") and "langgraph" not in tags:
        tags.append("langgraph")
    if tool_trace and "mcp_tool" not in tags:
        tags.append("mcp_tool")
    if retrieval_strategy.get("backend") == "chroma" or retrieval_strategy.get("external_vector_db"):
        tags.append("chroma")
    if retrieval_strategy.get("personalized_enabled") or retrieval_strategy.get("personalized_hits"):
        tags.append("personalized_rag")
    if not ai_strategy.get("ai_enabled") and "fallback" not in tags:
        tags.append("fallback")

    stack_name = runtime_stack.get("stack_name") or f"{feature_type}_runtime"
    return {
        "feature_type": feature_type,
        "path": primary_path,
        "orchestrator": orchestrator,
        "generation_mode": generation_mode,
        "model_name": _string(ai_strategy.get("model_name")),
        "prompt_version": _string(ai_strategy.get("prompt_version")),
        "langgraph_enabled": bool(runtime.get("langgraph_available")),
        "langchain_explicit": bool(langchain_trace),
        "mcp_tooling": bool(tool_trace),
        "chroma_enabled": bool(retrieval_strategy.get("backend") == "chroma" or retrieval_strategy.get("external_vector_db")),
        "personalized_rag": bool(retrieval_strategy.get("personalized_enabled") or retrieval_strategy.get("personalized_hits")),
        "fallback": primary_path == "fallback",
        "stack_name": stack_name,
        "tags": tags,
        "context_sources": _build_context_sources(feature_type, payload),
    }


def _build_runtime_stack(feature_type: str, payload: Dict[str, Any], feature_runtime: Dict[str, Any]) -> Dict[str, Any]:
    runtime = _dict(payload.get("runtime"))
    current = _dict(payload.get("runtime_stack"))
    stack = dict(current)
    stack.setdefault("stack_name", current.get("stack_name") or f"{feature_type}_runtime")
    stack["feature_type"] = feature_type
    stack["path"] = feature_runtime.get("path")
    stack["orchestrator"] = feature_runtime.get("orchestrator")
    stack["generation_mode"] = feature_runtime.get("generation_mode")
    stack["tags"] = feature_runtime.get("tags", [])
    stack["langgraph"] = bool(runtime.get("langgraph_available"))
    stack["langchain_explicit"] = bool(_list(payload.get("langchain_trace")))
    stack["mcp_tooling"] = bool(_list(payload.get("tool_trace")))
    stack["fallback"] = bool(feature_runtime.get("fallback"))
    return stack


def _headline_and_summary(feature_type: str, payload: Dict[str, Any]) -> Dict[str, str]:
    if feature_type == "study_coach":
        coach = _dict(payload.get("coach"))
        return {
            "headline": _string(coach.get("headline"), "AI 学习教练建议"),
            "summary": _string(coach.get("today_strategy") or coach.get("coach_tip"), "已结合你的学习状态生成建议"),
        }
    if feature_type == "word_tutor":
        word = _string(_dict(_dict(payload.get("snapshot")).get("word_detail")).get("word"), "当前单词")
        tutor = _dict(payload.get("tutor"))
        return {
            "headline": _string(payload.get("headline"), f"AI 讲词：{word}"),
            "summary": _string(tutor.get("simple_explanation_cn") or tutor.get("usage_tip"), "已生成记忆和用法提示"),
        }
    if feature_type == "wrong_words_review":
        review = _dict(payload.get("review"))
        return {
            "headline": _string(review.get("headline"), "AI 错词复盘"),
            "summary": _string(review.get("summary") or review.get("coach_line"), "已整理错词模式和回收建议"),
        }
    if feature_type == "grammar_tutor":
        tutor = _dict(payload.get("tutor"))
        if tutor:
            return {
                "headline": _string(payload.get("headline"), "AI 语法讲解"),
                "summary": _string(tutor.get("explanation_cn") or tutor.get("coach_tip"), "已生成句子讲解"),
            }
        return {
            "headline": _string(payload.get("headline"), "AI 语法问答"),
            "summary": _string(payload.get("answer"), "已生成语法问答结果"),
        }
    if feature_type == "writing_correct":
        result = _dict(payload.get("result"))
        return {
            "headline": _string(payload.get("headline"), "AI 写作批改"),
            "summary": _string(result.get("overall_feedback"), "已完成写作批改"),
        }
    if feature_type == "writing_prompt":
        result = _dict(payload.get("result"))
        return {
            "headline": _string(result.get("title"), "AI 写作题目生成"),
            "summary": _string(result.get("prompt"), "已生成写作题目和提纲"),
        }
    if feature_type == "translation_evaluate":
        result = _dict(payload.get("result"))
        return {
            "headline": _string(payload.get("headline"), "AI 翻译训练"),
            "summary": _string(result.get("feedback"), "已生成翻译反馈"),
        }
    if feature_type == "scenario_dialogue":
        result = _dict(payload.get("result"))
        return {
            "headline": _string(result.get("scenario_label"), "AI 情景对话"),
            "summary": _string(result.get("assistant_reply"), "已生成下一轮对话"),
        }
    if feature_type == "grammar_guide":
        return {
            "headline": _string(payload.get("headline"), "AI 语法导学"),
            "summary": _string(payload.get("summary"), "已生成语法导学建议"),
        }
    if feature_type == "rag_search":
        answer = _dict(payload.get("answer"))
        return {
            "headline": _string(payload.get("headline"), "AI 检索问答"),
            "summary": _string(answer.get("summary"), "已生成 grounded answer"),
        }
    if feature_type == "vector_rag":
        answer = _dict(payload.get("answer"))
        return {
            "headline": _string(payload.get("headline"), "AI 向量 RAG"),
            "summary": _string(_dict(payload.get("answer_brief")).get("summary") or answer.get("summary"), "已生成向量检索结果"),
        }
    return {
        "headline": _string(payload.get("headline")),
        "summary": _string(payload.get("summary")),
    }


def normalize_feature_contract(feature_type: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(payload, dict):
        return payload
    headline_summary = _headline_and_summary(feature_type, payload)
    payload["headline"] = headline_summary["headline"]
    payload["summary"] = headline_summary["summary"]
    payload.setdefault("langchain_trace", [])
    feature_runtime = _build_feature_runtime(feature_type, payload)
    payload["feature_runtime"] = feature_runtime
    payload["runtime_stack"] = _build_runtime_stack(feature_type, payload, feature_runtime)
    payload["context_sources"] = feature_runtime.get("context_sources", [])
    payload["runtime_summary"] = _build_runtime_summary(payload, feature_runtime)
    if payload.get("run_id") and not payload["runtime_summary"].get("run_id"):
        payload["runtime_summary"]["run_id"] = _string(payload.get("run_id"))
    return payload
