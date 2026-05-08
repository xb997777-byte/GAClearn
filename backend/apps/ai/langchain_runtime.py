from __future__ import annotations

import json
import os
from time import monotonic
from typing import Any, Dict, List, Optional, Type

from pydantic import BaseModel, Field, create_model

from .compat import ChatOpenAI, LANGCHAIN_CORE_AVAILABLE, LANGCHAIN_OPENAI_AVAILABLE
from .mcp.registry import execute_tool, list_tool_defs

try:
    from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
    from langchain_core.output_parsers import JsonOutputParser
    from langchain_core.prompts import ChatPromptTemplate
    from langchain_core.tools import StructuredTool

    LANGCHAIN_EXPLICIT_RUNTIME_AVAILABLE = True
except ImportError:
    AIMessage = HumanMessage = SystemMessage = ToolMessage = None
    JsonOutputParser = ChatPromptTemplate = StructuredTool = None
    LANGCHAIN_EXPLICIT_RUNTIME_AVAILABLE = False


class TraceCollector:
    def __init__(self, stack_name: str):
        self.stack_name = stack_name
        self.events: List[Dict[str, Any]] = []
        self.runtime_stack = {
            "stack_name": stack_name,
            "langchain": bool(LANGCHAIN_EXPLICIT_RUNTIME_AVAILABLE),
            "tool_calling": bool(LANGCHAIN_EXPLICIT_RUNTIME_AVAILABLE),
            "output_parser": bool(LANGCHAIN_EXPLICIT_RUNTIME_AVAILABLE),
        }

    def add(self, phase: str, name: str, detail: str = "", status: str = "success", **meta) -> None:
        self.events.append(
            {
                "phase": phase,
                "name": name,
                "detail": detail,
                "status": status,
                "latency_ms": int(meta.pop("latency_ms", 0) or 0),
                **({"meta": meta} if meta else {}),
            }
        )


def langchain_explicit_available() -> bool:
    return LANGCHAIN_EXPLICIT_RUNTIME_AVAILABLE and LANGCHAIN_OPENAI_AVAILABLE and LANGCHAIN_CORE_AVAILABLE


def build_langchain_capabilities() -> Dict[str, Any]:
    return {
        "langchain_explicit_available": langchain_explicit_available(),
        "langchain_tool_calling_available": langchain_explicit_available(),
        "langchain_trace_available": langchain_explicit_available(),
    }


def get_chat_model():
    if not langchain_explicit_available():
        raise RuntimeError("LangChain explicit runtime is not available")
    return ChatOpenAI(
        api_key=os.getenv("AI_API_KEY", "").strip(),
        model=os.getenv("AI_MODEL", "").strip(),
        base_url=os.getenv("AI_BASE_URL", "https://api.openai.com/v1").strip().rstrip("/"),
        temperature=0.2,
    )


def _schema_type(schema: Dict[str, Any]) -> Any:
    raw_type = schema.get("type", "string")
    if raw_type == "integer":
        return int
    if raw_type == "boolean":
        return bool
    if raw_type == "array":
        return list[str]
    return str


def _build_input_model(tool_name: str, input_schema: Dict[str, Any]) -> Type[BaseModel]:
    fields = {}
    properties = (input_schema or {}).get("properties", {}) or {}
    required = set((input_schema or {}).get("required", []) or [])
    for key, schema in properties.items():
        py_type = _schema_type(schema)
        default = ... if key in required else None
        fields[key] = (Optional[py_type] if default is None else py_type, Field(default=default, description=schema.get("description", "")))
    return create_model(f"{tool_name.title().replace('_', '')}Input", **fields)  # type: ignore[arg-type]


def make_structured_tools(user, trace: TraceCollector | None = None) -> List[Any]:
    if not langchain_explicit_available():
        return []
    tools = []
    for item in list_tool_defs():
        input_model = _build_input_model(item["name"], item.get("input_schema", {}))

        def _make_invoke(_tool_name=item["name"], _trace=trace, _input_model=input_model):
            def _invoke(**kwargs):
                started = monotonic()
                payload = _input_model(**kwargs) if kwargs else _input_model()
                args = payload.model_dump(exclude_none=True)
                if _trace:
                    _trace.add("tool_start", _tool_name, detail="LangChain StructuredTool invoke", args=args)
                result = execute_tool(user, _tool_name, args)
                if _trace:
                    _trace.add(
                        "tool_end",
                        _tool_name,
                        detail="Tool completed",
                        latency_ms=int((monotonic() - started) * 1000),
                        args=args,
                    )
                return json.dumps(result, ensure_ascii=False, default=str)

            return _invoke

        tools.append(
            StructuredTool.from_function(
                func=_make_invoke(),
                name=item["name"],
                description=item["description"],
                args_schema=input_model,
                return_direct=False,
            )
        )
    return tools


def build_tool_executor(user, trace: TraceCollector | None = None):
    def _execute(tool_name: str, args: Dict[str, Any] | None = None) -> Dict[str, Any]:
        started = monotonic()
        payload = args or {}
        if trace:
            trace.add("tool_start", tool_name, detail="LangChain direct tool executor", args=payload)
        result = execute_tool(user, tool_name, payload)
        if trace:
            trace.add(
                "tool_end",
                tool_name,
                detail="Tool completed",
                latency_ms=int((monotonic() - started) * 1000),
                args=payload,
            )
        return result

    return _execute


def run_tool_calling_chain(
    *,
    stack_name: str,
    system_prompt: str,
    payload: Dict[str, Any],
    user,
    tool_names: Optional[List[str]] = None,
) -> Dict[str, Any]:
    trace = TraceCollector(stack_name)
    if not langchain_explicit_available() or AIMessage is None or HumanMessage is None or SystemMessage is None or ToolMessage is None:
        return {"enabled": False, "trace": trace.events, "runtime_stack": trace.runtime_stack, "result": {}}

    tools = make_structured_tools(user, trace)
    if tool_names:
        tools = [item for item in tools if getattr(item, "name", "") in set(tool_names)]
    if not tools:
        return {"enabled": False, "trace": trace.events, "runtime_stack": trace.runtime_stack, "result": {}}

    model = get_chat_model().bind_tools(tools, parallel_tool_calls=False, strict=False)
    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=json.dumps(payload, ensure_ascii=False, default=str)),
    ]

    started = monotonic()
    trace.add("chain_start", stack_name, detail="Tool calling chain start")
    last_response: AIMessage | None = None
    for _ in range(3):
        response = model.invoke(messages)
        last_response = response
        tool_calls = list(getattr(response, "tool_calls", None) or [])
        trace.add(
            "chain_step",
            stack_name,
            detail="LLM response received",
            latency_ms=0,
            tool_calls=len(tool_calls),
        )
        messages.append(response)
        if not tool_calls:
            break

        for call in tool_calls:
            tool_name = call.get("name", "") if isinstance(call, dict) else getattr(call, "name", "")
            args = call.get("args") or {}
            tool_id = call.get("id", tool_name) if isinstance(call, dict) else getattr(call, "id", tool_name)
            started_tool = monotonic()
            trace.add("tool_start", tool_name, detail="LangChain tool call", args=args)
            result = execute_tool(user, tool_name, args)
            trace.add(
                "tool_end",
                tool_name,
                detail="Tool call completed",
                latency_ms=int((monotonic() - started_tool) * 1000),
                args=args,
            )
            messages.append(ToolMessage(content=json.dumps(result, ensure_ascii=False, default=str), tool_call_id=tool_id))

    trace.add("chain_end", stack_name, detail="Tool calling chain end", latency_ms=int((monotonic() - started) * 1000))
    last_tool_calls = list(getattr(last_response, "tool_calls", None) or []) if last_response is not None else []
    return {
        "enabled": True,
        "trace": trace.events,
        "runtime_stack": trace.runtime_stack,
        "result": {
            "content": getattr(last_response, "content", "") if last_response is not None else "",
            "tool_calls": [
                item.get("name", "") if isinstance(item, dict) else getattr(item, "name", "")
                for item in last_tool_calls
            ],
        },
    }


def run_json_chain(*, stack_name: str, system_prompt: str, payload: Dict[str, Any], schema_model: type[BaseModel]) -> Dict[str, Any]:
    trace = TraceCollector(stack_name)
    if not langchain_explicit_available():
        return {"enabled": False, "trace": trace.events, "runtime_stack": trace.runtime_stack, "result": {}}

    parser = JsonOutputParser(pydantic_object=schema_model)
    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", system_prompt),
            ("user", "{payload}"),
        ]
    )
    model = get_chat_model()
    chain = prompt | model | parser

    started = monotonic()
    trace.add("chain_start", stack_name, detail="LCEL chain start")
    trace.add("parser_start", schema_model.__name__, detail="JsonOutputParser prepare")
    result = chain.invoke({"payload": json.dumps(payload, ensure_ascii=False, default=str)})
    trace.add("parser_end", schema_model.__name__, detail="JsonOutputParser complete")
    trace.add("chain_end", stack_name, detail="LCEL chain end", latency_ms=int((monotonic() - started) * 1000))
    return {
        "enabled": True,
        "trace": trace.events,
        "runtime_stack": trace.runtime_stack,
        "result": result,
    }
