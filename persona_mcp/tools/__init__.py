"""MCP tools registry (8 tools: 6 persona + 2 memory)."""
from . import persona_tools, memory_tools

ALL_TOOLS = persona_tools.TOOLS + memory_tools.TOOLS
DISPATCH = {t["name"]: t["handler"] for t in ALL_TOOLS}

__all__ = ["ALL_TOOLS", "DISPATCH", "persona_tools", "memory_tools"]
