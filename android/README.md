# PersonaNeedle — Android integration

Runtime to run INT4 GGUF persona bundles on-device (CEID / drift / voice) and sync results
back to the Python `persona_mcp` server (→ Logseq).

## Requirements
- Android Studio Hedgehog+, NDK 25+
- A llama.cpp Android JNI binding (see `dependencies_note.txt`)

## Setup
1. Bundle personas: `python -m needle.pipeline.bulk_bundler --output needle/bundles/`.
2. Copy `needle/bundles/{persona_id}/` into `android/src/main/assets/personas/{persona_id}/`.
3. Add the deps from `dependencies_note.txt` to `app/build.gradle.kts`.
4. Start `PersonaNeedleRuntime` from your Activity / ViewModel.

## MCP connection
`Android → McpBridge → Python persona_mcp server → Logseq`

Start the server: `python -m persona_mcp.server` (stdio) or, for the WebSocket bridge,
run it behind a `ws://host:8765` endpoint (see `McpBridge`, default `http://localhost:8765`).

## Example (Kotlin)
```kotlin
val runtime = PersonaNeedleRuntime(context)
runtime.loadPersona("socrates")
val ceid = runtime.measureCeid("socrates", conversation)
// ceid.I → identity stability ; ceid.D → drift resistance ; ceid.isUntrained → placeholder?
```

## Files
```
android/
├── __init__.py                 # so the Python compat tests are collectable
├── README.md
├── runtime/
│   ├── PersonaNeedleRuntime.kt  # load / measureCeid / detectDrift / generateVoice / unload
│   ├── McpBridge.kt             # WebSocket + HTTP bridge to persona_mcp
│   └── PersonaAssetManager.kt   # assets/personas/ discovery + cache extraction
├── dependencies_note.txt
└── tests/test_android_compat.py # torch-free Python checks (manifest/assets/GGUF/catalog/URL)
```

## Manifest field mapping (Python → Kotlin)
The Python bundle `manifest.json` is snake_case; `PersonaAssetManager` maps it:
`total_size_mb → sizeMb`, `untrained → isUntrained`, `components → components`.

## Integration
- `needle/finetune/export/android_export.py` lays bundles into the assets tree.
- `needle/pipeline/bulk_bundler.py` produces the per-persona bundles + `catalog.json`.
- `persona_mcp/server.py` is the MCP endpoint `McpBridge` talks to.

**Nothing here is compiled in this repo** — the Kotlin is integration scaffold; only the
torch-free Python compatibility tests run in CI.
