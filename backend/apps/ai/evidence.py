import os
from typing import Any, Dict, List


DEFAULT_PROMPT_VERSIONS = {
    "study_coach": "study_coach_v1",
    "word_tutor": "vocab_tutor_v1",
    "wrong_words_review": "wrong_word_review_v1",
    "grammar_tutor": "grammar_tutor_v1",
    "writing_correct": "assistant_v1",
    "writing_prompt": "assistant_v1",
    "translation_evaluate": "assistant_v1",
    "rag_search": "assistant_v1",
    "vector_rag": "assistant_v1",
    "rag_recall_eval": "assistant_v1",
    "scenario_dialogue": "assistant_v1",
    "grammar_guide": "assistant_v1",
    "multi_agent_brief": "assistant_v2_architecture",
    "study_report": "report_v1",
    "plan_replan": "plan_replan_v2_multi_agent",
    "retrieval_orchestrator": "retrieval_orchestrator_v2_multi_agent",
}


def _trim_text(value: Any, limit: int = 120) -> str:
    text = str(value or "").strip()
    if len(text) <= limit:
        return text
    return f"{text[: limit - 1]}..."


def _build_runtime_summary(feature_type: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    ai_strategy = payload.get("ai_strategy") or {}
    runtime = payload.get("runtime") or {}
    observability = payload.get("ai_observability") or {}
    langchain_trace = payload.get("langchain_trace") or []
    multi_agent = payload.get("multi_agent") or {}
    model_name = (
        observability.get("model_name")
        or ai_strategy.get("model_name")
        or os.getenv("AI_MODEL", "").strip()
    )
    prompt_version = (
        observability.get("prompt_version")
        or ai_strategy.get("prompt_version")
        or DEFAULT_PROMPT_VERSIONS.get(feature_type, "")
    )
    return {
        "engine": ai_strategy.get("engine") or runtime.get("preferred_runtime") or "pipeline",
        "model_name": model_name,
        "prompt_version": prompt_version,
        "ai_enabled": bool(ai_strategy.get("ai_enabled", runtime.get("ai_model_env_ready", False))),
        "rag_enabled": bool(ai_strategy.get("rag_enabled")) if "rag_enabled" in ai_strategy else None,
        "langgraph_available": bool(runtime.get("langgraph_available", False)),
        "mcp_available": bool(runtime.get("mcp_available", False)),
        "cache_hit": observability.get("cache_hit"),
        "latency_ms": observability.get("latency_ms"),
    }


def _build_observability(payload: Dict[str, Any], runtime_summary: Dict[str, Any]) -> Dict[str, Any]:
    observability = dict(payload.get("ai_observability") or {})
    result = {
        "engine": runtime_summary.get("engine", ""),
        "model_name": runtime_summary.get("model_name", ""),
        "prompt_version": runtime_summary.get("prompt_version", ""),
        "run_id": observability.get("run_id", ""),
    }
    for field in ("cache_hit", "cache_key", "latency_ms", "endpoint", "status", "cached_at"):
        if field in observability:
            result[field] = observability.get(field)
    rate_limit = observability.get("rate_limit") or {}
    if rate_limit:
        result["rate_limit_remaining"] = rate_limit.get("remaining")
        result["rate_limit_limit"] = rate_limit.get("limit")
    return result


def _build_trace_timeline(feature_type: str, payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    timeline: List[Dict[str, Any]] = []
    agent_flow = payload.get("agent_flow") or {}
    workflow = agent_flow.get("steps") or []
    tool_trace = payload.get("tool_trace") or []
    langchain_trace = payload.get("langchain_trace") or []
    multi_agent = payload.get("multi_agent") or {}
    observability = payload.get("ai_observability") or {}

    for index, item in enumerate(workflow):
        timeline.append(
            _trace_item(
                step=item.get("name", f"step-{index + 1}"),
                phase="workflow",
                detail=item.get("detail", ""),
                status="success",
            )
        )

    for item in tool_trace:
        timeline.append(
            _trace_item(
                step=item.get("tool_name", "tool"),
                phase="tool_call",
                detail=item.get("summary", ""),
                status="success",
                tool_name=item.get("tool_name", ""),
                meta={"args": item.get("args", {})},
            )
        )

    for item in (langchain_trace or [])[:12]:
        timeline.append(
            _trace_item(
                step=item.get("name", "langchain"),
                phase=item.get("phase", "langchain"),
                detail=item.get("detail", ""),
                status=item.get("status", "success"),
                meta={
                    "latency_ms": item.get("latency_ms", 0),
                    **(item.get("meta") or {}),
                },
            )
        )

    for item in (multi_agent.get("handoffs") or []):
        timeline.append(
            _trace_item(
                step=f"{item.get('from', '')} -> {item.get('to', '')}",
                phase="multi_agent",
                detail=item.get("reason", ""),
                status="success",
            )
        )

    retrieval = payload.get("retrieval_strategy") or {}
    if retrieval:
        timeline.append(
            _trace_item(
                step="retrieval_strategy",
                phase="retrieval",
                detail=f"{retrieval.get('type', '')} / {retrieval.get('version', '')}",
                status="success",
                meta=retrieval,
            )
        )

    profile_memory = payload.get("profile_memory") or {}
    if profile_memory:
        timeline.append(
            _trace_item(
                step="profile_memory",
                phase="memory",
                detail=profile_memory.get("profile_summary", "") or "AI long-term learner profile loaded.",
                status="success",
                meta={"preferred_modes": profile_memory.get("preferred_modes", [])},
            )
        )

    if observability:
        timeline.append(
            _trace_item(
                step="response",
                phase="output",
                detail=f"latency={observability.get('latency_ms', 0)}ms cache_hit={bool(observability.get('cache_hit'))}",
                status=observability.get("status", "success"),
                meta={
                    "endpoint": observability.get("endpoint", ""),
                    "model_name": observability.get("model_name", ""),
                    "prompt_version": observability.get("prompt_version", ""),
                },
            )
        )

    if feature_type == "rag_recall_eval":
        vector = payload.get("vector_recall") or {}
        structured = payload.get("structured_recall") or {}
        timeline.append(
            _trace_item(
                step="compare_recall",
                phase="evaluation",
                detail=f"structured={structured.get('coverage_rate', 0)}%, vector={vector.get('coverage_rate', 0)}%",
                status="success",
            )
        )

    return timeline


def _hit(source_type: str, title: str, reason: str = "", preview: str = "", score: Any = None) -> Dict[str, Any]:
    item = {
        "source_type": source_type,
        "title": _trim_text(title, 80),
        "reason": _trim_text(reason, 120),
        "preview": _trim_text(preview, 140),
    }
    if score not in (None, ""):
        item["score"] = score
    return item


def _tool(name: str, detail: str, args: Dict[str, Any] | None = None) -> Dict[str, Any]:
    return {
        "name": name,
        "detail": _trim_text(detail, 140),
        "args": args or {},
    }


def _trace_item(step: str, phase: str, detail: str, status: str = "success", tool_name: str = "", meta: Dict[str, Any] | None = None) -> Dict[str, Any]:
    item = {
        "step": _trim_text(step, 60),
        "phase": phase,
        "detail": _trim_text(detail, 180),
        "status": status,
    }
    if tool_name:
        item["tool_name"] = tool_name
    if meta:
        item["meta"] = meta
    return item


def _hits_from_learning_context(context: Dict[str, Any], limit: int = 5) -> List[Dict[str, Any]]:
    hits: List[Dict[str, Any]] = []
    for item in (context.get("words") or [])[:limit]:
        hits.append(
            _hit(
                "word",
                item.get("word", ""),
                item.get("reason", "") or item.get("meaning_cn", ""),
                item.get("example_sentence", ""),
            )
        )
    for item in (context.get("grammar_points") or [])[:limit]:
        hits.append(
            _hit(
                "grammar_point",
                item.get("title", ""),
                item.get("learning_tip", "") or item.get("description", ""),
                item.get("description", ""),
            )
        )
    for item in (context.get("sentences") or [])[:limit]:
        hits.append(
            _hit(
                "grammar_sentence",
                item.get("sentence", ""),
                item.get("point_title", "") or item.get("summary", ""),
                item.get("translation_cn", ""),
            )
        )
    return hits[:limit]


def _hits_from_vector_documents(documents: List[Dict[str, Any]], limit: int = 5) -> List[Dict[str, Any]]:
    hits = []
    for item in (documents or [])[:limit]:
        metadata = item.get("metadata", {}) or {}
        reason_parts = []
        if metadata.get("chunk_kind"):
            reason_parts.append(f"chunk={metadata.get('chunk_kind')}")
        if metadata.get("point_title"):
            reason_parts.append(str(metadata.get("point_title")))
        if metadata.get("book_name"):
            reason_parts.append(str(metadata.get("book_name")))
        hits.append(
            _hit(
                item.get("source_type", "document"),
                item.get("title", ""),
                " / ".join(reason_parts) or item.get("match_reason", "") or item.get("content_preview", ""),
                "；".join(item.get("highlights") or []) or item.get("content_preview", "") or item.get("content", ""),
                item.get("score"),
            )
        )
    return hits


def _hits_from_word_snapshot(snapshot: Dict[str, Any]) -> List[Dict[str, Any]]:
    word_detail = snapshot.get("word_detail") or {}
    hits = []
    for item in (word_detail.get("related_words") or [])[:3]:
        hits.append(
            _hit(
                "related_word",
                item.get("word", ""),
                item.get("reason", "") or item.get("meaning_cn", ""),
                item.get("meaning_cn", ""),
            )
        )
    for item in (word_detail.get("examples_preview") or [])[:2]:
        hits.append(
            _hit(
                "example_sentence",
                item.get("sentence", ""),
                "讲词时参考的例句",
                item.get("translation", ""),
            )
        )
    return hits[:5]


def _hits_from_study_snapshot(snapshot: Dict[str, Any]) -> List[Dict[str, Any]]:
    hits = []
    for item in (snapshot.get("priority_wrong_words") or [])[:3]:
        hits.append(
            _hit(
                "wrong_word",
                item.get("word", ""),
                item.get("reason", "") or item.get("meaning_cn", ""),
                item.get("meaning_cn", ""),
            )
        )
    for item in (snapshot.get("due_review_words") or [])[:2]:
        hits.append(
            _hit(
                "due_review",
                item.get("word", ""),
                f"wrong_count={item.get('wrong_count', 0)} mastery={item.get('mastery_level', 0)}",
                item.get("meaning_cn", ""),
            )
        )
    return hits[:5]


def _hits_from_wrong_words_snapshot(snapshot: Dict[str, Any]) -> List[Dict[str, Any]]:
    hits = []
    for item in (snapshot.get("priority_words") or [])[:4]:
        hits.append(
            _hit(
                "wrong_word",
                item.get("word", ""),
                item.get("reason", "") or item.get("meaning_cn", ""),
                item.get("meaning_cn", ""),
            )
        )
    return hits


def _hits_from_recommended_points(points: List[Dict[str, Any]], limit: int = 5) -> List[Dict[str, Any]]:
    hits = []
    for item in (points or [])[:limit]:
        hits.append(
            _hit(
                "grammar_point",
                item.get("title", ""),
                item.get("reason", "") or item.get("learning_tip", ""),
                item.get("sample_sentence", "") or item.get("learning_tip", ""),
            )
        )
    return hits


def _hits_from_report_snapshot(snapshot: Dict[str, Any]) -> List[Dict[str, Any]]:
    coach_bundle = snapshot.get("coach_bundle") or {}
    return _hits_from_study_snapshot(coach_bundle)


def _hits_from_rag_recall(payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    hits = []
    structured_hits = ((payload.get("structured_recall") or {}).get("top_hits") or [])[:3]
    vector_hits = ((payload.get("vector_recall") or {}).get("top_hits") or [])[:3]
    for item in structured_hits:
        hits.append(
            _hit(
                item.get("source_type", "structured"),
                item.get("title", ""),
                "structured recall",
                item.get("text", ""),
            )
        )
    for item in vector_hits:
        hits.append(
            _hit(
                item.get("source_type", "vector"),
                item.get("title", ""),
                "vector recall",
                "",
                item.get("score"),
            )
        )
    return hits[:6]


def _feature_definition(feature_type: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    if feature_type == "study_coach":
        snapshot = payload.get("snapshot") or {}
        return {
            "summary": "基于当前计划、今日任务、错词和学习趋势生成教练建议。",
            "workflow": {
                "label": "学习教练工作流",
                "steps": [
                    {"name": "读取学习快照", "detail": "聚合当前计划、今日任务、复习压力和 7 天趋势。"},
                    {"name": "识别高风险词", "detail": "优先关注高频错词和到期复习词。"},
                    {"name": "输出今日顺序", "detail": "生成今天更适合的新词/复习节奏和执行顺序。"},
                ],
            },
            "tools_used": [
                _tool("get_user_plan", "读取当前计划"),
                _tool("get_today_task", "读取今日任务与 adaptive 建议"),
                _tool("get_due_reviews", "读取到期复习词"),
                _tool("get_wrong_words", "读取当前错词本"),
                _tool("get_study_snapshot", "读取最近 7 天学习趋势"),
            ],
            "retrieval_hits": _hits_from_study_snapshot(snapshot),
        }
    if feature_type == "word_tutor":
        snapshot = payload.get("snapshot") or {}
        return {
            "summary": "基于单词详情、例句、近义词和你的学习状态生成讲词结果。",
            "workflow": {
                "label": "讲词工作流",
                "steps": [
                    {"name": "读取单词详情", "detail": "读取词义、词性、例句和学习轨迹。"},
                    {"name": "关联近义词与例句", "detail": "补充易混词、近义词与例句来源。"},
                    {"name": "生成讲词与微练习", "detail": "输出记忆提示、使用提醒和小练习。"},
                ],
            },
            "tools_used": [
                _tool("get_word_detail", "读取当前单词详情"),
            ],
            "retrieval_hits": _hits_from_word_snapshot(snapshot),
        }
    if feature_type == "wrong_words_review":
        snapshot = payload.get("snapshot") or {}
        return {
            "summary": "基于错词本和 adaptive 快照整理错词模式与回收动作。",
            "workflow": {
                "label": "错词复盘工作流",
                "steps": [
                    {"name": "读取错词本", "detail": "读取活跃错词、错词次数与最近出错情况。"},
                    {"name": "统计错误模式", "detail": "按词性和高频错词聚合主要风险。"},
                    {"name": "输出回收动作", "detail": "给出优先词和执行步骤。"},
                ],
            },
            "tools_used": [
                _tool("get_wrong_words", "读取当前错词本"),
                _tool("get_study_snapshot", "读取 adaptive 学习快照"),
            ],
            "retrieval_hits": _hits_from_wrong_words_snapshot(snapshot),
        }
    if feature_type == "grammar_guide":
        return {
            "summary": "基于学习状态和弱点输出本周语法导学建议。",
            "workflow": {
                "label": "语法导学工作流",
                "steps": [
                    {"name": "读取学习状态", "detail": "统计近期学习、错词模式和已学词。"},
                    {"name": "推荐语法专题", "detail": "筛选更贴近当前阶段的语法点。"},
                    {"name": "输出导学顺序", "detail": "给出本周优先语法点和示例句。"},
                ],
            },
            "tools_used": [
                _tool("get_study_snapshot", "读取最近学习状态"),
                _tool("search_grammar_points", "检索可用语法点"),
            ],
            "retrieval_hits": _hits_from_recommended_points(payload.get("recommended_points") or []),
        }
    if feature_type in {"rag_search", "writing_correct", "writing_prompt", "translation_evaluate", "scenario_dialogue"}:
        return {
            "summary": "基于项目内词库、语法点和例句做检索增强，并结合输入生成回答。",
            "workflow": {
                "label": "检索增强工作流",
                "steps": [
                    {"name": "解析输入", "detail": "提取关键词、学习主题或场景。"},
                    {"name": "检索学习上下文", "detail": "从词库、语法点和句库中召回相关资料。"},
                    {"name": "生成回答", "detail": "基于命中的上下文输出结构化结果。"},
                ],
            },
            "tools_used": [
                _tool("rag_search", "执行结构化检索问答"),
            ],
            "retrieval_hits": _hits_from_learning_context(payload.get("retrieval") or {}),
        }
    if feature_type == "vector_rag":
        query_intent = (payload.get("advanced_debug") or {}).get("query_intent") or {}
        return {
            "summary": "优先使用 Chroma 知识库检索命中的知识 chunk，并支持 hybrid 召回、命中高亮和结果解释；若不可用则回退到本地轻量向量检索。",
            "workflow": {
                "label": "向量 RAG 工作流",
                "steps": [
                    {"name": "构建知识 chunk", "detail": "知识库由词条、词条例句、语法点和语法句子组成。"},
                    {"name": "向量 / hybrid 检索", "detail": "优先在 Chroma 中检索相似 chunk，也支持结构化检索与向量召回融合。"},
                    {"name": "生成 grounded 回答", "detail": "仅基于召回 chunk 输出答案。"},
                ],
            },
            "tools_used": [
                _tool("vector_rag_search", "执行 Chroma / 本地轻量向量召回"),
            ],
            "retrieval_hits": _hits_from_vector_documents(payload.get("documents") or []),
            "query_intent": query_intent,
        }
    if feature_type == "rag_recall_eval":
        return {
            "summary": "对结构化检索和轻量向量检索的召回覆盖率进行对比评估。",
            "workflow": {
                "label": "RAG 召回评测流",
                "steps": [
                    {"name": "设定评测关键词", "detail": "读取问题、期望关键词和偏好资料类型。"},
                    {"name": "并行评估召回", "detail": "比较 structured recall 和 vector recall 的命中。"},
                    {"name": "输出诊断", "detail": "给出覆盖率与更优策略建议。"},
                ],
            },
            "tools_used": [
                _tool("evaluate_rag_recall", "评估结构化与向量召回表现"),
            ],
            "retrieval_hits": _hits_from_rag_recall(payload),
        }
    if feature_type == "multi_agent_brief":
        hits = []
        for item in (payload.get("agents") or [])[:4]:
            hits.append(_hit("agent_role", item.get("name", ""), item.get("focus", ""), item.get("action", "")))
        return {
            "summary": "展示当前项目里的多 Agent 角色分工，以及两条真实可运行的协作链路。",
            "workflow": {
                "label": "多 Agent 架构总览",
                "steps": [
                    {"name": "planner", "detail": "负责问题分析与策略起草。"},
                    {"name": "retriever", "detail": "负责调用项目数据与 RAG 证据。"},
                    {"name": "coach", "detail": "负责面向学习者的表达和建议。"},
                    {"name": "supervisor", "detail": "负责最终整合与路径选择。"},
                ],
            },
            "tools_used": [
                _tool("get_multi_agent_brief", "生成多角色学习简报"),
            ],
            "retrieval_hits": hits[:5],
        }
    if feature_type == "study_report":
        snapshot = payload.get("source_snapshot") or {}
        return {
            "summary": "聚合学习、复习、语法和错词数据生成阶段报告，并支持历史对比。",
            "workflow": {
                "label": "学习报告工作流",
                "steps": [
                    {"name": "汇总阶段数据", "detail": "读取阶段内学习、复习、语法和错词指标。"},
                    {"name": "生成报告", "detail": "整理亮点、风险和下一步计划。"},
                    {"name": "对比历史", "detail": "可选对比上一期报告变化。"},
                ],
            },
            "tools_used": [
                _tool("get_study_snapshot", "读取阶段学习快照"),
                _tool("get_learning_reports", "读取历史报告"),
            ],
            "retrieval_hits": _hits_from_report_snapshot(snapshot),
        }
    if feature_type == "plan_replan":
        tool_trace = payload.get("tool_trace") or []
        tools_used = []
        for item in tool_trace:
            tools_used.append(_tool(item.get("tool_name", ""), item.get("summary", ""), item.get("args", {})))
        for item in (payload.get("multi_agent", {}).get("roles") or []):
            tools_used.append(_tool(item.get("name", ""), item.get("responsibility", ""), {}))
        return {
            "summary": "以 planner / retriever / coach / supervisor 四角色协作方式，读取计划与趋势，再结合 RAG 资料输出新的学习计划建议。",
            "workflow": {
                "label": "AI 重规划学习计划 Multi-Agent",
                "steps": payload.get("agent_flow", {}).get("steps", []),
            },
            "tools_used": tools_used,
            "retrieval_hits": _hits_from_vector_documents(
                ((payload.get("knowledge") or {}).get("vector_rag") or {}).get("documents") or []
            ) or _hits_from_learning_context(
                ((payload.get("knowledge") or {}).get("structured_rag") or {}).get("retrieval") or {}
            ),
        }
    if feature_type == "retrieval_orchestrator":
        selection = payload.get("selection") or {}
        hybrid_docs = ((payload.get("knowledge") or {}).get("hybrid_rag") or {}).get("documents") or []
        structured_ctx = ((payload.get("knowledge") or {}).get("structured_rag") or {}).get("retrieval") or {}
        tools_used = [_tool(item.get("tool_name", ""), item.get("summary", ""), item.get("args", {})) for item in (payload.get("tool_trace") or [])]
        for item in (payload.get("multi_agent", {}).get("roles") or []):
            tools_used.append(_tool(item.get("name", ""), item.get("responsibility", ""), {}))
        return {
            "summary": "以 planner / retriever / coach / supervisor 四角色协作方式，分析查询并执行结构化 RAG 与 Hybrid RAG，最后选择主回答路径。",
            "workflow": {
                "label": "LangGraph 检索编排 Multi-Agent",
                "steps": payload.get("agent_flow", {}).get("steps", []),
            },
            "tools_used": tools_used,
            "retrieval_hits": _hits_from_vector_documents(hybrid_docs) or _hits_from_learning_context(structured_ctx),
        }
    return {
        "summary": "当前 AI 结果包含模型运行信息和相关上下文。",
        "workflow": {
            "label": "AI 结果生成流程",
            "steps": [
                {"name": "读取上下文", "detail": "读取与当前问题相关的数据。"},
                {"name": "生成结果", "detail": "结合上下文输出结构化回答。"},
            ],
        },
        "tools_used": [],
        "retrieval_hits": [],
    }


def attach_feature_evidence(feature_type: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(payload, dict):
        return payload
    definition = _feature_definition(feature_type, payload)
    runtime_summary = _build_runtime_summary(feature_type, payload)
    payload["evidence"] = {
        "feature_type": feature_type,
        "summary": definition.get("summary", ""),
        "workflow": definition.get("workflow", {}),
        "tools_used": definition.get("tools_used", []),
        "retrieval_hits": definition.get("retrieval_hits", []),
        "trace_timeline": _build_trace_timeline(feature_type, payload),
        "observability": _build_observability(payload, runtime_summary),
    }
    return payload
