import os
from functools import lru_cache
from typing import Any, Dict, List, TypedDict

from pydantic import BaseModel, Field

from ..compat import END, START, LANGGRAPH_AVAILABLE, StateGraph, build_runtime_capabilities
from ..langchain_runtime import run_json_chain, run_tool_calling_chain
from ..mcp.server_http import call_mcp_tool
from ..providers.deepseek import is_provider_ready
from ..rag.retrievers import extract_query_keywords


PROMPT_VERSION = "retrieval_orchestrator_v2_multi_agent"


class RetrievalOrchestratorState(TypedDict, total=False):
    user: Any
    query: str
    limit: int
    query_analysis: Dict[str, Any]
    learner_context: Dict[str, Any]
    tool_trace: List[Dict[str, Any]]
    knowledge: Dict[str, Any]
    selection: Dict[str, Any]
    final_answer: Dict[str, Any]
    multi_agent: Dict[str, Any]
    agent_flow: Dict[str, Any]
    runtime: Dict[str, Any]
    headline: str
    summary: str
    langchain_trace: List[Dict[str, Any]]
    runtime_stack: Dict[str, Any]


class RetrievalAnswerSchema(BaseModel):
    headline: str = Field(default="")
    summary: str = Field(default="")
    grounded_points: List[str] = Field(default_factory=list)
    recommended_next_actions: List[str] = Field(default_factory=list)


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
    if tool_name == "get_profile_memory":
        return f"读取学习画像：{(result.get('profile_summary') or '已加载用户偏好')[:36]}"
    if tool_name == "get_study_snapshot":
        overview = result.get("overview") or {}
        return f"学习快照：已学 {overview.get('learned_word_count', 0)} 词，错词 {overview.get('wrong_word_count', 0)} 个"
    if tool_name == "rag_search":
        return f"结构化 RAG：{((result.get('answer') or {}).get('summary') or '')}"
    if tool_name == "vector_rag_search":
        answer = result.get("answer") or {}
        strategy = result.get("retrieval_strategy") or {}
        return f"Hybrid RAG：{answer.get('summary', '')} / mode={strategy.get('retrieval_mode', '')}"
    return item.get("summary", tool_name)


def _guess_focus(query: str) -> Dict[str, str]:
    text = str(query or "").lower()
    if any(token in text for token in ["语法", "grammar", "时态", "从句", "句型"]):
        return {"focus": "grammar_rule", "focus_label": "语法规则理解", "preferred_mode": "structured"}
    if any(token in text for token in ["区别", "近义", "表达", "怎么说", "搭配", "例句", "用法"]):
        return {"focus": "usage_and_difference", "focus_label": "词义区别与例句用法", "preferred_mode": "hybrid"}
    return {"focus": "general_lookup", "focus_label": "通用知识检索", "preferred_mode": "hybrid"}


def _build_query_analysis(query: str) -> Dict[str, Any]:
    guess = _guess_focus(query)
    return {
        "query": query,
        "keywords": extract_query_keywords(query),
        "focus": guess["focus"],
        "focus_label": guess["focus_label"],
        "preferred_mode": guess["preferred_mode"],
        "planner_note": (
            "优先用结构化检索拿到明确规则，再结合 hybrid RAG 补充近义词、例句和更相近表达。"
            if guess["preferred_mode"] == "hybrid"
            else "先从规则型资料中命中更明确的内容，再按需补充相近语义召回。"
        ),
    }


def _structured_hit_count(result: Dict[str, Any]) -> int:
    retrieval = result.get("retrieval") or {}
    return len(retrieval.get("words") or []) + len(retrieval.get("grammar_points") or []) + len(retrieval.get("sentences") or [])


def _hybrid_hit_count(result: Dict[str, Any]) -> int:
    return len(result.get("documents") or [])


def _hybrid_dual_source_count(result: Dict[str, Any]) -> int:
    return sum(1 for item in (result.get("documents") or []) if len(item.get("retrieval_sources") or []) >= 2)


def _build_fallback_final_answer(state: RetrievalOrchestratorState) -> Dict[str, Any]:
    query_analysis = state.get("query_analysis") or {}
    knowledge = state.get("knowledge") or {}
    structured = knowledge.get("structured_rag") or {}
    hybrid = knowledge.get("hybrid_rag") or {}
    selection = state.get("selection") or {}
    selected_label = selection.get("selected_label", "Hybrid RAG")
    structured_answer = (structured.get("answer") or {}).get("summary", "")
    hybrid_answer = (hybrid.get("answer") or {}).get("summary", "")
    return {
        "headline": "LangGraph 检索编排已完成",
        "summary": f"围绕“{state.get('query', '')}”，系统先分析问题意图，再通过 MCP 工具依次执行结构化 RAG 和 Hybrid RAG，最后选择更适合当前问题的 {selected_label} 作为主回答路径。",
        "grounded_points": [
            f"问题焦点：{query_analysis.get('focus_label', '通用检索')}",
            f"结构化 RAG：{structured_answer or '已完成规则型知识检索'}",
            f"Hybrid RAG：{hybrid_answer or '已完成语义召回与融合检索'}",
        ],
        "recommended_next_actions": [
            "继续追问第一个命中结果的例句或语法点。",
            "切换到 Hybrid 查看结构化与向量融合后的命中差异。",
            "把这个问题写成更具体的句子，再观察编排策略是否变化。",
        ],
    }


def _build_selection(state: RetrievalOrchestratorState) -> Dict[str, Any]:
    query_analysis = state.get("query_analysis") or {}
    knowledge = state.get("knowledge") or {}
    structured = knowledge.get("structured_rag") or {}
    hybrid = knowledge.get("hybrid_rag") or {}
    structured_hits = _structured_hit_count(structured)
    hybrid_hits = _hybrid_hit_count(hybrid)
    dual_source_hits = _hybrid_dual_source_count(hybrid)
    preferred_mode = query_analysis.get("preferred_mode", "hybrid")
    selected_path = "hybrid_rag"
    selected_label = "Hybrid RAG"
    reasons: List[str] = []
    if preferred_mode == "structured" and structured_hits > 0:
        selected_path = "structured_rag"
        selected_label = "结构化 RAG"
        reasons.append("当前问题更偏规则解释，结构化检索更容易命中明确语法点或词条。")
    elif dual_source_hits > 0:
        reasons.append("同一批结果里存在结构化与向量双重命中，说明 Hybrid 结果更稳定。")
    elif structured_hits >= hybrid_hits and structured_hits > 0:
        selected_path = "structured_rag"
        selected_label = "结构化 RAG"
        reasons.append("结构化检索命中的规则型内容更多，更适合先给出明确答案。")
    else:
        reasons.append("Hybrid RAG 能补充相近意思和例句，覆盖面更好。")
    return {
        "selected_path": selected_path,
        "selected_label": selected_label,
        "comparison": {"structured_hits": structured_hits, "hybrid_hits": hybrid_hits, "dual_source_hits": dual_source_hits},
        "preferred_mode": preferred_mode,
        "reasons": reasons or ["系统根据召回覆盖情况自动选择了更合适的检索路径。"],
    }


def _build_multi_agent_story(state: RetrievalOrchestratorState) -> Dict[str, Any]:
    selection = state.get("selection") or {}
    return {
        "roles": [
            {"name": "supervisor", "title": "总控协调者", "responsibility": "比较两条检索路径并输出最终主回答。", "output": selection.get("selected_label", "")},
            {"name": "planner", "title": "问题分析员", "responsibility": "分析 query 关键词、焦点与 preferred_mode。", "output": (state.get("query_analysis") or {}).get("focus_label", "")},
            {"name": "retriever", "title": "检索执行员", "responsibility": "执行 structured 与 hybrid 检索并比较命中情况。", "output": f"structured={selection.get('comparison', {}).get('structured_hits', 0)} / hybrid={selection.get('comparison', {}).get('hybrid_hits', 0)}"},
            {"name": "coach", "title": "学习教练", "responsibility": "把检索结果翻译成适合学习者的解释与下一步建议。", "output": ((state.get('final_answer') or {}).get('summary') or "")},
        ],
        "handoffs": [
            {"from": "planner", "to": "retriever", "reason": "问题分析员先确定焦点和检索偏好，再交给检索执行员。"},
            {"from": "retriever", "to": "coach", "reason": "检索执行员把 structured/hybrid 命中差异交给教练组织解释。"},
            {"from": "coach", "to": "supervisor", "reason": "教练完成学习者可读表达后，由总控确定最终主路径。"},
        ],
        "selected_path_reason": selection.get("reasons", []),
    }


def _generate_answer_with_langchain(state: RetrievalOrchestratorState) -> Dict[str, Any]:
    fallback = _build_fallback_final_answer(state)
    payload = {
        "query": state.get("query", ""),
        "query_analysis": state.get("query_analysis") or {},
        "learner_context": state.get("learner_context") or {},
        "knowledge": state.get("knowledge") or {},
        "selection": state.get("selection") or {},
        "multi_agent": state.get("multi_agent") or {},
        "task": "Summarize how the retrieval orchestrator answered the learner query and return strict JSON.",
    }
    tool_chain = run_tool_calling_chain(
        stack_name="retrieval_orchestrator_chain",
        system_prompt="You are a retrieval-orchestration explainer for an English-learning AI demo. Use the provided state only, call relevant tools if needed, then explain the final answer.",
        payload=payload,
        user=state["user"],
        tool_names=["get_profile_memory", "get_study_snapshot", "rag_search", "vector_rag_search"],
    )
    result = run_json_chain(
        stack_name="retrieval_orchestrator_json",
        system_prompt="You are a retrieval-orchestration explainer for an English-learning AI demo. Use the provided state only and output strict JSON.",
        payload=payload,
        schema_model=RetrievalAnswerSchema,
    )
    final = dict(fallback)
    chain_result = result.get("result") or {}
    if result.get("enabled"):
        final.update(
            {
                "headline": chain_result.get("headline") or final["headline"],
                "summary": chain_result.get("summary") or final["summary"],
                "grounded_points": chain_result.get("grounded_points") or final["grounded_points"],
                "recommended_next_actions": chain_result.get("recommended_next_actions") or final["recommended_next_actions"],
            }
        )
    return {
        "result": final,
        "langchain_trace": (tool_chain.get("trace") or []) + (result.get("trace") or []),
        "runtime_stack": {
            **(tool_chain.get("runtime_stack") or {}),
            **(result.get("runtime_stack") or {}),
        },
    }


def _node_analyze_query(state: RetrievalOrchestratorState) -> Dict[str, Any]:
    return {"query_analysis": _build_query_analysis(state.get("query", ""))}


def _node_load_context(state: RetrievalOrchestratorState) -> Dict[str, Any]:
    user = state["user"]
    trace = [
        _invoke_tool(user, "get_profile_memory", {}, "读取 AI 长期学习画像"),
        _invoke_tool(user, "get_study_snapshot", {"days": 7}, "读取最近学习快照"),
    ]
    for item in trace:
        item["summary"] = _summarize_tool_result(item)
    return {"learner_context": {"profile_memory": trace[0]["result"], "study_snapshot": trace[1]["result"]}, "tool_trace": trace}


def _node_run_structured_rag(state: RetrievalOrchestratorState) -> Dict[str, Any]:
    user = state["user"]
    limit = min(max(int(state.get("limit", 6) or 6), 3), 8)
    tool_call = _invoke_tool(user, "rag_search", {"query": state.get("query", ""), "limit": limit}, "执行结构化 RAG，优先命中词条、语法点和句库中的明确内容")
    tool_call["summary"] = _summarize_tool_result(tool_call)
    knowledge = dict(state.get("knowledge") or {})
    knowledge["structured_rag"] = tool_call["result"]
    return {"knowledge": knowledge, "tool_trace": (state.get("tool_trace") or []) + [tool_call]}


def _node_run_hybrid_rag(state: RetrievalOrchestratorState) -> Dict[str, Any]:
    user = state["user"]
    limit = min(max(int(state.get("limit", 6) or 6), 3), 8)
    tool_call = _invoke_tool(user, "vector_rag_search", {"query": state.get("query", ""), "limit": limit, "retrieval_mode": "hybrid"}, "执行 Hybrid RAG，把结构化命中与向量召回融合后再排序")
    tool_call["summary"] = _summarize_tool_result(tool_call)
    knowledge = dict(state.get("knowledge") or {})
    knowledge["hybrid_rag"] = tool_call["result"]
    return {"knowledge": knowledge, "tool_trace": (state.get("tool_trace") or []) + [tool_call]}


def _node_select_strategy(state: RetrievalOrchestratorState) -> Dict[str, Any]:
    return {"selection": _build_selection(state)}


def _node_run_multi_agent(state: RetrievalOrchestratorState) -> Dict[str, Any]:
    return {"multi_agent": _build_multi_agent_story(state)}


def _node_summarize_result(state: RetrievalOrchestratorState) -> Dict[str, Any]:
    runtime = build_runtime_capabilities()
    final_payload = _generate_answer_with_langchain(state) if is_provider_ready() else {"result": _build_fallback_final_answer(state), "langchain_trace": [], "runtime_stack": {}}
    final_answer = final_payload["result"]
    selection = state.get("selection") or {}
    query_analysis = state.get("query_analysis") or {}
    knowledge = state.get("knowledge") or {}
    agent_flow = {
        "title": "LangGraph 检索编排 Multi-Agent",
        "inputs": [f"query：{state.get('query', '')}", f"focus：{query_analysis.get('focus_label', '通用检索')}", f"preferred_mode：{query_analysis.get('preferred_mode', 'hybrid')}"],
        "steps": [
            {"name": "planner", "detail": "问题分析员识别 query 焦点、关键词和 preferred_mode。"},
            {"name": "retriever", "detail": "检索执行员依次运行 structured 和 hybrid 检索。"},
            {"name": "coach", "detail": "学习教练将检索结果翻译成适合学习者的解释与后续建议。"},
            {"name": "supervisor", "detail": "总控协调者比较命中情况并选择主回答路径。"},
        ],
        "decision_highlights": [
            f"最终选择：{selection.get('selected_label', 'Hybrid RAG')}",
            f"structured_hits={selection.get('comparison', {}).get('structured_hits', 0)}",
            f"hybrid_hits={selection.get('comparison', {}).get('hybrid_hits', 0)} / dual_source_hits={selection.get('comparison', {}).get('dual_source_hits', 0)}",
        ],
        "graph_nodes": ["planner", "retriever_structured", "retriever_hybrid", "coach", "supervisor"],
    }
    return {
        "runtime": runtime,
        "final_answer": final_answer,
        "agent_flow": agent_flow,
        "headline": final_answer.get("headline", ""),
        "summary": final_answer.get("summary", ""),
        "selection": selection,
        "knowledge": {"structured_rag": knowledge.get("structured_rag") or {}, "hybrid_rag": knowledge.get("hybrid_rag") or {}},
        "langchain_trace": final_payload.get("langchain_trace") or [],
        "runtime_stack": final_payload.get("runtime_stack") or {},
    }


@lru_cache(maxsize=1)
def _build_graph():
    graph = StateGraph(RetrievalOrchestratorState)
    graph.add_node("analyze_query", _node_analyze_query)
    graph.add_node("load_context", _node_load_context)
    graph.add_node("run_structured_rag", _node_run_structured_rag)
    graph.add_node("run_hybrid_rag", _node_run_hybrid_rag)
    graph.add_node("select_strategy", _node_select_strategy)
    graph.add_node("run_multi_agent", _node_run_multi_agent)
    graph.add_node("synthesize_answer", _node_summarize_result)
    graph.add_edge(START, "analyze_query")
    graph.add_edge("analyze_query", "load_context")
    graph.add_edge("load_context", "run_structured_rag")
    graph.add_edge("run_structured_rag", "run_hybrid_rag")
    graph.add_edge("run_hybrid_rag", "select_strategy")
    graph.add_edge("select_strategy", "run_multi_agent")
    graph.add_edge("run_multi_agent", "synthesize_answer")
    graph.add_edge("synthesize_answer", END)
    return graph.compile()


def _run_pipeline(initial_state: RetrievalOrchestratorState) -> RetrievalOrchestratorState:
    state = dict(initial_state)
    state.update(_node_analyze_query(state))
    state.update(_node_load_context(state))
    state.update(_node_run_structured_rag(state))
    state.update(_node_run_hybrid_rag(state))
    state.update(_node_select_strategy(state))
    state.update(_node_run_multi_agent(state))
    state.update(_node_summarize_result(state))
    return state


def _run_graph(initial_state: RetrievalOrchestratorState) -> RetrievalOrchestratorState:
    if LANGGRAPH_AVAILABLE:
        return _build_graph().invoke(initial_state)
    return _run_pipeline(initial_state)


def build_retrieval_orchestrator_detail(user, query: str, limit: int = 6) -> Dict[str, Any]:
    state = _run_graph({"user": user, "query": str(query or "").strip(), "limit": min(max(int(limit or 6), 3), 8)})
    final_answer = state.get("final_answer") or {}
    return {
        "headline": state.get("headline", "") or final_answer.get("headline", ""),
        "summary": state.get("summary", "") or final_answer.get("summary", ""),
        "query_analysis": state.get("query_analysis", {}),
        "learner_context": state.get("learner_context", {}),
        "selection": state.get("selection", {}),
        "final_answer": final_answer,
        "knowledge": state.get("knowledge", {}),
        "tool_trace": [{"tool_name": item.get("tool_name", ""), "args": item.get("args", {}), "summary": item.get("summary", "")} for item in (state.get("tool_trace") or [])],
        "multi_agent": state.get("multi_agent", {}),
        "agent_flow": state.get("agent_flow", {}),
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
