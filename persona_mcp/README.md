# persona_mcp — Logseq MCP integration

An MCP (Model Context Protocol) server that turns Logseq into a **persona knowledge
graph + memory** for the Persona stack: measure CEID, detect drift, store conversation
memory, and browse persona profiles — all backed by `persona_math` (and `needle`'s
PersonaNeedle when available).

> The package is named **`persona_mcp`** (not `mcp`) on purpose: a top-level `mcp/`
> package would shadow the `mcp` SDK on `sys.path`. Internal structure is otherwise as
> designed (`logseq/`, `tools/`, `templates/`).

## Tools (7)

| Tool | Does |
|---|---|
| `get_persona_profile` | K-layer vector + CEID reference + CEID history + recent conversations |
| `measure_persona_ceid` | CEID (C/E/I/D) for a conversation → auto-logged to Logseq/cache |
| `detect_drift` | identity-drift detection → red alert logged on drift |
| `add_conversation_memory` | append a conversation to the persona's page |
| `get_persona_history` | last N conversations + CEID history + delta |
| `list_personas` | list/filter personas (domain / tags / query) |
| `compare_personas` | two personas' K-layer distance + CEID profiles |

## Logseq setup

1. Install Logseq (logseq.com).
2. **Settings → Advanced → Developer mode**, then **Settings → Features → HTTP APIs server** (enable).
3. Start the API server (toolbar “API”), set **port 12315** and an **authorization token**.

## MCP setup

```bash
pip install -r persona_mcp/requirements.txt   # mcp, httpx, python-dateutil, jinja2
python persona_mcp/server.py                  # stdio server
```

## Claude Code integration (`.mcp.json`)

See `persona_mcp/mcp.json.example`:

```json
{
  "mcpServers": {
    "persona-mcp": {
      "command": "python",
      "args": ["persona_mcp/server.py"],
      "env": { "LOGSEQ_TOKEN": "your_token", "LOGSEQ_PORT": "12315" }
    }
  }
}
```

(No live `.mcp.json` is committed at the repo root, to avoid auto-spawning the server.)

## Architecture

- `logseq/client.py` — `LogseqClient` over the Logseq HTTP API (`POST /api`, Bearer token).
- `logseq/graph.py` — `PersonaGraph`: jinja2-rendered pages + **graceful degradation** (every
  write also goes to a durable local cache under `persona_mcp/.cache/`, so reads/writes work
  even when Logseq is down). `init_all_personas()` bulk-creates pages for the whole library.
- `logseq/templates/` — `persona_page.md`, `ceid_entry.md`, `conversation.md`.
- `tools/` — the 7 tools as SDK-free `{name, description, inputSchema, handler}` dicts.
- `server.py` — wires the tools into an MCP `Server` over stdio.

## Integration notes

- **Graceful degradation:** if Logseq isn't reachable, tools don't error — they fall back to
  the local cache (`LogseqUnavailable` is caught in `PersonaGraph`).
- **PersonaNeedle / torch optional:** `measure_persona_ceid` uses `needle.PersonaNeedle` when
  torch is installed; otherwise it falls back to `persona_math.ceid.ceid_score` (the reference).
  `detect_drift` returns a `degraded` result without torch (PersonaNeedle required).
- Every `measure_persona_ceid` call is logged to the persona's Logseq page / cache automatically.
- `PersonaGraph.init_all_personas()` creates a page for each of the ~500 library personas.

## Tests

`pytest persona_mcp/tests` — server/7-tool test (skips if the `mcp` SDK is absent), Logseq
client mock (no real Logseq), template render, graceful-degradation, and `persona_math`
integration (torch-free).
