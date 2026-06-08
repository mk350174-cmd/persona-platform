"""
persona_mcp — Logseq MCP integration for the Persona stack.

`import persona_mcp` works **without** the `mcp` SDK: the Logseq client, knowledge-graph
and tool registry load eagerly; the SDK-backed `build_server` / `main` load lazily.
(The package is named `persona_mcp`, not `mcp`, to avoid shadowing the `mcp` SDK on
`sys.path`.)
"""

from .logseq import LogseqClient, LogseqUnavailable, PersonaGraph
from .tools import ALL_TOOLS, DISPATCH

__version__ = "0.1.0"
__all__ = [
    "LogseqClient", "LogseqUnavailable", "PersonaGraph",
    "ALL_TOOLS", "DISPATCH", "build_server", "main",
]


def __getattr__(name):  # lazy SDK-backed server
    if name in ("build_server", "main", "build_graph"):
        from . import server
        return getattr(server, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
