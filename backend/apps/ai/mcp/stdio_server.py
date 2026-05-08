from __future__ import annotations

import re
from types import SimpleNamespace
from typing import Any, Dict

from mcp.server.fastmcp import FastMCP

from .registry import list_prompt_defs, list_resource_defs, list_tool_defs, execute_tool, read_resource


def _build_runtime_user() -> Any:
    return SimpleNamespace(id=0, is_authenticated=True, username="mcp_stdio_demo", is_mcp_stdio=True)


def create_stdio_server() -> FastMCP:
    server = FastMCP(
        name="english-word-miniapp-ai",
        instructions="English word miniapp AI MCP server for plans, RAG, grammar, and observability.",
    )

    for item in list_tool_defs():
        server.tool(name=item["name"], description=item["description"])(_make_tool_handler(item["name"]))

    for item in list_resource_defs():
        server.resource(
            uri=item["uri"],
            name=item["name"],
            description=f"{item['name']} resource placeholder for MCP discovery.",
            mime_type=item["mime_type"],
        )(_make_resource_handler(item["uri"]))

    for item in list_prompt_defs():
        server.prompt(name=item["name"], description=item["description"])(_make_prompt_handler(item["name"], item["arguments"]))

    return server


def _make_tool_handler(tool_name: str):
    def tool_handler(args: Dict[str, Any] | None = None) -> Dict[str, Any]:
        return execute_tool(_build_runtime_user(), tool_name, args or {})

    tool_handler.__name__ = f"tool_{tool_name}"
    return tool_handler


def _make_resource_handler(resource_uri: str):
    uri_params = re.findall(r"{([^}]+)}", resource_uri)
    namespace = {"resource_uri": resource_uri}
    if uri_params:
        params_sig = ", ".join(uri_params)
        params_value = uri_params[0]
        source = (
            f"def resource_handler({params_sig}):\n"
            f"    value = {params_value}\n"
            f"    resolved = resource_uri.replace('{{{params_value}}}', str(value))\n"
            "    return read_resource(_build_runtime_user(), resolved)\n"
        )
    else:
        source = (
            "def resource_handler():\n"
            "    return read_resource(_build_runtime_user(), resource_uri)\n"
        )
    namespace["read_resource"] = read_resource
    namespace["_build_runtime_user"] = _build_runtime_user
    exec(source, namespace)
    resource_handler = namespace["resource_handler"]
    resource_handler.__name__ = "resource_handler"
    return resource_handler


def _make_prompt_handler(prompt_name: str, arguments: list[dict[str, Any]]):
    if arguments:
        arg_names = [item["name"] for item in arguments]
        params_sig = ", ".join(f"{name}=None" for name in arg_names)
        params_obj = ", ".join(f"'{name}': {name}" for name in arg_names)
        namespace = {"prompt_name": prompt_name, "arguments": arguments}
        source = (
            f"def prompt_handler({params_sig}):\n"
            "    return {\n"
            "        'name': prompt_name,\n"
            "        'arguments': arguments,\n"
            f"        'values': {{{params_obj}}},\n"
            "        'message': f\"{prompt_name} prompt is exposed for MCP discovery and external orchestration.\",\n"
            "    }\n"
        )
        exec(source, namespace)
        prompt_handler = namespace["prompt_handler"]
    else:
        def prompt_handler() -> Dict[str, Any]:
            return {
                "name": prompt_name,
                "arguments": arguments,
                "message": f"{prompt_name} prompt is exposed for MCP discovery and external orchestration.",
            }

    prompt_handler.__name__ = f"prompt_{prompt_name}"
    return prompt_handler


def run_stdio_server() -> None:
    create_stdio_server().run("stdio")
