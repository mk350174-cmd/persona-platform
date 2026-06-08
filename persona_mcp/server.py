"""
persona-mcp — MCP server (stdio) exposing the Persona stack to Logseq / Claude Code.

Run: ``python persona_mcp/server.py`` (env: ``LOGSEQ_PORT`` default 12315,
``LOGSEQ_TOKEN``). Registers the 7 tools from ``persona_mcp.tools``. Requires the
``mcp`` SDK (``persona_mcp/requirements.txt``); the rest of the package imports without it.
"""

from __future__ import annotations

import asyncio
import json
import os

from mcp.server import Server
from mcp.server.stdio import stdio_server
import mcp.types as types

from .logseq import LogseqClient, PersonaGraph
from .tools import ALL_TOOLS, DISPATCH


def build_graph() -> PersonaGraph:
    port = os.environ.get("LOGSEQ_PORT", "12315")
    token = os.environ.get("LOGSEQ_TOKEN")
    client = LogseqClient(base_url=f"http://localhost:{port}/api", token=token)
    return PersonaGraph(client=client)


def build_server(graph: PersonaGraph | None = None) -> Server:
    graph = graph or build_graph()
    server = Server("persona-mcp")

    @server.list_tools()
    async def _list_tools() -> list[types.Tool]:
        return [types.Tool(name=t["name"], description=t["description"],
                           inputSchema=t["inputSchema"]) for t in ALL_TOOLS]

    @server.call_tool()
    async def _call_tool(name: str, arguments: dict) -> list[types.TextContent]:
        handler = DISPATCH.get(name)
        if handler is None:
            result = {"error": f"unknown tool: {name}"}
        else:
            try:
                result = handler(arguments or {}, graph)
            except Exception as exc:  # never crash the server on a tool error
                result = {"error": str(exc), "tool": name}
        return [types.TextContent(type="text", text=json.dumps(result, ensure_ascii=False))]

    return server


async def _amain() -> None:
    server = build_server()
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


def main() -> None:
    asyncio.run(_amain())


if __name__ == "__main__":
    main()
