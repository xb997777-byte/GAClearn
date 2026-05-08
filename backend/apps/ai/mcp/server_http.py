from ..compat import MCP_AVAILABLE
from .registry import execute_tool, list_prompt_defs, list_resource_defs, list_tool_defs, read_resource


def build_mcp_blueprint():
    stdio_command = "python manage.py run_mcp_stdio_server"
    tools = list_tool_defs()
    resources = list_resource_defs()
    prompts = list_prompt_defs()
    return {
        "enabled": MCP_AVAILABLE,
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


def read_mcp_resource(user, resource_uri):
    return read_resource(user, resource_uri)
