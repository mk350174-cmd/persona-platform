"""
HPEP Studio API
===============
Matematiksel olarak doğrulanmış AI persona mühendisliği platformu.

Endpoints:
  POST /auth/register       → create account + API key
  GET  /me                  → current user info

  POST /workspaces          → create workspace
  GET  /workspaces          → list my workspaces
  GET  /workspaces/{id}     → workspace detail + limits

  POST /workspaces/{id}/personas              → create custom persona
  GET  /workspaces/{id}/personas              → list personas
  GET  /workspaces/{id}/personas/{pid}        → persona detail
  PUT  /workspaces/{id}/personas/{pid}        → update blocks/name
  DELETE /workspaces/{id}/personas/{pid}      → delete

  GET  /workspaces/{id}/personas/{pid}/ceid          → 4-axis CEID diagnostic
  GET  /workspaces/{id}/personas/{pid}/compare       → similarity vs another
  POST /workspaces/{id}/personas/{pid}/compile       → single platform+tier
  POST /workspaces/{id}/personas/{pid}/compile/all   → all combinations
  GET  /workspaces/{id}/personas/{pid}/export        → JSON/YAML/SDK/character-sheet

  GET  /library             → browse Persona Hub library (534 personas)
  POST /library/{id}/import → import library persona into workspace

  GET  /health              → system health
"""

import os
import logging
import time
from pathlib import Path

from fastapi import FastAPI, HTTPException, Depends, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, EmailStr
from sqlalchemy import text
from sqlalchemy.orm import Session
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from api.db import (
    init_db, get_db, create_user, get_user_by_email,
    get_user_by_api_key, User, Workspace, WorkspaceMember,
    CustomPersona, create_workspace,
)
from api import workspaces as ws_router_mod
from api import personas as persona_router_mod
from api import export as export_router_mod

from persona_math.persona_library import PERSONA_LIBRARY, search_personas
from persona_math.compiler import compile_persona, SUPPORTED_PLATFORMS, SUPPORTED_TIERS
from api.personas import _build_vector, _compute_ceid

# ── Logging ───────────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger("hpep_studio")

# ── Rate limiter ──────────────────────────────────────────────────────────────

limiter = Limiter(key_func=get_remote_address, default_limits=["1000/hour"])

# ── App ───────────────────────────────────────────────────────────────────────

_CORS_ORIGINS = [o.strip() for o in os.getenv("CORS_ORIGINS", "*").split(",")]

app = FastAPI(
    title="HPEP Studio API",
    description=(
        "Matematiksel olarak doğrulanmış AI persona mühendisliği. "
        "HPEP-100 vektörleri, CEID kalite skoru, çoklu platform derleme."
    ),
    version="1.0.0",
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    start = time.time()
    response = await call_next(request)
    ms = round((time.time() - start) * 1000)
    logger.info("%s %s %s %dms", request.method, request.url.path, response.status_code, ms)
    return response


@app.on_event("startup")
def startup():
    init_db()
    logger.info("HPEP Studio started — %d library personas available", len(PERSONA_LIBRARY))


from api.auth import get_current_user  # noqa: E402 — after app creation

# ── Include routers ───────────────────────────────────────────────────────────

app.include_router(ws_router_mod.router)
app.include_router(persona_router_mod.router)
app.include_router(export_router_mod.router)

# ── Auth endpoints ────────────────────────────────────────────────────────────

class RegisterRequest(BaseModel):
    email: EmailStr
    workspace_name: str = "My Workspace"


@app.post("/auth/register", tags=["auth"])
@limiter.limit("5/hour")
def register(body: RegisterRequest, request: Request, db: Session = Depends(get_db)):
    if get_user_by_email(db, body.email):
        raise HTTPException(409, "Email already registered.")
    user = create_user(db, body.email)
    ws = create_workspace(db, body.workspace_name, user)
    return {
        "api_key":      user.api_key,
        "email":        user.email,
        "workspace_id": ws.id,
        "workspace_name": ws.name,
        "plan":         ws.plan_tier,
        "note": "Store your API key — it won't be shown again.",
    }


@app.get("/me", tags=["auth"])
def me(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    memberships = db.query(WorkspaceMember).filter(
        WorkspaceMember.user_id == user.id
    ).all()
    workspace_ids = [m.workspace_id for m in memberships]
    return {
        "email":       user.email,
        "created_at":  user.created_at.isoformat() if user.created_at else None,
        "workspace_ids": workspace_ids,
    }


# ── Library (Persona Hub bridge) ──────────────────────────────────────────────

@app.get("/library", tags=["library"])
def browse_library(
    q: str = "", domain: str = "", limit: int = 50, offset: int = 0,
    _: User = Depends(get_current_user),
):
    """Browse the built-in 534-persona library."""
    results = search_personas(q, domain=domain or None)
    paginated = results[offset: offset + limit]
    return {
        "personas": paginated,
        "total":    len(PERSONA_LIBRARY),
        "query":    q,
    }


@app.post("/workspaces/{workspace_id}/personas/import/{library_id}", tags=["library"])
def import_library_persona(
    workspace_id: str,
    library_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Copy a library persona into your workspace as a custom persona."""
    spec = PERSONA_LIBRARY.get(library_id)
    if not spec:
        raise HTTPException(404, f"Library persona '{library_id}' not found.")

    member = db.query(WorkspaceMember).filter(
        WorkspaceMember.workspace_id == workspace_id,
        WorkspaceMember.user_id == user.id,
    ).first()
    if not member:
        raise HTTPException(404, "Workspace not found or access denied.")

    import json
    raw_blocks = spec.get("blocks", {})
    blocks = {int(k): float(v) for k, v in raw_blocks.items()}

    # Convert block dict to B1-B10 float activations
    block_dict = {i: blocks.get(i, 0.5) for i in range(1, 11)}
    P = _build_vector(block_dict, {})
    score = _compute_ceid(P)

    p = CustomPersona(
        workspace_id=workspace_id,
        name=f"{spec['name']} (imported)",
        description=spec.get("tagline", ""),
        blocks_json=json.dumps(block_dict),
        ceid_score=score,
        is_public=False,
    )
    db.add(p)
    db.commit()
    db.refresh(p)
    return {
        "status": "imported",
        "persona_id": p.id,
        "ceid_score": score,
        "source_library_id": library_id,
    }


# ── Health ────────────────────────────────────────────────────────────────────

@app.get("/health", tags=["system"])
def health(db: Session = Depends(get_db)):
    try:
        db.execute(text("SELECT 1"))
        db_ok = True
    except Exception:
        db_ok = False
    return {
        "status":          "ok" if db_ok else "degraded",
        "version":         "1.0.0",
        "db":              db_ok,
        "library_personas": len(PERSONA_LIBRARY),
        "platforms":       SUPPORTED_PLATFORMS,
        "tiers":           SUPPORTED_TIERS,
    }
