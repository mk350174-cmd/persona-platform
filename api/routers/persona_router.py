from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect, status

from ..persona_catalog import CATALOG, PersonaCatalogEntry
from ..schemas import PersonaSummary, PersonaDetail, CEIDMeasureRequest
from ..deps import get_current_user
from ..db import User, ChatMessage

router = APIRouter(prefix="/personas", tags=["personas"])

_graph = None


def _get_graph():
    """Lazy singleton PersonaGraph (persona_mcp), cache_dir under ./data so
    it survives restarts without needing a live Logseq instance."""
    global _graph
    if _graph is None:
        from persona_mcp.logseq import PersonaGraph
        _graph = PersonaGraph(client=None, cache_dir="data/persona_mcp_cache")
    return _graph


def _entry_or_404(persona_id: str) -> PersonaCatalogEntry:
    entry = CATALOG.get(persona_id)
    if entry is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Unknown persona: {persona_id}")
    return entry


@router.get("/", response_model=list[PersonaSummary])
def list_personas():
    return [
        PersonaSummary(
            persona_id=e.persona_id, name=e.name, description=e.description,
            is_historical=e.is_historical, k_layer_available=e.k_layer_available,
        )
        for e in CATALOG.values()
    ]


@router.get("/{persona_id}", response_model=PersonaDetail)
def get_persona(persona_id: str):
    e = _entry_or_404(persona_id)
    return PersonaDetail(
        persona_id=e.persona_id, name=e.name, description=e.description,
        is_historical=e.is_historical, k_layer_available=e.k_layer_available,
        model=e.model, has_disclosure=e.has_disclosure, hpep100_blocks=e.hpep100_blocks,
    )


@router.post("/{persona_id}/ceid")
def measure_ceid(persona_id: str, body: CEIDMeasureRequest,
                  user: User = Depends(get_current_user)):
    """Measure CEID for a conversation snippet. Wraps persona_mcp's
    measure_persona_ceid (ADR 0001 T2-003 — REST wrapper, not a live MCP
    client). The `untrained` flag is ALWAYS surfaced to the caller
    (T2-018) — never hidden, per CLAUDE.md's honest-tier discipline.
    """
    e = _entry_or_404(persona_id)
    if not e.k_layer_available:
        return {
            "persona_id": persona_id, "ceid": {}, "untrained": True,
            "source": "unavailable (no K-layer vector for this persona)",
            "warning": (
                f"'{persona_id}' has no entry in the 495-persona K-layer "
                f"library (confirmed absent, not just unmapped — see "
                f"api/persona_catalog.py). CEID measurement is not possible."
            ),
        }
    import warnings
    from persona_mcp.tools.persona_tools import measure_persona_ceid as _measure

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        result = _measure({"persona_id": e.k_layer_key, "conversation": body.conversation},
                           _get_graph())
    if caught:
        result["engine_warnings"] = [str(w.message) for w in caught]
    return result


@router.websocket("/{persona_id}/chat")
async def chat_websocket(websocket: WebSocket, persona_id: str, token: str | None = None):
    """Real-time chat. Auth via `?token=<JWT>` query param (WebSocket has no
    header-based bearer auth in browsers) — T2-016.

    **Scope (2026-07-30):** this endpoint echoes + logs turns and reports the
    persona's `k_layer_available`/`untrained` status; it does not generate
    real LLM completions (that requires wiring an actual model provider,
    tracked separately — Faz 4 continuation). Do not present this as a
    finished chat product; it validates the transport + auth + persistence
    path honestly, nothing more.
    """
    from ..security import decode_access_token
    from ..db import SessionLocal

    entry = CATALOG.get(persona_id)
    if entry is None:
        await websocket.close(code=4404, reason=f"Unknown persona: {persona_id}")
        return
    user_id = decode_access_token(token) if token else None
    if user_id is None:
        await websocket.close(code=4401, reason="Missing or invalid token")
        return

    await websocket.accept()
    db = SessionLocal()
    try:
        await websocket.send_json({
            "type": "session_start", "persona_id": persona_id,
            "k_layer_available": entry.k_layer_available,
            "untrained": True,
            "note": "echo-only transport validation, no LLM completion wired yet",
        })
        while True:
            text = await websocket.receive_text()
            db.add(ChatMessage(user_id=user_id, persona_id=persona_id, role="user", content=text))
            reply = f"[{entry.name} — echo, no LLM wired] {text}"
            db.add(ChatMessage(user_id=user_id, persona_id=persona_id, role="persona", content=reply))
            db.commit()
            await websocket.send_json({"type": "message", "role": "persona", "content": reply})
    except WebSocketDisconnect:
        pass
    finally:
        db.close()
