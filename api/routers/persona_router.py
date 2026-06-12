"""
persona_router — FastAPI endpoints bridging the platform to PersonaNeedle / persona_math.

Routes (mounted under /api/v1 in api.main):
    GET  /personas/                  → list personas (optionally filtered)
    GET  /personas/{id}/profile      → K-layer + reference CEID
    POST /personas/{id}/ceid         → measure CEID for a conversation
    POST /personas/{id}/drift        → detect identity drift
    POST /personas/{id}/voice        → generate text in the persona's voice
    GET  /personas/{id}/history      → CEID / drift / conversation history (from persona_mcp graph)

Import-safe without torch (needle_service is lazy + falls back to persona_math). Unknown
personas raise HTTP 404.
"""

from __future__ import annotations

from typing import Optional
from pathlib import Path

import numpy as np
from fastapi import APIRouter, HTTPException, Depends, Header, Request
from fastapi.responses import FileResponse
from pydantic import BaseModel
from slowapi import Limiter
from slowapi.util import get_remote_address

from api import needle_service
from api.auth import get_current_user, require_persona_access
from persona_math.persona_library import get_library_persona, PERSONA_LIBRARY, search_personas

router = APIRouter(tags=["personas"])

# Rate limiter for image downloads (50 per hour per IP)
_image_limiter = Limiter(key_func=get_remote_address)


class ConversationBody(BaseModel):
    conversation: str


class PromptBody(BaseModel):
    prompt: str


def _require(persona_id: str) -> None:
    if persona_id not in PERSONA_LIBRARY:
        raise HTTPException(status_code=404, detail=f"persona not found: {persona_id}")


@router.get("/personas/")
def list_personas(domain: Optional[str] = None, query: str = ""):
    if domain or query:
        specs = search_personas(query=query, domain=domain)
    else:
        specs = [PERSONA_LIBRARY[k] for k in sorted(PERSONA_LIBRARY)]
    out = [{"id": s["id"], "domain": s.get("domain"), "tags": s.get("tags")} for s in specs]
    return {"count": len(out), "personas": out[:500]}


@router.get("/personas/{persona_id}/profile")
def get_persona_profile(persona_id: str):
    _require(persona_id)
    P = np.asarray(get_library_persona(persona_id), dtype=float)
    return {"persona_id": persona_id, "k_layer_dim": int(P.shape[0]),
            "k_layer_preview": [round(float(x), 3) for x in P[:8]],
            "ceid_reference": needle_service._ceid_reference(P)}


@router.post("/personas/{persona_id}/ceid")
def post_ceid(persona_id: str, body: ConversationBody):
    _require(persona_id)
    return {"persona_id": persona_id, **needle_service.measure_ceid(persona_id, body.conversation)}


@router.post("/personas/{persona_id}/drift")
def post_drift(persona_id: str, body: ConversationBody):
    _require(persona_id)
    return {"persona_id": persona_id, **needle_service.detect_drift(persona_id, body.conversation)}


@router.post("/personas/{persona_id}/voice")
def post_voice(persona_id: str, body: PromptBody):
    _require(persona_id)
    return {"persona_id": persona_id, **needle_service.generate_voice(persona_id, body.prompt)}


@router.get("/personas/{persona_id}/history")
def get_persona_history(persona_id: str):
    _require(persona_id)
    # bridge to the persona_mcp knowledge-graph (local cache; graceful degradation)
    from persona_mcp.logseq import PersonaGraph
    g = PersonaGraph(client=None)
    return {
        "persona_id": persona_id,
        "ceid_history": g.get_ceid_history(persona_id, limit=20),
        "drift_events": g.get_drift_events(persona_id),
        "conversations": g.get_memories(persona_id, limit=20),
    }


@router.get("/personas/{persona_id}/image")
@_image_limiter.limit("50/hour")
def get_persona_image(
    persona_id: str,
    current_user = Depends(get_current_user),
    x_api_key: Optional[str] = Header(None),
    request: Request = None,
):
    """
    Get persona portrait image (authenticated, rate-limited to 50/hour per IP).

    Requires:
    - Valid API key (X-API-Key header)
    - User has purchased persona or has admin access

    Returns:
    - PNG image file
    - 404 if persona not found or image missing
    - 403 if not authenticated/authorized
    - 429 if rate limit exceeded
    """
    _require(persona_id)

    # Require persona access (checks purchase/subscription)
    access = require_persona_access(current_user, persona_id)
    if not access:
        raise HTTPException(status_code=403, detail="Not authorized to access this persona")

    # Construct image path
    demo_dir = Path(__file__).parent.parent.parent / "demo"
    assets_dir = demo_dir / "assets"
    img_path = assets_dir / "personas" / f"{persona_id}.png"

    # Return image if exists
    if img_path.exists():
        return FileResponse(
            path=img_path,
            media_type="image/png",
            headers={
                "Cache-Control": "public, max-age=86400, immutable",
                "ETag": f'"{persona_id}-{int(img_path.stat().st_mtime)}"',
            }
        )
    else:
        raise HTTPException(status_code=404, detail=f"Image not found for persona: {persona_id}")
