from __future__ import annotations

from time import monotonic
from typing import Any, Dict

from .agent_contracts import get_agent_contract
from .agent_runtime import (
    AgentRunResult,
    AgentStepResult,
    complete_run,
    create_artifact,
    ensure_feature_runtime_payload,
    fail_run,
    finish_step,
    start_step,
)
from .critic import run_feature_critic
from .graphs.grammar_tutor import build_grammar_tutor_answer, build_grammar_tutor_detail
from .graphs.plan_replanner import build_plan_replan_detail, build_fast_plan_replan_detail
from .graphs.retrieval_orchestrator import build_retrieval_orchestrator_detail
from .graphs.study_coach import build_study_coach_detail
from .graphs.vocab_tutor import build_word_tutor_detail
from .graphs.wrong_word_review import build_wrong_words_review_detail
from .learning_assistant import run_rag_search, run_vector_rag_search
from .learning_assistant import build_grammar_guide, correct_writing, evaluate_translation, generate_writing_prompt, run_scenario_dialogue
from .learning_reports import generate_study_report
from .mcp.registry import execute_agent_safe_tool
from .models import AIAsyncRun, AIConversation, AIMessage
from .response_contracts import normalize_feature_contract
from .workflows import get_workflow_definition
from .observability import fit_model_char_value


def _listify(value: Any) -> list:
    return value if isinstance(value, list) else []


def _stringify(value: Any, default: str = "") -> str:
    text = str(value or "").strip()
    return text or default


def _dictify(value: Any) -> Dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _conversation_state(conversation: AIConversation | None) -> Dict[str, Any]:
    return dict((conversation.context if conversation else {}) or {})


def _normalize_conversation_context(
    conversation: AIConversation | None,
    *,
    feature_type: str,
    resolved_route: str,
    question: str,
    answer_payload: Dict[str, Any],
) -> Dict[str, Any]:
    context = _conversation_state(conversation)
    turn_count = int(context.get("turn_count") or 0) + 1
    assistant_summary = _stringify(
        (_dictify(answer_payload.get("answer_brief")).get("summary"))
        or (_dictify(answer_payload.get("answer")).get("summary"))
        or answer_payload.get("summary")
    )
    route_state = dict(_dictify(context.get("route_state")))
    if resolved_route == "grammar":
        route_state["grammar"] = {
            "last_sentence": answer_payload.get("sentence") or question,
            "last_question": answer_payload.get("question") or question,
        }
    elif resolved_route == "writing":
        route_state["writing"] = {
            "last_text": question,
        }
    elif resolved_route == "translation":
        route_state["translation"] = {
            "last_source_text": _dictify(answer_payload.get("result")).get("source_text") or context.get("last_source_text") or question,
            "last_user_translation": _dictify(answer_payload.get("result")).get("user_translation") or context.get("last_user_translation") or "",
        }
    elif resolved_route == "scenario":
        route_state["scenario"] = {
            "scenario": (_dictify(answer_payload.get("result")).get("scenario")) or context.get("scenario") or "daily",
            "last_user_message": question,
        }
    rolling_summary = assistant_summary or _stringify(question, "最近一轮会话")
    next_context = {
        **context,
        "source": "conversation_runtime",
        "feature_type": feature_type,
        "rolling_summary": rolling_summary,
        "last_route": resolved_route,
        "route_state": route_state,
        "memory_digest": {
            "last_question": question[:120],
            "last_answer_summary": assistant_summary[:180],
        },
        "turn_count": turn_count,
    }
    if resolved_route == "grammar":
        next_context["current_sentence"] = (answer_payload.get("sentence") or question)
    if resolved_route == "writing":
        next_context["last_text"] = question
    if resolved_route == "translation":
        next_context["last_source_text"] = route_state["translation"]["last_source_text"]
        next_context["last_user_translation"] = route_state["translation"]["last_user_translation"]
    if resolved_route == "scenario":
        next_context["scenario"] = route_state["scenario"]["scenario"]
    return next_context


def _assistant_content_from_answer_payload(answer_payload: Dict[str, Any]) -> str:
    return _stringify(
        (_dictify(answer_payload.get("answer_brief")).get("summary"))
        or (_dictify(answer_payload.get("answer")).get("summary"))
        or answer_payload.get("summary"),
        "已经生成本轮回答。",
    )


def _persist_conversation_messages(
    run: AIAsyncRun,
    *,
    question: str,
    final_payload: Dict[str, Any],
) -> None:
    conversation = run.conversation
    if not conversation:
        return
    user_message = (
        conversation.messages.filter(role="user", content=question, runtime_run__isnull=True)
        .order_by("-id")
        .first()
    )
    if user_message:
        user_message.runtime_run = run
        user_message.save(update_fields=["runtime_run", "updated_at"])

    assistant_payload = _dictify(final_payload.get("assistant_message"))
    answer_payload = _dictify(final_payload.get("answer")) or assistant_payload.get("payload") or {}
    AIMessage.objects.create(
        conversation=conversation,
        role="assistant",
        content=_assistant_content_from_answer_payload(answer_payload),
        payload=final_payload,
        runtime_run=run,
        prompt_version=fit_model_char_value(
            (_dictify(answer_payload.get("ai_strategy")).get("prompt_version"))
            or (_dictify(final_payload.get("ai_strategy")).get("prompt_version"))
            or "",
            AIMessage._meta.get_field("prompt_version").max_length,
        ),
        model_name=fit_model_char_value(
            (_dictify(answer_payload.get("ai_strategy")).get("model_name"))
            or (_dictify(final_payload.get("ai_strategy")).get("model_name"))
            or "",
            AIMessage._meta.get_field("model_name").max_length,
        ),
        latency_ms=int(
            (_dictify(answer_payload.get("ai_observability")).get("latency_ms"))
            or (_dictify(final_payload.get("ai_observability")).get("latency_ms"))
            or 0
        ),
    )


def _conversation_route_inputs(payload: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
    question = _stringify(payload.get("question"))
    feature_type = _stringify(payload.get("feature_type"), "rag")
    lowered = question.lower()
    if feature_type == "grammar":
        route = "grammar"
    elif feature_type == "writing":
        route = "writing"
    elif feature_type == "translation":
        route = "translation"
    elif feature_type == "scenario":
        route = "scenario"
    elif any(marker in lowered for marker in ["translate", "译文", "翻译", "原文：", "原文:"]):
        route = "translation"
    elif any(marker in lowered for marker in ["改作文", "润色", "写作", "essay", "paragraph"]):
        route = "writing"
    elif any(marker in lowered for marker in ["例句", "语法", "why", "who", "which", "什么意思", "为什么", "怎么用"]):
        route = "grammar"
    else:
        route = "rag"
    return {
        "resolved_route": route,
        "question": question,
        "context": context,
        "feature_type": feature_type,
    }


def _execute_conversation_route(run: AIAsyncRun, route: str, route_input: Dict[str, Any]) -> Dict[str, Any]:
    payload = dict(run.request_payload or {})
    question = _stringify(payload.get("question"))
    context = route_input.get("context") or {}
    if route == "grammar":
        current_sentence = _stringify(context.get("current_sentence"))
        if current_sentence and question and question != current_sentence:
            return build_grammar_tutor_answer(run.user, current_sentence, question)
        return build_grammar_tutor_detail(run.user, question)
    if route == "writing":
        return correct_writing(run.user, question, level=_stringify(context.get("level"), "cet4"))
    if route == "translation":
        lines = [item.strip() for item in question.splitlines() if item.strip()]
        source_text = ""
        user_translation = ""
        for line in lines:
            if line.startswith("原文：") or line.startswith("原文:"):
                source_text = line.split("：", 1)[-1] if "：" in line else line.split(":", 1)[-1]
            elif line.startswith("译文：") or line.startswith("译文:") or line.startswith("我的翻译：") or line.startswith("我的翻译:"):
                user_translation = line.split("：", 1)[-1] if "：" in line else line.split(":", 1)[-1]
        if not source_text and len(lines) >= 2:
            source_text = lines[0]
            user_translation = "\n".join(lines[1:])
        if not source_text:
            source_text = question
            user_translation = _stringify(context.get("last_user_translation"))
        return evaluate_translation(run.user, source_text, user_translation, direction="auto")
    if route == "scenario":
        return run_scenario_dialogue(
            run.user,
            _stringify(context.get("scenario"), "daily"),
            question,
            payload.get("conversation_id"),
        )
    return run_rag_search(question, int(payload.get("limit") or 6))


def _critic_step(
    run: AIAsyncRun,
    *,
    feature_type: str,
    payload: Dict[str, Any],
    require_evidence: bool = False,
    require_answer_brief: bool = False,
    max_repair_loops: int = 1,
) -> Dict[str, Any]:
    current_payload = payload
    started = monotonic()
    step = start_step(
        run,
        step_key=f"{feature_type}_critic",
        step_kind="critic",
        agent_name="critic",
        title="校验输出结构与依据",
        input_payload={
            "feature_type": feature_type,
            "require_evidence": require_evidence,
            "require_answer_brief": require_answer_brief,
        },
        metadata={"feature_type": feature_type, "max_repair_loops": max_repair_loops},
    )
    critic_result = None
    for _ in range(max(max_repair_loops, 1)):
        critic_result = run_feature_critic(
            feature_type=feature_type,
            payload=current_payload,
            require_evidence=require_evidence,
            require_answer_brief=require_answer_brief,
        )
        current_payload = critic_result.repaired_payload or current_payload
        if critic_result.ok:
            break
    critic_output = {
        "summary": critic_result.summary if critic_result else "critic 未执行",
        "issues": critic_result.issues if critic_result else [],
        "degraded": bool(critic_result and critic_result.degraded),
    }
    finish_step(
        step,
        AgentStepResult(
            output_payload=critic_output,
            summary=critic_output["summary"],
            artifacts=[
                {
                    "artifact_type": "critic_report",
                    "artifact_key": feature_type,
                    "title": "Critic 校验报告",
                    "payload": critic_output,
                    "summary": critic_output["summary"],
                }
            ],
        ),
        started,
    )
    return current_payload


def _build_plan_replan_fallback(run: AIAsyncRun, error_message: str) -> Dict[str, object]:
    payload = dict(run.request_payload or {})
    trend_days = int(payload.get("trend_days") or 7)
    fallback = build_fast_plan_replan_detail(run.user, trend_days)
    fallback["headline"] = fallback.get("headline") or "AI 已回退到保底自适应计划"
    fallback["summary"] = fallback.get("summary") or "完整 AI 生成暂时不可用，已返回保底自适应计划。"
    fallback["ai_strategy"] = {
        **(fallback.get("ai_strategy") or {}),
        "engine": "agent_runtime_fallback",
    }
    fallback["runtime_stack"] = {
        **(fallback.get("runtime_stack") or {}),
        "fallback": True,
    }
    fallback["degraded_notice"] = {
        "enabled": True,
        "reason": str(error_message),
        "message": "完整 AI 生成暂时失败，已自动回退到保底自适应计划。",
    }
    return normalize_feature_contract("plan_replan", fallback)


def execute_plan_replan_run(run: AIAsyncRun) -> AIAsyncRun:
    payload = dict(run.request_payload or {})
    trend_days = int(payload.get("trend_days") or 7)
    try:
        workflow = get_workflow_definition("plan_replan")
        build_started = monotonic()
        step = start_step(
            run,
            step_key="plan_replanner",
            step_kind="agent",
            agent_name="coordinator",
            title="生成 AI 自适应计划",
            input_payload=payload,
            metadata={"feature_type": "plan_replan", "workflow": workflow.planner, "roles": workflow.required_roles},
        )
        result_payload = build_plan_replan_detail(run.user, trend_days)
        result_payload = ensure_feature_runtime_payload("plan_replan", result_payload, run)
        result_payload = _critic_step(
            run,
            feature_type="plan_replan",
            payload=result_payload,
            max_repair_loops=get_agent_contract("critic").max_repair_loops,
        )
        finish_step(
            step,
            AgentStepResult(
                output_payload={
                    "headline": result_payload.get("headline", ""),
                    "summary": result_payload.get("summary", ""),
                    "multi_agent": result_payload.get("multi_agent", {}),
                    "agent_flow": result_payload.get("agent_flow", {}),
                },
                summary=result_payload.get("summary", ""),
                artifacts=[
                    {
                        "artifact_type": "plan_patch",
                        "artifact_key": "plan_patch",
                        "title": "今日计划调整",
                        "payload": result_payload.get("plan_patch", {}),
                        "summary": result_payload.get("summary", ""),
                    },
                    {
                        "artifact_type": "runtime_trace",
                        "artifact_key": "agent_flow",
                        "title": "执行轨迹",
                        "payload": result_payload.get("agent_flow", {}),
                        "summary": result_payload.get("headline", ""),
                    },
                ],
            ),
            build_started,
        )
        create_artifact(
            run,
            artifact_type="result_payload",
            artifact_key="final_result",
            title="最终结果",
            payload=result_payload,
            summary=result_payload.get("summary", ""),
        )
        return complete_run(
            run,
            AgentRunResult(
                feature_type="plan_replan",
                result_payload=result_payload,
                degraded=bool((result_payload.get("degraded_notice") or {}).get("enabled")),
                retryable=bool((result_payload.get("degraded_notice") or {}).get("enabled")),
                status_text="已完成",
            ),
            request_payload=payload,
        )
    except Exception as exc:
        fallback = _build_plan_replan_fallback(run, str(exc))
        try:
            create_artifact(
                run,
                artifact_type="error_fallback",
                artifact_key="plan_fallback",
                title="保底计划",
                payload=fallback,
                summary=str(exc),
            )
            return complete_run(
                run,
                AgentRunResult(
                    feature_type="plan_replan",
                    result_payload=ensure_feature_runtime_payload("plan_replan", fallback, run),
                    degraded=True,
                    retryable=True,
                    status_text="已完成，当前结果为降级模式",
                    error_message=str(exc),
                ),
                request_payload=payload,
            )
        except Exception:
            return fail_run(run, str(exc), request_payload=payload, retryable=True)


def _build_rag_search_fallback(run: AIAsyncRun, error_message: str) -> Dict[str, object]:
    payload = dict(run.request_payload or {})
    query = str(payload.get("query") or "").strip()
    limit = int(payload.get("limit") or 6)
    fallback = {
        "query": query,
        "headline": "AI 检索问答暂时回退",
        "summary": f"围绕“{query}”的检索主链路异常，已返回保底问答结果。",
        "answer": {
            "summary": "AI 检索问答暂时回退，已返回保底结果。",
            "grounded_points": ["请稍后重试，或换个更具体的问题。"],
            "next_questions": ["换个问法再试", "查看检索依据", "缩小问题范围"],
        },
        "answer_brief": {
            "summary": "AI 检索问答暂时回退，已返回保底结果。",
            "points": ["当前结果为降级模式。"],
            "next_questions": ["换个问法再试", "查看检索依据"],
        },
        "source_pills": [],
        "advanced_debug": {"fallback_reason": str(error_message)},
        "documents": [],
        "retrieval_explain": {
            "mode": "hybrid",
            "keywords": [],
            "normalized_query": query,
            "query_expansions": [],
            "using_chroma": False,
            "using_hybrid": True,
            "structured_context_available": False,
            "personalized_enabled": False,
            "personalized_hits": 0,
            "rerank_enabled": False,
            "multi_route_enabled": False,
            "why_this_result": ["主链路失败后已自动降级，先避免接口直接报错。"],
        },
        "structured_context": {},
        "retrieval_strategy": {
            "backend": "runtime_fallback",
            "retrieval_mode": "hybrid",
            "degraded": True,
            "limit": limit,
        },
        "degraded_notice": {
            "enabled": True,
            "reason": str(error_message),
            "message": "AI 检索问答暂时不可用，已返回保底结果。",
        },
        "ai_strategy": {
            "engine": "agent_runtime_fallback",
            "ai_enabled": False,
            "prompt_version": "assistant_v1",
            "model_name": "",
        },
        "runtime": {},
    }
    return normalize_feature_contract("rag_search", fallback)


def execute_rag_search_run(run: AIAsyncRun) -> AIAsyncRun:
    payload = dict(run.request_payload or {})
    query = str(payload.get("query") or "").strip()
    limit = int(payload.get("limit") or 6)
    try:
        workflow = get_workflow_definition("rag_search")
        build_started = monotonic()
        step = start_step(
            run,
            step_key="rag_search_retriever",
            step_kind="agent",
            agent_name="retriever",
            title="执行结构化检索",
            input_payload=payload,
            metadata={"feature_type": "rag_search", "workflow": workflow.planner, "roles": workflow.required_roles},
        )
        result_payload = run_rag_search(query, limit)
        result_payload = ensure_feature_runtime_payload("rag_search", result_payload, run)
        result_payload = _critic_step(
            run,
            feature_type="rag_search",
            payload=result_payload,
            require_evidence=True,
            require_answer_brief=True,
            max_repair_loops=get_agent_contract("critic").max_repair_loops,
        )
        finish_step(
            step,
            AgentStepResult(
                output_payload={
                    "headline": result_payload.get("headline", ""),
                    "summary": result_payload.get("summary", ""),
                    "answer_brief": result_payload.get("answer_brief", {}),
                    "retrieval_strategy": result_payload.get("retrieval_strategy", {}),
                },
                summary=result_payload.get("summary", ""),
                artifacts=[
                    {
                        "artifact_type": "retrieval_documents",
                        "artifact_key": "documents",
                        "title": "检索结果",
                        "payload": result_payload.get("documents", []),
                        "summary": result_payload.get("summary", ""),
                    }
                ],
            ),
            build_started,
        )
        create_artifact(
            run,
            artifact_type="result_payload",
            artifact_key="final_result",
            title="最终结果",
            payload=result_payload,
            summary=result_payload.get("summary", ""),
        )
        return complete_run(
            run,
            AgentRunResult(
                feature_type="rag_search",
                result_payload=result_payload,
                degraded=bool((result_payload.get("degraded_notice") or {}).get("enabled")),
                retryable=True,
                status_text="已完成",
            ),
            request_payload=payload,
        )
    except Exception as exc:
        fallback = _build_rag_search_fallback(run, str(exc))
        try:
            create_artifact(
                run,
                artifact_type="error_fallback",
                artifact_key="rag_search_fallback",
                title="检索问答保底结果",
                payload=fallback,
                summary=str(exc),
            )
            return complete_run(
                run,
                AgentRunResult(
                    feature_type="rag_search",
                    result_payload=ensure_feature_runtime_payload("rag_search", fallback, run),
                    degraded=True,
                    retryable=True,
                    status_text="已完成，当前结果为降级模式",
                    error_message=str(exc),
                ),
                request_payload=payload,
            )
        except Exception:
            return fail_run(run, str(exc), request_payload=payload, retryable=True)


def _build_vector_rag_fallback(run: AIAsyncRun, error_message: str) -> Dict[str, object]:
    payload = dict(run.request_payload or {})
    query = str(payload.get("query") or "").strip()
    retrieval_mode = str(payload.get("retrieval_mode") or "hybrid").strip() or "hybrid"
    fallback = {
        "query": query,
        "answer": {
            "summary": "向量 RAG 主链路异常，已返回保底问答结果。",
            "grounded_points": ["请稍后重试，或换一个更具体的问题。"],
            "next_questions": ["换个问法再试", "改问更具体的词义区别", "查看检索依据"],
        },
        "answer_brief": {
            "summary": "向量 RAG 主链路异常，已返回保底问答结果。",
            "points": ["当前结果为降级模式。"],
            "next_questions": ["换个问法再试", "查看检索依据"],
        },
        "source_pills": [],
        "advanced_debug": {"fallback_reason": str(error_message)},
        "documents": [],
        "retrieval_explain": {
            "mode": retrieval_mode,
            "keywords": [],
            "normalized_query": query,
            "query_expansions": [],
            "using_chroma": False,
            "using_hybrid": retrieval_mode == "hybrid",
            "structured_context_available": False,
            "personalized_enabled": False,
            "personalized_hits": 0,
            "rerank_enabled": False,
            "multi_route_enabled": False,
            "why_this_result": ["主链路失败后已自动降级，先避免接口直接报错。"],
        },
        "structured_context": {},
        "retrieval_strategy": {
            "backend": "runtime_fallback",
            "retrieval_mode": retrieval_mode,
            "degraded": True,
        },
        "degraded_notice": {
            "enabled": True,
            "reason": str(error_message),
            "message": "向量 RAG 暂时不可用，已返回保底结果。",
        },
        "ai_strategy": {
            "engine": "agent_runtime_fallback",
            "ai_enabled": False,
            "prompt_version": "assistant_v1",
            "model_name": "",
        },
        "runtime": {},
    }
    return normalize_feature_contract("vector_rag", fallback)


def execute_vector_rag_run(run: AIAsyncRun) -> AIAsyncRun:
    payload = dict(run.request_payload or {})
    query = str(payload.get("query") or "").strip()
    limit = int(payload.get("limit") or 8)
    retrieval_mode = str(payload.get("retrieval_mode") or "hybrid").strip() or "hybrid"
    try:
        workflow = get_workflow_definition("vector_rag")
        build_started = monotonic()
        step = start_step(
            run,
            step_key="vector_rag_retriever",
            step_kind="agent",
            agent_name="retriever",
            title="执行向量 RAG 检索",
            input_payload=payload,
            metadata={"feature_type": "vector_rag", "retrieval_mode": retrieval_mode, "workflow": workflow.planner, "roles": workflow.required_roles},
        )
        result_payload = run_vector_rag_search(
            query,
            limit,
            retrieval_mode=retrieval_mode,
            user=run.user,
        )
        result_payload = ensure_feature_runtime_payload("vector_rag", result_payload, run)
        result_payload = _critic_step(
            run,
            feature_type="vector_rag",
            payload=result_payload,
            require_evidence=True,
            require_answer_brief=True,
            max_repair_loops=get_agent_contract("critic").max_repair_loops,
        )
        finish_step(
            step,
            AgentStepResult(
                output_payload={
                    "headline": result_payload.get("headline", ""),
                    "summary": result_payload.get("summary", ""),
                    "answer_brief": result_payload.get("answer_brief", {}),
                    "retrieval_strategy": result_payload.get("retrieval_strategy", {}),
                },
                summary=result_payload.get("summary", ""),
                artifacts=[
                    {
                        "artifact_type": "retrieval_documents",
                        "artifact_key": "documents",
                        "title": "检索结果",
                        "payload": result_payload.get("documents", []),
                        "summary": result_payload.get("summary", ""),
                    },
                    {
                        "artifact_type": "runtime_trace",
                        "artifact_key": "evidence",
                        "title": "检索依据",
                        "payload": result_payload.get("evidence", {}),
                        "summary": result_payload.get("headline", ""),
                    },
                ],
            ),
            build_started,
        )
        create_artifact(
            run,
            artifact_type="result_payload",
            artifact_key="final_result",
            title="最终结果",
            payload=result_payload,
            summary=result_payload.get("summary", ""),
        )
        return complete_run(
            run,
            AgentRunResult(
                feature_type="vector_rag",
                result_payload=result_payload,
                degraded=bool((result_payload.get("degraded_notice") or {}).get("enabled")),
                retryable=True,
                status_text="已完成",
            ),
            request_payload=payload,
        )
    except Exception as exc:
        fallback = _build_vector_rag_fallback(run, str(exc))
        try:
            create_artifact(
                run,
                artifact_type="error_fallback",
                artifact_key="vector_rag_fallback",
                title="向量 RAG 保底结果",
                payload=fallback,
                summary=str(exc),
            )
            return complete_run(
                run,
                AgentRunResult(
                    feature_type="vector_rag",
                    result_payload=ensure_feature_runtime_payload("vector_rag", fallback, run),
                    degraded=True,
                    retryable=True,
                    status_text="已完成，当前结果为降级模式",
                    error_message=str(exc),
                ),
                request_payload=payload,
            )
        except Exception:
            return fail_run(run, str(exc), request_payload=payload, retryable=True)


def _build_retrieval_orchestrator_fallback(run: AIAsyncRun, error_message: str) -> Dict[str, object]:
    payload = dict(run.request_payload or {})
    query = str(payload.get("query") or "").strip()
    fallback = {
        "headline": "检索编排暂时回退",
        "summary": f"围绕“{query}”的检索编排主链路异常，已返回降级结果。",
        "query_analysis": {"query": query, "preferred_mode": "hybrid", "focus_label": "通用检索"},
        "learner_context": {},
        "selection": {
            "selected_path": "hybrid_rag",
            "selected_label": "Hybrid RAG",
            "comparison": {"structured_hits": 0, "hybrid_hits": 0, "dual_source_hits": 0},
            "preferred_mode": "hybrid",
            "reasons": ["主链路失败后已自动降级。"],
        },
        "final_answer": {
            "headline": "检索编排暂时回退",
            "summary": f"围绕“{query}”的检索编排主链路异常，已返回降级结果。",
            "grounded_points": ["建议稍后重试，或改成更具体的问题。"],
            "recommended_next_actions": ["换个问法再试", "缩小问题范围", "查看高级依据"],
        },
        "knowledge": {"structured_rag": {}, "hybrid_rag": {}},
        "tool_trace": [],
        "multi_agent": {"roles": [], "handoffs": [], "selected_path_reason": ["主链路失败后已自动降级。"]},
        "agent_flow": {
            "title": "检索编排回退路径",
            "inputs": [f"query：{query}"],
            "steps": [{"name": "fallback", "detail": "检索编排主链路异常，系统已自动降级。"}],
            "decision_highlights": ["当前结果为降级模式。"],
        },
        "langchain_trace": [],
        "runtime_stack": {"fallback": True},
        "degraded_notice": {
            "enabled": True,
            "reason": str(error_message),
            "message": "检索编排暂时不可用，已返回保底结果。",
        },
        "ai_strategy": {
            "engine": "agent_runtime_fallback",
            "rag_enabled": True,
            "ai_enabled": False,
            "prompt_version": "retrieval_orchestrator_v2_multi_agent",
            "model_name": "",
        },
        "runtime": {},
    }
    return normalize_feature_contract("retrieval_orchestrator", fallback)


def execute_retrieval_orchestrator_run(run: AIAsyncRun) -> AIAsyncRun:
    payload = dict(run.request_payload or {})
    query = str(payload.get("query") or "").strip()
    limit = int(payload.get("limit") or 6)
    try:
        workflow = get_workflow_definition("retrieval_orchestrator")
        build_started = monotonic()
        step = start_step(
            run,
            step_key="retrieval_orchestrator",
            step_kind="agent",
            agent_name="coordinator",
            title="执行检索编排",
            input_payload=payload,
            metadata={"feature_type": "retrieval_orchestrator", "workflow": workflow.planner, "roles": workflow.required_roles},
        )
        result_payload = build_retrieval_orchestrator_detail(run.user, query, limit)
        result_payload = ensure_feature_runtime_payload("retrieval_orchestrator", result_payload, run)
        result_payload = _critic_step(
            run,
            feature_type="retrieval_orchestrator",
            payload=result_payload,
            require_evidence=True,
            max_repair_loops=get_agent_contract("critic").max_repair_loops,
        )
        finish_step(
            step,
            AgentStepResult(
                output_payload={
                    "headline": result_payload.get("headline", ""),
                    "summary": result_payload.get("summary", ""),
                    "multi_agent": result_payload.get("multi_agent", {}),
                    "agent_flow": result_payload.get("agent_flow", {}),
                    "selection": result_payload.get("selection", {}),
                },
                summary=result_payload.get("summary", ""),
                artifacts=[
                    {
                        "artifact_type": "retrieval_knowledge",
                        "artifact_key": "knowledge",
                        "title": "知识召回结果",
                        "payload": result_payload.get("knowledge", {}),
                        "summary": result_payload.get("summary", ""),
                    },
                    {
                        "artifact_type": "runtime_trace",
                        "artifact_key": "agent_flow",
                        "title": "编排轨迹",
                        "payload": result_payload.get("agent_flow", {}),
                        "summary": result_payload.get("headline", ""),
                    },
                ],
            ),
            build_started,
        )
        create_artifact(
            run,
            artifact_type="result_payload",
            artifact_key="final_result",
            title="最终结果",
            payload=result_payload,
            summary=result_payload.get("summary", ""),
        )
        return complete_run(
            run,
            AgentRunResult(
                feature_type="retrieval_orchestrator",
                result_payload=result_payload,
                degraded=bool((result_payload.get("degraded_notice") or {}).get("enabled")),
                retryable=True,
                status_text="已完成",
            ),
            request_payload=payload,
        )
    except Exception as exc:
        fallback = _build_retrieval_orchestrator_fallback(run, str(exc))
        try:
            create_artifact(
                run,
                artifact_type="error_fallback",
                artifact_key="retrieval_orchestrator_fallback",
                title="检索编排保底结果",
                payload=fallback,
                summary=str(exc),
            )
            return complete_run(
                run,
                AgentRunResult(
                    feature_type="retrieval_orchestrator",
                    result_payload=ensure_feature_runtime_payload("retrieval_orchestrator", fallback, run),
                    degraded=True,
                    retryable=True,
                    status_text="已完成，当前结果为降级模式",
                    error_message=str(exc),
                ),
                request_payload=payload,
            )
        except Exception:
            return fail_run(run, str(exc), request_payload=payload, retryable=True)


def _build_conversation_run_fallback(run: AIAsyncRun, error_message: str) -> Dict[str, object]:
    payload = dict(run.request_payload or {})
    feature_type = str(payload.get("feature_type") or "rag").strip() or "rag"
    question = str(payload.get("question") or "").strip()
    fallback = {
        "conversation": {
            "id": run.conversation_id or 0,
            "feature_type": feature_type,
            "title": question[:48] or "AI 学习问答",
            "context": {"feature_type": feature_type},
            "status": "active",
        },
        "user_message": {"content": question},
        "assistant_message": {
            "content": "对话服务暂时不可用，已返回保底结果。",
            "payload": {
                "summary": "对话服务暂时不可用，已返回保底结果。",
                "degraded_notice": {"enabled": True, "reason": str(error_message)},
                "answer_brief": {"summary": "对话服务暂时不可用。", "points": [], "next_questions": ["稍后再试"]},
            },
        },
        "answer": {
            "summary": "对话服务暂时不可用，已返回保底结果。",
            "grounded_points": ["请稍后重试。"],
            "next_questions": ["稍后再试"],
        },
        "ai_strategy": {
            "engine": "agent_runtime_fallback",
            "ai_enabled": False,
            "prompt_version": "assistant_v1",
            "model_name": "",
        },
        "runtime": {},
        "degraded_notice": {
            "enabled": True,
            "reason": str(error_message),
            "message": "对话服务暂时不可用，已返回保底结果。",
        },
    }
    fallback["resolved_route"] = feature_type
    fallback["runtime_summary"] = {"status_text": "已降级", "summary": "对话服务暂时回退。"}
    return normalize_feature_contract("conversation", fallback)


def execute_conversation_run(run: AIAsyncRun) -> AIAsyncRun:
    payload = dict(run.request_payload or {})
    question = _stringify(payload.get("question"))
    feature_type = _stringify(payload.get("feature_type"), "rag")
    conversation = run.conversation
    context = _conversation_state(conversation)
    workflow = get_workflow_definition("conversation")
    try:
        planner_started = monotonic()
        planner_step = start_step(
            run,
            step_key="conversation_planner",
            step_kind="agent",
            agent_name="planner",
            title="分析会话路由与上下文",
            input_payload=payload,
            metadata={"feature_type": "conversation", "workflow": workflow.planner, "roles": workflow.required_roles},
        )
        route_input = _conversation_route_inputs(payload, context)
        resolved_route = route_input["resolved_route"]
        finish_step(
            planner_step,
            AgentStepResult(
                output_payload={
                    "resolved_route": resolved_route,
                    "rolling_summary": _stringify(context.get("rolling_summary")),
                    "selected_tools": [resolved_route],
                },
                summary=f"本轮会话将按 {resolved_route} 路由执行。",
                artifacts=[
                    {
                        "artifact_type": "route_decision",
                        "artifact_key": "conversation_route",
                        "title": "会话路由决策",
                        "payload": route_input,
                        "summary": f"选择 {resolved_route} 路由。",
                    }
                ],
            ),
            planner_started,
        )

        tool_started = monotonic()
        tool_step = start_step(
            run,
            step_key="conversation_tool_router",
            step_kind="tool",
            agent_name="tool_router",
            title="确定本轮允许调用的工具",
            input_payload={"resolved_route": resolved_route},
            metadata={"feature_type": "conversation", "allowed_tools": workflow.allowed_tools},
        )
        selected_tools = [resolved_route]
        if resolved_route == "rag":
            selected_tools = ["rag_search"]
        elif resolved_route == "grammar":
            selected_tools = ["grammar_tutor"]
        elif resolved_route == "writing":
            selected_tools = ["writing_correct"]
        elif resolved_route == "translation":
            selected_tools = ["translation_evaluate"]
        elif resolved_route == "scenario":
            selected_tools = ["scenario_dialogue"]
        finish_step(
            tool_step,
            AgentStepResult(
                output_payload={"selected_tools": selected_tools},
                summary="工具路由已确认。",
                artifacts=[
                    {
                        "artifact_type": "tool_plan",
                        "artifact_key": "conversation_tools",
                        "title": "工具计划",
                        "payload": {"selected_tools": selected_tools},
                        "summary": "本轮只允许使用白名单内工具。",
                    }
                ],
            ),
            tool_started,
        )

        exec_started = monotonic()
        exec_step = start_step(
            run,
            step_key="conversation_domain_tutor",
            step_kind="agent",
            agent_name="domain_tutor",
            title="生成本轮会话回答",
            input_payload={"question": question, "resolved_route": resolved_route},
            metadata={"feature_type": "conversation", "selected_tools": selected_tools},
        )
        answer_payload = _execute_conversation_route(run, resolved_route, route_input)
        answer_payload = ensure_feature_runtime_payload(
            "rag_search" if resolved_route == "rag" else (
                "grammar_tutor" if resolved_route == "grammar" else (
                    "writing_correct" if resolved_route == "writing" else (
                        "translation_evaluate" if resolved_route == "translation" else "scenario_dialogue"
                    )
                )
            ),
            answer_payload,
            run,
        )
        next_context = _normalize_conversation_context(
            conversation,
            feature_type=feature_type,
            resolved_route=resolved_route,
            question=question,
            answer_payload=answer_payload,
        )
        if conversation and next_context != (conversation.context or {}):
            conversation.context = next_context
            conversation.save(update_fields=["context", "updated_at"])
        conversation_payload = {
            "id": conversation.id if conversation else 0,
            "feature_type": conversation.feature_type if conversation else feature_type,
            "title": conversation.title if conversation else question[:48] or "AI 学习问答",
            "context": next_context,
            "status": conversation.status if conversation else "active",
        }
        final_payload = normalize_feature_contract(
            "conversation",
            {
                "conversation": conversation_payload,
                "resolved_route": resolved_route,
                "user_message": {"content": question},
                "assistant_message": {
                    "content": _stringify(
                        (_dictify(answer_payload.get("answer_brief")).get("summary"))
                        or (_dictify(answer_payload.get("answer")).get("summary"))
                        or answer_payload.get("summary")
                    ),
                    "payload": answer_payload,
                },
                "answer": answer_payload,
                "sentence": answer_payload.get("sentence"),
                "question": answer_payload.get("question") or question,
                "multi_agent": {
                    "roles": [{"name": role, "title": role, "responsibility": role, "output": role} for role in workflow.required_roles],
                    "handoffs": [
                        {"from": "planner", "to": "tool_router", "reason": "先决定本轮路线和允许工具。"},
                        {"from": "tool_router", "to": "domain_tutor", "reason": "按白名单选择实际执行路径。"},
                        {"from": "domain_tutor", "to": "critic", "reason": "回答生成后统一做结构和依据校验。"},
                    ],
                    "selected_tools": selected_tools,
                },
                "agent_flow": {
                    "title": "统一会话 Agent",
                    "inputs": [f"question: {question[:100]}"],
                    "steps": [
                        {"name": "planner", "detail": f"解析到 {resolved_route} 路由"},
                        {"name": "tool_router", "detail": f"选择工具 {', '.join(selected_tools)}"},
                        {"name": "domain_tutor", "detail": "已生成面向用户的回答"},
                    ],
                    "decision_highlights": [f"最近会话已累计 {next_context.get('turn_count', 1)} 轮。"],
                },
                "degraded_notice": answer_payload.get("degraded_notice") or {},
                "ai_strategy": answer_payload.get("ai_strategy") or {},
                "runtime": answer_payload.get("runtime") or {},
            },
        )
        final_payload = _critic_step(
            run,
            feature_type="conversation",
            payload=final_payload,
            require_answer_brief=False,
            max_repair_loops=get_agent_contract("critic").max_repair_loops,
        )
        _persist_conversation_messages(run, question=question, final_payload=final_payload)
        finish_step(
            exec_step,
            AgentStepResult(
                output_payload={
                    "headline": final_payload.get("headline", ""),
                    "summary": final_payload.get("summary", ""),
                    "resolved_route": resolved_route,
                    "selected_tools": selected_tools,
                },
                summary=final_payload.get("summary", ""),
                artifacts=[
                    {
                        "artifact_type": "conversation",
                        "artifact_key": "conversation_state",
                        "title": "会话状态",
                        "payload": conversation_payload,
                        "summary": final_payload.get("summary", ""),
                    },
                    {
                        "artifact_type": "result",
                        "artifact_key": "answer",
                        "title": "本轮回答",
                        "payload": answer_payload,
                        "summary": final_payload.get("summary", ""),
                    },
                ],
            ),
            exec_started,
        )
        create_artifact(
            run,
            artifact_type="result_payload",
            artifact_key="final_result",
            title="最终结果",
            payload=final_payload,
            summary=final_payload.get("summary", ""),
        )
        return complete_run(
            run,
            AgentRunResult(
                feature_type="conversation",
                result_payload=ensure_feature_runtime_payload("conversation", final_payload, run),
                degraded=bool((final_payload.get("degraded_notice") or {}).get("enabled")),
                retryable=True,
                status_text="已完成",
            ),
            request_payload=payload,
        )
    except Exception as exc:
        fallback = _build_conversation_run_fallback(run, str(exc))
        try:
            create_artifact(
                run,
                artifact_type="error_fallback",
                artifact_key="conversation_fallback",
                title="对话保底结果",
                payload=fallback,
                summary=str(exc),
            )
            return complete_run(
                run,
                AgentRunResult(
                    feature_type="conversation",
                    result_payload=ensure_feature_runtime_payload("conversation", fallback, run),
                    degraded=True,
                    retryable=True,
                    status_text="已完成，当前结果为降级模式",
                    error_message=str(exc),
                ),
                request_payload=payload,
            )
        except Exception:
            return fail_run(run, str(exc), request_payload=payload, retryable=True)


def _build_simple_feature_fallback(run: AIAsyncRun, error_message: str, headline: str, summary: str) -> Dict[str, object]:
    return normalize_feature_contract(
        str((run.request_payload or {}).get("feature_type") or run.feature_type),
        {
            "headline": headline,
            "summary": summary,
            "degraded_notice": {
                "enabled": True,
                "reason": str(error_message),
                "message": summary,
            },
            "ai_strategy": {
                "engine": "agent_runtime_fallback",
                "ai_enabled": False,
                "prompt_version": "assistant_v1",
                "model_name": "",
            },
            "runtime": {},
        },
    )


def execute_study_coach_run(run: AIAsyncRun) -> AIAsyncRun:
    payload = dict(run.request_payload or {})
    return _execute_simple_runtime_feature(
        run,
        feature_type="study_coach",
        step_key="study_coach",
        agent_name="coach",
        title="生成学习教练建议",
        builder=build_study_coach_detail,
        builder_args=(run.user, int(payload.get("trend_days") or 7)),
        fallback_builder=lambda current_run, error: _build_simple_feature_fallback(
            current_run,
            error,
            "AI 学习教练暂时回退",
            "学习教练主链路异常，已返回保底建议。",
        ),
    )


def execute_word_tutor_run(run: AIAsyncRun) -> AIAsyncRun:
    payload = dict(run.request_payload or {})
    return _execute_simple_runtime_feature(
        run,
        feature_type="word_tutor",
        step_key="word_tutor",
        agent_name="domain_tutor",
        title="生成 AI 讲词结果",
        builder=build_word_tutor_detail,
        builder_args=(run.user, int(payload.get("word_id") or 0)),
        fallback_builder=lambda current_run, error: _build_simple_feature_fallback(
            current_run,
            error,
            "AI 讲词暂时回退",
            "讲词主链路异常，已返回保底结果。",
        ),
    )


def execute_wrong_words_review_run(run: AIAsyncRun) -> AIAsyncRun:
    payload = dict(run.request_payload or {})
    return _execute_simple_runtime_feature(
        run,
        feature_type="wrong_words_review",
        step_key="wrong_words_review",
        agent_name="coach",
        title="生成错词复盘建议",
        builder=build_wrong_words_review_detail,
        builder_args=(run.user, int(payload.get("limit") or 12)),
        fallback_builder=lambda current_run, error: _build_simple_feature_fallback(
            current_run,
            error,
            "错词复盘暂时回退",
            "错词复盘主链路异常，已返回保底建议。",
        ),
    )


def execute_grammar_tutor_run(run: AIAsyncRun) -> AIAsyncRun:
    payload = dict(run.request_payload or {})
    sentence = str(payload.get("sentence") or "").strip()
    question = str(payload.get("question") or "").strip()
    builder = build_grammar_tutor_answer if question else build_grammar_tutor_detail
    args = (run.user, sentence, question) if question else (run.user, sentence)
    return _execute_simple_runtime_feature(
        run,
        feature_type="grammar_tutor",
        step_key="grammar_tutor",
        agent_name="domain_tutor",
        title="生成语法讲解",
        builder=builder,
        builder_args=args,
        fallback_builder=lambda current_run, error: _build_simple_feature_fallback(
            current_run,
            error,
            "语法讲解暂时回退",
            "语法问答主链路异常，已返回保底讲解。",
        ),
    )


def execute_writing_correct_run(run: AIAsyncRun) -> AIAsyncRun:
    payload = dict(run.request_payload or {})
    return _execute_simple_runtime_feature(
        run,
        feature_type="writing_correct",
        step_key="writing_correct",
        agent_name="domain_tutor",
        title="生成写作批改",
        builder=correct_writing,
        builder_args=(run.user, str(payload.get("text") or ""), str(payload.get("level") or "cet4")),
        fallback_builder=lambda current_run, error: _build_simple_feature_fallback(
            current_run,
            error,
            "写作批改暂时回退",
            "写作批改主链路异常，已返回保底结果。",
        ),
    )


def execute_writing_prompt_run(run: AIAsyncRun) -> AIAsyncRun:
    payload = dict(run.request_payload or {})
    return _execute_simple_runtime_feature(
        run,
        feature_type="writing_prompt",
        step_key="writing_prompt",
        agent_name="planner",
        title="生成写作题目",
        builder=generate_writing_prompt,
        builder_args=(
            run.user,
            str(payload.get("level") or "cet4"),
            str(payload.get("topic") or ""),
            str(payload.get("genre") or "essay"),
        ),
        fallback_builder=lambda current_run, error: _build_simple_feature_fallback(
            current_run,
            error,
            "写作题目生成暂时回退",
            "写作题目主链路异常，已返回保底结果。",
        ),
    )


def execute_translation_evaluate_run(run: AIAsyncRun) -> AIAsyncRun:
    payload = dict(run.request_payload or {})
    return _execute_simple_runtime_feature(
        run,
        feature_type="translation_evaluate",
        step_key="translation_evaluate",
        agent_name="domain_tutor",
        title="生成翻译反馈",
        builder=evaluate_translation,
        builder_args=(
            run.user,
            str(payload.get("source_text") or ""),
            str(payload.get("user_translation") or ""),
            str(payload.get("direction") or "auto"),
        ),
        fallback_builder=lambda current_run, error: _build_simple_feature_fallback(
            current_run,
            error,
            "翻译训练暂时回退",
            "翻译训练主链路异常，已返回保底结果。",
        ),
    )


def execute_scenario_dialogue_run(run: AIAsyncRun) -> AIAsyncRun:
    payload = dict(run.request_payload or {})
    return _execute_simple_runtime_feature(
        run,
        feature_type="scenario_dialogue",
        step_key="scenario_dialogue",
        agent_name="coach",
        title="生成情景对话回复",
        builder=run_scenario_dialogue,
        builder_args=(
            run.user,
            str(payload.get("scenario") or "daily"),
            str(payload.get("user_message") or ""),
            payload.get("conversation_id"),
        ),
        fallback_builder=lambda current_run, error: _build_simple_feature_fallback(
            current_run,
            error,
            "情景对话暂时回退",
            "情景对话主链路异常，已返回保底结果。",
        ),
    )


def execute_grammar_guide_run(run: AIAsyncRun) -> AIAsyncRun:
    return _execute_simple_runtime_feature(
        run,
        feature_type="grammar_guide",
        step_key="grammar_guide",
        agent_name="coach",
        title="生成语法导学",
        builder=build_grammar_guide,
        builder_args=(run.user,),
        fallback_builder=lambda current_run, error: _build_simple_feature_fallback(
            current_run,
            error,
            "语法导学暂时回退",
            "语法导学主链路异常，已返回保底结果。",
        ),
    )


def execute_study_report_run(run: AIAsyncRun) -> AIAsyncRun:
    payload = dict(run.request_payload or {})
    return _execute_simple_runtime_feature(
        run,
        feature_type="study_report",
        step_key="study_report",
        agent_name="critic",
        title="生成学习报告",
        builder=generate_study_report,
        builder_args=(run.user, str(payload.get("report_type") or "weekly")),
        fallback_builder=lambda current_run, error: _build_simple_feature_fallback(
            current_run,
            error,
            "学习报告暂时回退",
            "学习报告主链路异常，已返回保底结果。",
        ),
    )


def execute_mcp_tool_call_run(run: AIAsyncRun) -> AIAsyncRun:
    payload = dict(run.request_payload or {})
    tool_name = str(payload.get("tool_name") or "").strip()
    args = payload.get("args") or {}
    if not tool_name:
        return fail_run(run, "tool_name is required", request_payload=payload, retryable=False)
    try:
        build_started = monotonic()
        step = start_step(
            run,
            step_key="mcp_tool_router",
            step_kind="tool",
            agent_name="tool_router",
            title=f"执行 MCP 技能：{tool_name}",
            input_payload=payload,
            metadata={"feature_type": "mcp_tool_call", "tool_name": tool_name},
        )
        result_payload = execute_agent_safe_tool(
            run.user,
            tool_name,
            args,
            feature_type="mcp_tool_call",
            allowed_tools=[tool_name],
            run=run,
            step=step,
        )
        if isinstance(result_payload, dict) and result_payload.get("status") == "pending_approval":
            finish_step(
                step,
                AgentStepResult(
                    output_payload=result_payload,
                    summary=result_payload.get("summary", "该技能正在等待审批。"),
                    artifacts=[
                        {
                            "artifact_type": "approval_request",
                            "artifact_key": tool_name,
                            "title": f"{tool_name} 审批请求",
                            "payload": result_payload,
                            "summary": result_payload.get("summary", ""),
                        }
                    ],
                ),
                build_started,
            )
            create_artifact(
                run,
                artifact_type="approval_request",
                artifact_key=tool_name,
                title=f"{tool_name} 待审批",
                payload=result_payload,
                summary=result_payload.get("summary", ""),
            )
            return run
        finish_step(
            step,
            AgentStepResult(
                output_payload={
                    "tool_name": tool_name,
                    "summary": (result_payload or {}).get("summary", ""),
                    "runtime_summary": (result_payload or {}).get("runtime_summary", {}),
                },
                summary=(result_payload or {}).get("summary", f"{tool_name} 已执行"),
                artifacts=[
                    {
                        "artifact_type": "tool_result",
                        "artifact_key": tool_name,
                        "title": f"{tool_name} 结果",
                        "payload": result_payload or {},
                        "summary": (result_payload or {}).get("summary", ""),
                    }
                ],
            ),
            build_started,
        )
        final_payload = ensure_feature_runtime_payload(
            "mcp_tool_call",
            {
                "tool_name": tool_name,
                "result": result_payload or {},
            },
            run,
        )
        create_artifact(
            run,
            artifact_type="result_payload",
            artifact_key="final_result",
            title="最终结果",
            payload=final_payload,
            summary=((result_payload or {}).get("summary") or f"{tool_name} 已执行"),
        )
        return complete_run(
            run,
            AgentRunResult(
                feature_type="mcp_tool_call",
                result_payload=final_payload,
                degraded=bool(((result_payload or {}).get("degraded_notice") or {}).get("enabled")),
                retryable=True,
                status_text="已完成",
            ),
            request_payload=payload,
        )
    except Exception as exc:
        return fail_run(run, str(exc), request_payload=payload, retryable=True)


def _summary_from_payload(result_payload: Dict[str, object]) -> str:
    if not isinstance(result_payload, dict):
        return ""
    if result_payload.get("summary"):
        return str(result_payload.get("summary") or "")
    answer = result_payload.get("answer") or {}
    if isinstance(answer, dict) and answer.get("summary"):
        return str(answer.get("summary") or "")
    brief = result_payload.get("answer_brief") or {}
    if isinstance(brief, dict) and brief.get("summary"):
        return str(brief.get("summary") or "")
    return ""


def _build_role_cards(workflow, fallback_role: str) -> list[Dict[str, str]]:
    roles = workflow.required_roles or [fallback_role]
    return [
        {
            "name": role,
            "title": role,
            "responsibility": role,
            "output": role,
        }
        for role in roles
    ]


def _build_handoffs(workflow, *, selected_tools: list[str], title: str) -> list[Dict[str, str]]:
    roles = workflow.required_roles or []
    handoffs: list[Dict[str, str]] = []
    if "planner" in roles and "tool_router" in roles:
        handoffs.append(
            {
                "from": "planner",
                "to": "tool_router",
                "reason": f"先根据输入判断 {title} 需要哪些工具和上下文。",
            }
        )
    if "tool_router" in roles and "domain_tutor" in roles:
        handoffs.append(
            {
                "from": "tool_router",
                "to": "domain_tutor",
                "reason": f"按白名单选择工具 {', '.join(selected_tools) if selected_tools else 'direct_builder'} 后生成用户结果。",
            }
        )
    if "domain_tutor" in roles and "critic" in roles:
        handoffs.append(
            {
                "from": "domain_tutor",
                "to": "critic",
                "reason": "生成回答后统一做结构和质量校验。",
            }
        )
    return handoffs


def _inject_runtime_agent_metadata(
    feature_type: str,
    result_payload: Dict[str, object],
    *,
    workflow,
    planner_summary: str,
    selected_tools: list[str],
    title: str,
    detail: str,
) -> Dict[str, object]:
    payload = dict(result_payload or {})
    payload["multi_agent"] = {
        **_dictify(payload.get("multi_agent")),
        "roles": _build_role_cards(workflow, "domain_tutor"),
        "handoffs": _build_handoffs(workflow, selected_tools=selected_tools, title=title),
        "selected_tools": selected_tools,
    }
    payload["agent_flow"] = {
        "title": title,
        "inputs": [planner_summary],
        "steps": [
            {"name": "planner", "detail": planner_summary},
            {"name": "tool_router", "detail": f"选择工具：{', '.join(selected_tools) if selected_tools else 'direct_builder'}"},
            {"name": "domain_tutor", "detail": detail},
        ],
        "decision_highlights": [planner_summary],
    }
    return normalize_feature_contract(feature_type, payload)


def _artifacts_from_payload(result_payload: Dict[str, object]) -> list[Dict[str, object]]:
    artifacts: list[Dict[str, object]] = []
    if not isinstance(result_payload, dict):
        return artifacts
    artifact_specs = [
        ("snapshot", "snapshot", "上下文快照"),
        ("retrieval", "retrieval", "检索上下文"),
        ("result", "result", "核心结果"),
        ("review", "review", "复盘结果"),
        ("coach", "coach", "教练建议"),
        ("tutor", "tutor", "讲解结果"),
        ("conversation", "conversation", "会话信息"),
    ]
    for key, artifact_key, title in artifact_specs:
        payload = result_payload.get(key)
        if payload:
            artifacts.append(
                {
                    "artifact_type": key,
                    "artifact_key": artifact_key,
                    "title": title,
                    "payload": payload,
                    "summary": _summary_from_payload(result_payload),
                }
            )
    return artifacts


def _execute_simple_runtime_feature(
    run: AIAsyncRun,
    *,
    feature_type: str,
    step_key: str,
    agent_name: str,
    title: str,
    builder,
    builder_args: tuple = (),
    builder_kwargs: Dict[str, object] | None = None,
    fallback_builder=None,
) -> AIAsyncRun:
    payload = dict(run.request_payload or {})
    try:
        workflow = get_workflow_definition(feature_type)
        planner_started = monotonic()
        planner_step = start_step(
            run,
            step_key=f"{step_key}_planner",
            step_kind="agent",
            agent_name="planner" if "planner" in (workflow.required_roles or []) else agent_name,
            title=f"{title} · 规划输入",
            input_payload=payload,
            metadata={"feature_type": feature_type, "workflow": workflow.planner, "roles": workflow.required_roles or [agent_name]},
        )
        planner_summary = f"已解析 {feature_type} 请求，并准备进入 {title}。"
        finish_step(
            planner_step,
            AgentStepResult(
                output_payload={"selected_strategy": workflow.planner or "direct_builder"},
                summary=planner_summary,
                artifacts=[
                    {
                        "artifact_type": "route_decision",
                        "artifact_key": feature_type,
                        "title": "执行规划",
                        "payload": {
                            "feature_type": feature_type,
                            "workflow": workflow.planner,
                            "request_payload": payload,
                        },
                        "summary": planner_summary,
                    }
                ],
            ),
            planner_started,
        )

        selected_tools = list(workflow.allowed_tools or [])
        tool_started = monotonic()
        tool_step = start_step(
            run,
            step_key=f"{step_key}_tool_router",
            step_kind="tool",
            agent_name="tool_router" if "tool_router" in (workflow.required_roles or workflow.optional_roles or []) else agent_name,
            title=f"{title} · 选择工具",
            input_payload={"request_payload": payload},
            metadata={"feature_type": feature_type, "allowed_tools": selected_tools},
        )
        finish_step(
            tool_step,
            AgentStepResult(
                output_payload={"selected_tools": selected_tools},
                summary="工具计划已确认。",
                artifacts=[
                    {
                        "artifact_type": "tool_plan",
                        "artifact_key": feature_type,
                        "title": "工具计划",
                        "payload": {"selected_tools": selected_tools},
                        "summary": "本轮使用白名单内工具或直连 builder。",
                    }
                ],
            ),
            tool_started,
        )

        build_started = monotonic()
        step = start_step(
            run,
            step_key=f"{step_key}_domain_tutor",
            step_kind="agent",
            agent_name=agent_name,
            title=title,
            input_payload=payload,
            metadata={"feature_type": feature_type, "selected_tools": selected_tools},
        )
        result_payload = builder(*builder_args, **(builder_kwargs or {}))
        result_payload = _inject_runtime_agent_metadata(
            feature_type,
            result_payload,
            workflow=workflow,
            planner_summary=planner_summary,
            selected_tools=selected_tools,
            title=title,
            detail=f"{title} 已生成用户结果。",
        )
        result_payload = ensure_feature_runtime_payload(feature_type, result_payload, run)
        result_payload = _critic_step(
            run,
            feature_type=feature_type,
            payload=result_payload,
            max_repair_loops=1,
        )
        summary = _summary_from_payload(result_payload)
        finish_step(
            step,
            AgentStepResult(
                output_payload={
                    "headline": result_payload.get("headline", ""),
                    "summary": summary,
                    "feature_runtime": result_payload.get("feature_runtime", {}),
                    "multi_agent": result_payload.get("multi_agent", {}),
                },
                summary=summary,
                artifacts=_artifacts_from_payload(result_payload),
            ),
            build_started,
        )
        create_artifact(
            run,
            artifact_type="result_payload",
            artifact_key="final_result",
            title="最终结果",
            payload=result_payload,
            summary=summary,
        )
        return complete_run(
            run,
            AgentRunResult(
                feature_type=feature_type,
                result_payload=result_payload,
                degraded=bool((result_payload.get("degraded_notice") or {}).get("enabled")),
                retryable=True,
                status_text="已完成",
            ),
            request_payload=payload,
        )
    except Exception as exc:
        if not fallback_builder:
            return fail_run(run, str(exc), request_payload=payload, retryable=True)
        fallback = fallback_builder(run, str(exc))
        try:
            critic_started = monotonic()
            critic_step = start_step(
                run,
                step_key=f"{step_key}_critic",
                step_kind="critic",
                agent_name="critic",
                title=f"{title} · 降级结果校验",
                input_payload={"feature_type": feature_type, "fallback": True},
                metadata={"feature_type": feature_type, "fallback": True},
            )
            fallback = ensure_feature_runtime_payload(feature_type, fallback, run)
            fallback = _critic_step(
                run,
                feature_type=feature_type,
                payload=fallback,
                max_repair_loops=1,
            )
            finish_step(
                critic_step,
                AgentStepResult(
                    output_payload={
                        "headline": fallback.get("headline", ""),
                        "summary": _summary_from_payload(fallback),
                        "degraded": True,
                    },
                    summary=_summary_from_payload(fallback),
                ),
                critic_started,
            )
            create_artifact(
                run,
                artifact_type="error_fallback",
                artifact_key=f"{feature_type}_fallback",
                title="降级结果",
                payload=fallback,
                summary=str(exc),
            )
            return complete_run(
                run,
                AgentRunResult(
                    feature_type=feature_type,
                    result_payload=ensure_feature_runtime_payload(feature_type, fallback, run),
                    degraded=True,
                    retryable=True,
                    status_text="已完成，当前结果为降级模式",
                    error_message=str(exc),
                ),
                request_payload=payload,
            )
        except Exception:
            return fail_run(run, str(exc), request_payload=payload, retryable=True)
