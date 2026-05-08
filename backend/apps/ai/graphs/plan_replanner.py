import os
from functools import lru_cache
from typing import Any, Dict, List, TypedDict

from pydantic import BaseModel, Field

from ..compat import END, START, LANGGRAPH_AVAILABLE, StateGraph, build_runtime_capabilities
from ..langchain_runtime import run_json_chain, run_tool_calling_chain
from ..mcp.server_http import call_mcp_tool
from ..profile_memory import get_or_refresh_profile_memory, serialize_profile_memory
from ..providers.deepseek import is_provider_ready


PROMPT_VERSION = "plan_replan_v2_multi_agent"


class PlanReplanState(TypedDict, total=False):
    user: Any
    trend_days: int
    context_bundle: Dict[str, Any]
    profile_memory: Dict[str, Any]
    rag_query: str
    knowledge: Dict[str, Any]
    tool_trace: List[Dict[str, Any]]
    multi_agent: Dict[str, Any]
    replan: Dict[str, Any]
    agent_flow: Dict[str, Any]
    runtime: Dict[str, Any]
    langchain_trace: List[Dict[str, Any]]
    runtime_stack: Dict[str, Any]


class PlanReplanSchema(BaseModel):
    headline: str = Field(default="")
    summary: str = Field(default="")
    new_plan: Dict[str, Any] = Field(default_factory=dict)
    plan_patch: Dict[str, Any] = Field(default_factory=dict)
    decision: Dict[str, Any] = Field(default_factory=dict)


def _invoke_tool(user, tool_name: str, args: Dict[str, Any] | None = None, summary: str = "") -> Dict[str, Any]:
    result = call_mcp_tool(user, tool_name, args or {})
    return {
        "tool_name": tool_name,
        "args": args or {},
        "summary": summary or f"调用 {tool_name}",
        "result": result,
    }


def _summarize_tool_result(item: Dict[str, Any]) -> str:
    tool_name = item.get("tool_name", "")
    result = item.get("result") or {}
    if tool_name == "get_user_plan":
        plan = result.get("plan") or {}
        if not plan:
            return "当前没有激活的学习计划"
        return f"当前计划词书={plan.get('book', {}).get('name', '')}，daily_target={plan.get('daily_target', 0)}"
    if tool_name == "get_today_task":
        summary = result.get("summary") or {}
        adaptive = result.get("adaptive") or {}
        return (
            f"今日新词剩余={summary.get('new_words_remaining', 0)}，"
            f"复习剩余={summary.get('review_words_remaining', 0)}，"
            f"模式={adaptive.get('mode_label', '')}"
        )
    if tool_name == "get_due_reviews":
        return f"读取到期复习词 {len(result.get('list') or [])} 条"
    if tool_name == "get_wrong_words":
        return f"读取错词 {len(result.get('list') or [])} 条"
    if tool_name == "get_study_snapshot":
        overview = result.get("overview") or {}
        return f"最近学习词数={overview.get('learned_word_count', 0)}，错词数={overview.get('wrong_word_count', 0)}"
    if tool_name == "rag_search":
        answer = result.get("answer") or {}
        return f"结构化 RAG：{answer.get('summary', '')}"
    if tool_name == "vector_rag_search":
        answer = result.get("answer") or {}
        return f"向量 RAG：{answer.get('summary', '')}"
    return item.get("summary", tool_name)


def _build_rag_query(context_bundle: Dict[str, Any]) -> str:
    plan = (context_bundle.get("plan_ctx") or {}).get("plan") or {}
    today_task = context_bundle.get("today_task") or {}
    due_reviews = (context_bundle.get("due_reviews") or {}).get("list") or []
    wrong_words = (context_bundle.get("wrong_words") or {}).get("list") or []
    adaptive = (today_task.get("adaptive") or {})
    weak_points = adaptive.get("weak_points") or []
    book_name = ((plan.get("book") or {}).get("name") or "当前词书").strip()
    focus_bits = []
    for item in wrong_words[:2]:
        if item.get("word"):
            focus_bits.append(item["word"])
    for item in due_reviews[:2]:
        if item.get("word"):
            focus_bits.append(item["word"])
    for item in weak_points[:1]:
        if item.get("label"):
            focus_bits.append(item["label"])
    if focus_bits:
        return f"如何为学习 {book_name} 的用户重规划今天的英语学习任务，重点处理 {'、'.join(focus_bits)}，平衡新词与复习"
    return f"如何为学习 {book_name} 的用户平衡今天的新词学习与复习任务"


def _build_fallback_replan(state: PlanReplanState) -> Dict[str, Any]:
    context_bundle = state.get("context_bundle") or {}
    plan = (context_bundle.get("plan_ctx") or {}).get("plan") or {}
    today_task = context_bundle.get("today_task") or {}
    adaptive = today_task.get("adaptive") or {}
    summary = today_task.get("summary") or {}
    overview = ((context_bundle.get("study_snapshot") or {}).get("overview") or {})
    due_reviews = (context_bundle.get("due_reviews") or {}).get("list") or []
    wrong_words = (context_bundle.get("wrong_words") or {}).get("list") or []
    current_daily_target = int(plan.get("daily_target") or adaptive.get("base_daily_target") or 20)
    suggested_daily_target = int(adaptive.get("recommended_new_word_target") or current_daily_target)
    review_target = int(adaptive.get("recommended_review_word_target") or max(len(due_reviews), 10))
    mode = adaptive.get("mode", "balanced")
    mode_label = adaptive.get("mode_label", "维持均衡节奏")
    plan_patch = {}
    if plan and suggested_daily_target and suggested_daily_target != current_daily_target:
        plan_patch["daily_target"] = suggested_daily_target

    return {
        "headline": "AI 已为你重新规划今天的学习计划",
        "summary": adaptive.get("focus_tip") or "已根据计划、错词、复习压力和趋势重新整理今天更合适的节奏。",
        "new_plan": {
            "book_name": ((plan.get("book") or {}).get("name") or ""),
            "current_daily_target": current_daily_target,
            "suggested_daily_target": suggested_daily_target,
            "review_target": review_target,
            "focus_mode": mode,
            "focus_mode_label": mode_label,
            "study_order": [
                "先完成到期复习词",
                "回收高频错词",
                "再推进今天的新词",
                "最后用例句或语法点做一次巩固",
            ],
            "focus_words": [item.get("word", "") for item in wrong_words[:4] if item.get("word")],
            "time_blocks": [
                {"label": "复习回收", "minutes": 15, "focus": "先处理到期复习与高频错词"},
                {"label": "新词推进", "minutes": 20, "focus": "按建议目标推进今天的新词"},
                {"label": "例句巩固", "minutes": 10, "focus": "用例句或语法点把新旧内容串起来"},
            ],
        },
        "plan_patch": plan_patch,
        "decision": {
            "reasons": [
                f"当前建议模式为“{mode_label}”",
                f"今日仍有 {summary.get('review_words_remaining', 0)} 个复习任务待完成",
                f"当前活跃错词 {len(wrong_words)} 个，到期复习词 {len(due_reviews)} 个",
            ],
            "risks": [
                f"近期累计已学 {overview.get('learned_word_count', 0)} 个词，但如果今天继续堆新词，复习压力会继续上升。",
                "如果今晚时间不足，优先保留复习回收和错词巩固，再减少新词量。",
            ],
            "expected_benefit": "先把复习压力降下来，再推进新词，能降低重复出错和学习中断。",
        },
    }


def _build_multi_agent_story(context_bundle: Dict[str, Any], knowledge: Dict[str, Any], fallback: Dict[str, Any]) -> Dict[str, Any]:
    structured = (knowledge.get("structured_rag") or {}).get("answer") or {}
    vector = (knowledge.get("vector_rag") or {}).get("answer") or {}
    today_task = context_bundle.get("today_task") or {}
    adaptive = today_task.get("adaptive") or {}
    return {
        "roles": [
            {
                "name": "supervisor",
                "title": "总控协调者",
                "responsibility": "整合计划、检索与教练建议，输出最终计划 patch。",
                "output": fallback.get("headline", ""),
            },
            {
                "name": "planner",
                "title": "计划分析员",
                "responsibility": "读取计划、今日任务与复习压力，判断今天该保守还是推进。",
                "output": adaptive.get("mode_label", ""),
            },
            {
                "name": "retriever",
                "title": "证据检索员",
                "responsibility": "调用 structured/vector RAG、错词与趋势数据补充证据。",
                "output": structured.get("summary") or vector.get("summary") or "已补充检索证据",
            },
            {
                "name": "coach",
                "title": "学习教练",
                "responsibility": "把策略翻译成用户可读的顺序、提醒与收益。",
                "output": fallback.get("summary", ""),
            },
        ],
        "handoffs": [
            {"from": "planner", "to": "retriever", "reason": "计划分析员先确认当前复习与新词压力，再请求检索补证据。"},
            {"from": "retriever", "to": "coach", "reason": "检索员把错词、RAG 与趋势证据交给教练组织成可执行建议。"},
            {"from": "coach", "to": "supervisor", "reason": "教练完成用户可读表达后，由总控生成最终 patch。"},
        ],
        "selected_tools": ["get_user_plan", "get_today_task", "get_due_reviews", "get_wrong_words", "get_study_snapshot", "rag_search", "vector_rag_search"],
    }


def _generate_replan_with_langchain(state: PlanReplanState) -> Dict[str, Any]:
    fallback = _build_fallback_replan(state)
    payload = {
        "study_context": state.get("context_bundle") or {},
        "profile_memory": state.get("profile_memory") or {},
        "rag_query": state.get("rag_query", ""),
        "structured_rag": (state.get("knowledge") or {}).get("structured_rag") or {},
        "vector_rag": (state.get("knowledge") or {}).get("vector_rag") or {},
        "multi_agent": state.get("multi_agent") or {},
        "task": "Replan today's English learning schedule for the user and return strict JSON.",
    }
    result = run_tool_calling_chain(
        stack_name="plan_replanner_chain",
        system_prompt="You are a multi-agent English learning planning system for Chinese learners. Use the provided study context only, call the most relevant tools if needed, then provide a concise final response.",
        payload=payload,
        user=state["user"],
        tool_names=["get_user_plan", "get_today_task", "get_due_reviews", "get_wrong_words", "get_study_snapshot", "rag_search", "vector_rag_search"],
    )
    json_result = run_json_chain(
        stack_name="plan_replanner_json",
        system_prompt="You are a multi-agent English learning planning system for Chinese learners. Use the provided study context only and output strict JSON.",
        payload=payload,
        schema_model=PlanReplanSchema,
    )
    final = dict(fallback)
    chain_result = json_result.get("result") or {}
    if json_result.get("enabled"):
        final.update(
            {
                "headline": chain_result.get("headline") or final["headline"],
                "summary": chain_result.get("summary") or final["summary"],
                "new_plan": chain_result.get("new_plan") or final["new_plan"],
                "plan_patch": chain_result.get("plan_patch") or final["plan_patch"],
                "decision": chain_result.get("decision") or final["decision"],
            }
        )
    return {
        "result": final,
        "langchain_trace": (result.get("trace") or []) + (json_result.get("trace") or []),
        "runtime_stack": {
            **(result.get("runtime_stack") or {}),
            **(json_result.get("runtime_stack") or {}),
        },
    }


def _node_collect_context(state: PlanReplanState) -> Dict[str, Any]:
    user = state["user"]
    trend_days = min(max(int(state.get("trend_days", 7) or 7), 3), 14)
    memory = get_or_refresh_profile_memory(user, source="plan_replan")
    trace = [
        _invoke_tool(user, "get_user_plan", {}, "读取当前学习计划"),
        _invoke_tool(user, "get_today_task", {}, "读取今日任务与 adaptive 建议"),
        _invoke_tool(user, "get_due_reviews", {"limit": 8}, "读取到期复习词"),
        _invoke_tool(user, "get_wrong_words", {}, "读取当前错词本"),
        _invoke_tool(user, "get_study_snapshot", {"days": trend_days}, "读取最近学习趋势"),
    ]
    for item in trace:
        item["summary"] = _summarize_tool_result(item)
    return {
        "context_bundle": {
            "plan_ctx": trace[0]["result"],
            "today_task": trace[1]["result"],
            "due_reviews": trace[2]["result"],
            "wrong_words": trace[3]["result"],
            "study_snapshot": trace[4]["result"],
        },
        "profile_memory": serialize_profile_memory(memory),
        "tool_trace": trace,
    }


def _node_retrieve_knowledge(state: PlanReplanState) -> Dict[str, Any]:
    user = state["user"]
    rag_query = _build_rag_query(state.get("context_bundle") or {})
    structured = _invoke_tool(user, "rag_search", {"query": rag_query, "limit": 4}, "调用结构化 RAG 检索与当前问题更相关的词库、语法点和句库资料")
    vector = _invoke_tool(user, "vector_rag_search", {"query": rag_query, "limit": 4}, "调用本地轻量向量 RAG 召回更相近的学习资料")
    structured["summary"] = _summarize_tool_result(structured)
    vector["summary"] = _summarize_tool_result(vector)
    return {
        "rag_query": rag_query,
        "knowledge": {
            "structured_rag": structured["result"],
            "vector_rag": vector["result"],
        },
        "tool_trace": (state.get("tool_trace") or []) + [structured, vector],
    }


def _node_run_multi_agent(state: PlanReplanState) -> Dict[str, Any]:
    fallback = _build_fallback_replan(state)
    multi_agent = _build_multi_agent_story(state.get("context_bundle") or {}, state.get("knowledge") or {}, fallback)
    return {"multi_agent": multi_agent}


def _node_generate_result(state: PlanReplanState) -> Dict[str, Any]:
    runtime = build_runtime_capabilities()
    fallback = _build_fallback_replan(state)
    chain_payload = _generate_replan_with_langchain(state) if is_provider_ready() else {"result": fallback, "langchain_trace": [], "runtime_stack": {}}
    replan = chain_payload["result"]
    context_bundle = state.get("context_bundle") or {}
    plan = (context_bundle.get("plan_ctx") or {}).get("plan") or {}
    today_task = context_bundle.get("today_task") or {}
    wrong_words = ((context_bundle.get("wrong_words") or {}).get("list") or [])[:4]
    due_reviews = ((context_bundle.get("due_reviews") or {}).get("list") or [])[:4]
    agent_flow = {
        "title": "AI 重规划学习计划 Multi-Agent",
        "inputs": [
            f"当前词书：{((plan.get('book') or {}).get('name') or '未设置')}",
            f"当前日目标：{plan.get('daily_target', 0)}",
            f"复习剩余：{(today_task.get('summary') or {}).get('review_words_remaining', 0)}",
            f"错词数量：{len((context_bundle.get('wrong_words') or {}).get('list') or [])}",
        ],
        "steps": [
            {"name": "planner", "detail": "规划角色读取学习计划、今日任务与复习压力。"},
            {"name": "retriever", "detail": f"检索角色围绕“{state.get('rag_query', '')}”补充 structured/vector RAG 证据。"},
            {"name": "coach", "detail": "教练角色把策略翻译成用户可读的执行顺序和提醒。"},
            {"name": "supervisor", "detail": "总控角色整合角色输出，生成最终计划 patch。"},
        ],
        "decision_highlights": [
            f"优先错词：{'、'.join(item.get('word', '') for item in wrong_words if item.get('word')) or '暂无'}",
            f"到期复习：{'、'.join(item.get('word', '') for item in due_reviews if item.get('word')) or '暂无'}",
            f"建议模式：{(today_task.get('adaptive') or {}).get('mode_label', '')}",
        ],
    }
    return {
        "runtime": runtime,
        "replan": replan,
        "agent_flow": agent_flow,
        "langchain_trace": chain_payload.get("langchain_trace") or [],
        "runtime_stack": chain_payload.get("runtime_stack") or {},
    }


@lru_cache(maxsize=1)
def _build_graph():
    graph = StateGraph(PlanReplanState)
    graph.add_node("collect_context", _node_collect_context)
    graph.add_node("retrieve_knowledge", _node_retrieve_knowledge)
    graph.add_node("run_multi_agent", _node_run_multi_agent)
    graph.add_node("generate_result", _node_generate_result)
    graph.add_edge(START, "collect_context")
    graph.add_edge("collect_context", "retrieve_knowledge")
    graph.add_edge("retrieve_knowledge", "run_multi_agent")
    graph.add_edge("run_multi_agent", "generate_result")
    graph.add_edge("generate_result", END)
    return graph.compile()


def _run_pipeline(initial_state: PlanReplanState) -> PlanReplanState:
    state = dict(initial_state)
    state.update(_node_collect_context(state))
    state.update(_node_retrieve_knowledge(state))
    state.update(_node_run_multi_agent(state))
    state.update(_node_generate_result(state))
    return state


def _run_graph(initial_state: PlanReplanState) -> PlanReplanState:
    if LANGGRAPH_AVAILABLE:
        return _build_graph().invoke(initial_state)
    return _run_pipeline(initial_state)


def build_plan_replan_detail(user, trend_days: int = 7) -> Dict[str, Any]:
    state = _run_graph({"user": user, "trend_days": trend_days})
    context_bundle = state.get("context_bundle") or {}
    plan = (context_bundle.get("plan_ctx") or {}).get("plan") or {}
    plan_patch = state.get("replan", {}).get("plan_patch", {}) or {}
    if not plan:
        plan_patch = {}
    return {
        "headline": state.get("replan", {}).get("headline", ""),
        "summary": state.get("replan", {}).get("summary", ""),
        "new_plan": state.get("replan", {}).get("new_plan", {}),
        "plan_patch": plan_patch,
        "decision": state.get("replan", {}).get("decision", {}),
        "knowledge": state.get("knowledge", {}),
        "tool_trace": [{"tool_name": item.get("tool_name", ""), "args": item.get("args", {}), "summary": item.get("summary", "")} for item in (state.get("tool_trace") or [])],
        "agent_flow": state.get("agent_flow", {}),
        "context_bundle": state.get("context_bundle", {}),
        "profile_memory": state.get("profile_memory", {}),
        "multi_agent": state.get("multi_agent", {}),
        "langchain_trace": state.get("langchain_trace", []),
        "runtime_stack": state.get("runtime_stack", {}),
        "ai_strategy": {
            "engine": "langgraph" if LANGGRAPH_AVAILABLE else "pipeline",
            "rag_enabled": True,
            "ai_enabled": is_provider_ready(),
            "prompt_version": PROMPT_VERSION,
            "model_name": os.getenv("AI_MODEL", "").strip(),
        },
        "runtime": state.get("runtime", build_runtime_capabilities()),
    }
