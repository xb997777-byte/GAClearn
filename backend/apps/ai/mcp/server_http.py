from ..compat import MCP_AVAILABLE
from .registry import execute_agent_safe_tool, execute_tool, get_tool_agent_meta, list_prompt_defs, list_resource_defs, list_tool_defs, read_resource


def build_mcp_blueprint():
    stdio_command = "python manage.py run_mcp_stdio_server"
    tools = list_tool_defs()
    resources = list_resource_defs()
    prompts = list_prompt_defs()
    return {
        "enabled": MCP_AVAILABLE,
        "advanced_available": True,
        "external_server_support": False,
        "capability_flags": {
            "tool_form_mode": True,
            "resource_read_mode": True,
            "prompt_catalog": True,
            "raw_json_debug": True,
            "external_mcp_registry": False,
        },
        "transport": "http",
        "transport_modes": ["http", "stdio"],
        "name": "english-word-miniapp-ai",
        "version": "0.4.0",
        "description": "英语单词微信小程序内部 AI 工具层，面向学习计划、词库、语法、RAG 和观测能力。",
        "manifest_endpoint": "/api/v1/ai/mcp/manifest",
        "tool_call_endpoint": "/api/v1/ai/mcp/tools/call",
        "stdio_command": stdio_command,
        "mcp_stdio_available": MCP_AVAILABLE,
        "tool_count": len(tools),
        "resource_count": len(resources),
        "prompt_count": len(prompts),
        "tools": tools,
        "resources": resources,
        "prompts": prompts,
    }


def call_mcp_tool(user, tool_name, args=None):
    return execute_tool(user, tool_name, args or {})


def call_mcp_tool_with_guard(user, tool_name, args=None, *, run=None, feature_type="mcp_tool_call", step=None):
    meta = get_tool_agent_meta(tool_name)
    if meta.get("requires_approval"):
        return execute_agent_safe_tool(
            user,
            tool_name,
            args or {},
            feature_type=feature_type,
            allowed_tools=[tool_name],
            run=run,
            step=step,
        )
    return call_mcp_tool(user, tool_name, args or {})


def read_mcp_resource(user, resource_uri):
    return read_resource(user, resource_uri)
