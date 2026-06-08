"""
Memory MCP tools (2): add_conversation_memory, get_persona_history.

Plain dict tools (SDK-free); handlers take ``(arguments, graph)`` → dict.
"""

from __future__ import annotations


def add_conversation_memory(arguments: dict, graph) -> dict:
    pid = arguments["persona_id"]
    conversation = arguments["conversation"]
    metadata = arguments.get("metadata") or {}
    tags = metadata.get("tags") if isinstance(metadata, dict) else None
    res = graph.add_memory(pid, conversation, tags=tags, metadata=metadata)
    return {"persona_id": pid, "added": True, "backend": res["backend"]}


def get_persona_history(arguments: dict, graph) -> dict:
    pid = arguments["persona_id"]
    limit = int(arguments.get("limit", 10))
    ceid = graph.get_ceid_history(pid, limit=limit)
    delta = None
    if len(ceid) >= 2:
        first = ceid[0].get("composite", ceid[0].get("C"))
        last = ceid[-1].get("composite", ceid[-1].get("C"))
        if first is not None and last is not None:
            delta = round(float(last) - float(first), 4)
    return {
        "persona_id": pid,
        "ceid_history": ceid,
        "ceid_delta": delta,
        "conversations": graph.get_memories(pid, limit=limit),
        "drift_events": graph.get_drift_events(pid),
    }


TOOLS = [
    {"name": "add_conversation_memory",
     "description": "Append a conversation to the persona's Logseq page (or local cache).",
     "inputSchema": {"type": "object", "properties": {
         "persona_id": {"type": "string"}, "conversation": {"type": "string"},
         "metadata": {"type": "object"}}, "required": ["persona_id", "conversation"]},
     "handler": add_conversation_memory},
    {"name": "get_persona_history",
     "description": "Last N conversations + CEID history and the CEID delta over that window.",
     "inputSchema": {"type": "object", "properties": {
         "persona_id": {"type": "string"}, "limit": {"type": "integer", "default": 10}},
         "required": ["persona_id"]},
     "handler": get_persona_history},
]
