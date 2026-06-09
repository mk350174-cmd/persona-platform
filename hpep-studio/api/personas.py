"""
Custom persona CRUD — block specs → HPEP vector → CEID → compile.
"""

import json
import numpy as np
from typing import Optional

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from api.db import (
    get_db, CustomPersona, PersonaVersion, Workspace, User,
    get_workspace, PLAN_LIMITS,
)
from api.auth import get_current_user

# persona_math imports
from persona_math.foundation import vector_p
from persona_math.ceid import ceid_score, ceid_full_diagnostic
from persona_math.compiler import (
    compile_persona, compile_all_platforms, compile_all_tiers,
    SUPPORTED_PLATFORMS, SUPPORTED_TIERS,
)
from persona_math.metrics import cosine_similarity, drift as drift_metric

router = APIRouter(prefix="/workspaces/{workspace_id}/personas", tags=["personas"])


def _jsonify(obj):
    """Recursively convert numpy scalars to Python native types for JSON serialization."""
    if isinstance(obj, np.integer):
        return int(obj)
    if isinstance(obj, np.floating):
        return float(obj)
    if isinstance(obj, np.bool_):
        return bool(obj)
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    if isinstance(obj, dict):
        return {k: _jsonify(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_jsonify(v) for v in obj]
    return obj


# ── Schemas ───────────────────────────────────────────────────────────────────

class BlockSpec(BaseModel):
    """B1-B10 block activation levels (0.0 – 1.0)."""
    B1:  float = Field(0.5, ge=0.0, le=1.0, description="Power / Instrumental Rationality")
    B2:  float = Field(0.5, ge=0.0, le=1.0, description="Strategic Planning")
    B3:  float = Field(0.5, ge=0.0, le=1.0, description="Realist Epistemology")
    B4:  float = Field(0.5, ge=0.0, le=1.0, description="Rhetoric / Persuasion")
    B5:  float = Field(0.5, ge=0.0, le=1.0, description="Psychological Depth")
    B6:  float = Field(0.5, ge=0.0, le=1.0, description="Temporal Reasoning")
    B7:  float = Field(0.5, ge=0.0, le=1.0, description="Systemic Analysis")
    B8:  float = Field(0.5, ge=0.0, le=1.0, description="Cognitive Flexibility")
    B9:  float = Field(0.5, ge=0.0, le=1.0, description="Ethics / Prosociality")
    B10: float = Field(0.5, ge=0.0, le=1.0, description="Meta-cognition / Self-model")

    def to_dict(self) -> dict:
        return {i+1: v for i, v in enumerate([
            self.B1, self.B2, self.B3, self.B4, self.B5,
            self.B6, self.B7, self.B8, self.B9, self.B10
        ])}


class PersonaCreate(BaseModel):
    name:          str = Field(..., min_length=1, max_length=128)
    description:   Optional[str] = None
    blocks:        BlockSpec = Field(default_factory=BlockSpec)
    k_overrides:   Optional[dict[str, float]] = Field(
        None,
        description="K-layer fine-tuning: {\"0\": 0.95, \"11\": 0.88, ...} (K0-K99)"
    )
    is_public:     bool = False


class PersonaUpdate(BaseModel):
    name:        Optional[str] = Field(None, min_length=1, max_length=128)
    description: Optional[str] = None
    blocks:      Optional[BlockSpec] = None
    k_overrides: Optional[dict[str, float]] = None
    is_public:   Optional[bool] = None


class CompileRequest(BaseModel):
    platform: str = Field("claude", description=f"One of: {SUPPORTED_PLATFORMS}")
    tier:     str = Field("standard", description=f"One of: {SUPPORTED_TIERS}")


# ── Vector builder ────────────────────────────────────────────────────────────

def _build_vector(blocks: dict, k_overrides: dict) -> np.ndarray:
    """Convert B1-B10 block dict + K-overrides → 100-dim HPEP vector."""
    weights = []
    for block_idx in range(1, 11):
        activation = blocks.get(block_idx, 0.5)
        for _ in range(10):
            weights.append(activation)
    P = vector_p(weights)
    # Apply K-layer overrides (direct dimension control)
    for k_str, val in k_overrides.items():
        k = int(k_str)
        if 0 <= k < 100:
            P[k] = float(np.clip(val, 0.0, 1.0))
    return P


def _compute_ceid(P: np.ndarray) -> float:
    try:
        result = ceid_score(P)
        if isinstance(result, dict):
            val = result.get("CEID_score", result.get("ceid_score", 0.0))
        else:
            val = result
        return round(float(val), 4)
    except Exception:
        return 0.0


def _persona_to_vector(persona: CustomPersona) -> np.ndarray:
    return _build_vector(persona.get_blocks(), persona.get_k_overrides())


def _check_plan_limit(db: Session, workspace: Workspace) -> None:
    limit = PLAN_LIMITS.get(workspace.plan_tier, {}).get("personas")
    if limit is None:
        return
    count = db.query(CustomPersona).filter(
        CustomPersona.workspace_id == workspace.id
    ).count()
    if count >= limit:
        raise HTTPException(
            status_code=402,
            detail=f"Plan limit reached ({count}/{limit} personas). Upgrade your plan.",
        )


# ── CRUD ──────────────────────────────────────────────────────────────────────

@router.post("", status_code=201)
def create_persona(
    workspace_id: str,
    body: PersonaCreate,
    user: User = Depends(get_current_user),  # replaced by auth dep in main.py
    db: Session = Depends(get_db),
):
    ws = _get_ws_or_404(db, workspace_id, user.id)
    _check_plan_limit(db, ws)

    blocks_dict = body.blocks.to_dict()
    k_overrides = {str(k): v for k, v in (body.k_overrides or {}).items()}

    P = _build_vector(blocks_dict, k_overrides)
    score = _compute_ceid(P)

    persona = CustomPersona(
        workspace_id=workspace_id,
        name=body.name,
        description=body.description,
        blocks_json=json.dumps(blocks_dict),
        k_overrides_json=json.dumps(k_overrides) if k_overrides else None,
        ceid_score=score,
        is_public=body.is_public,
    )
    db.add(persona)
    db.flush()
    _save_version(db, persona)
    db.commit()
    db.refresh(persona)
    return _persona_response(persona)


@router.get("")
def list_personas(workspace_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    _get_ws_or_404(db, workspace_id, user.id)
    personas = db.query(CustomPersona).filter(
        CustomPersona.workspace_id == workspace_id
    ).order_by(CustomPersona.created_at.desc()).all()
    return {"personas": [_persona_response(p) for p in personas], "total": len(personas)}


@router.get("/{persona_id}")
def get_persona(
    workspace_id: str, persona_id: str,
    user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    _get_ws_or_404(db, workspace_id, user.id)
    p = _get_persona_or_404(db, workspace_id, persona_id)
    return _persona_response(p)


@router.put("/{persona_id}")
def update_persona(
    workspace_id: str, persona_id: str, body: PersonaUpdate,
    user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    _get_ws_or_404(db, workspace_id, user.id, required_role="editor")
    p = _get_persona_or_404(db, workspace_id, persona_id)

    if body.name is not None:
        p.name = body.name
    if body.description is not None:
        p.description = body.description
    if body.is_public is not None:
        p.is_public = body.is_public

    if body.blocks is not None or body.k_overrides is not None:
        blocks = body.blocks.to_dict() if body.blocks else p.get_blocks()
        k_overrides = (
            {str(k): v for k, v in body.k_overrides.items()}
            if body.k_overrides is not None
            else p.get_k_overrides()
        )
        P = _build_vector(blocks, k_overrides)
        p.blocks_json = json.dumps(blocks)
        p.k_overrides_json = json.dumps(k_overrides) if k_overrides else None
        p.ceid_score = _compute_ceid(P)
        p.version += 1
        _save_version(db, p)

    db.commit()
    db.refresh(p)
    return _persona_response(p)


@router.delete("/{persona_id}", status_code=204)
def delete_persona(
    workspace_id: str, persona_id: str,
    user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    _get_ws_or_404(db, workspace_id, user.id, required_role="editor")
    p = _get_persona_or_404(db, workspace_id, persona_id)
    db.delete(p)
    db.commit()


# ── CEID Diagnostic ───────────────────────────────────────────────────────────

@router.get("/{persona_id}/ceid")
def get_ceid(
    workspace_id: str, persona_id: str,
    user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    _get_ws_or_404(db, workspace_id, user.id)
    p = _get_persona_or_404(db, workspace_id, persona_id)
    P = _persona_to_vector(p)
    try:
        diag = ceid_full_diagnostic(P)
    except Exception as exc:
        raise HTTPException(500, f"CEID diagnostic failed: {exc}")
    axes = diag.get("axes", {})
    return _jsonify({
        "persona_id":   persona_id,
        "persona_name": p.name,
        "c_axis":  axes.get("C_semantic_resonance", 0.0),
        "e_axis":  axes.get("E_epistemic_vigilance", 0.0),
        "i_axis":  axes.get("I_tree_convergence",   0.0),
        "d_axis":  axes.get("D_sarsılmazlık",        0.0),
        "overall": diag.get("CEID_score", 0.0),
        "classification": diag.get("classification", ""),
        "details": diag,
    })


# ── Comparison ────────────────────────────────────────────────────────────────

@router.get("/{persona_id}/compare")
def compare_personas(
    workspace_id: str, persona_id: str, with_id: str,
    user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    _get_ws_or_404(db, workspace_id, user.id)
    p1 = _get_persona_or_404(db, workspace_id, persona_id)
    p2 = _get_persona_or_404(db, workspace_id, with_id)
    P1 = _persona_to_vector(p1)
    P2 = _persona_to_vector(p2)
    sim = float(cosine_similarity(P1, P2))
    try:
        dr = float(drift_metric(np.stack([P1, P2])))
    except Exception:
        dr = None
    return {
        "persona_a": {"id": persona_id, "name": p1.name, "ceid": p1.ceid_score},
        "persona_b": {"id": with_id, "name": p2.name, "ceid": p2.ceid_score},
        "cosine_similarity": round(sim, 4),
        "drift_score": round(dr, 4) if dr is not None else None,
        "are_compatible": sim > 0.6,
    }


# ── Compile ───────────────────────────────────────────────────────────────────

@router.post("/{persona_id}/compile")
def compile_single(
    workspace_id: str, persona_id: str, body: CompileRequest,
    user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    _get_ws_or_404(db, workspace_id, user.id)
    p = _get_persona_or_404(db, workspace_id, persona_id)
    if body.platform not in SUPPORTED_PLATFORMS:
        raise HTTPException(400, f"Unknown platform '{body.platform}'. Choose: {SUPPORTED_PLATFORMS}")
    if body.tier not in SUPPORTED_TIERS:
        raise HTTPException(400, f"Unknown tier '{body.tier}'. Choose: {SUPPORTED_TIERS}")
    P = _persona_to_vector(p)
    result = compile_persona(P, persona_id=persona_id, platform=body.platform, tier=body.tier)
    result["persona_name"] = p.name
    return result


@router.post("/{persona_id}/compile/all")
def compile_all(
    workspace_id: str, persona_id: str,
    user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    _get_ws_or_404(db, workspace_id, user.id)
    p = _get_persona_or_404(db, workspace_id, persona_id)
    P = _persona_to_vector(p)
    by_platform = compile_all_platforms(P, persona_id=persona_id)
    by_tier     = compile_all_tiers(P, persona_id=persona_id)
    return {
        "persona_id":   persona_id,
        "persona_name": p.name,
        "ceid_score":   p.ceid_score,
        "by_platform":  by_platform,
        "by_tier":      by_tier,
    }


# ── Helpers ───────────────────────────────────────────────────────────────────

def _get_ws_or_404(
    db: Session, workspace_id: str, user_id: str, required_role: str = "viewer"
) -> Workspace:
    from api.db import WorkspaceMember
    member = db.query(WorkspaceMember).filter(
        WorkspaceMember.workspace_id == workspace_id,
        WorkspaceMember.user_id == user_id,
    ).first()
    if not member:
        raise HTTPException(404, "Workspace not found or access denied.")
    role_order = {"viewer": 0, "editor": 1, "owner": 2}
    if role_order.get(member.role, 0) < role_order.get(required_role, 0):
        raise HTTPException(403, f"Requires '{required_role}' role.")
    return db.query(Workspace).filter(Workspace.id == workspace_id).first()


def _get_persona_or_404(db: Session, workspace_id: str, persona_id: str) -> CustomPersona:
    p = db.query(CustomPersona).filter(
        CustomPersona.id == persona_id,
        CustomPersona.workspace_id == workspace_id,
    ).first()
    if not p:
        raise HTTPException(404, "Persona not found.")
    return p


def _save_version(db: Session, p: CustomPersona) -> None:
    v = PersonaVersion(
        persona_id=p.id,
        version=p.version,
        blocks_json=p.blocks_json,
        k_overrides_json=p.k_overrides_json,
        ceid_score=p.ceid_score,
    )
    db.add(v)


def _persona_response(p: CustomPersona) -> dict:
    return {
        "id":          p.id,
        "name":        p.name,
        "description": p.description,
        "blocks":      p.get_blocks(),
        "k_overrides": p.get_k_overrides(),
        "ceid_score":  p.ceid_score,
        "version":     p.version,
        "is_public":   p.is_public,
        "workspace_id":p.workspace_id,
        "created_at":  p.created_at.isoformat() if p.created_at else None,
        "updated_at":  p.updated_at.isoformat() if p.updated_at else None,
    }
