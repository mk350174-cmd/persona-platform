"""Hybrid Persona API Router — Phase 4: Endpoints for matching and browsing hybrid personas.

Endpoints:
1. GET /api/v1/personas/hybrid/{persona_id}/profile — Get hybrid persona profile
2. POST /api/v1/personas/match — Match user K-layer to personas
3. GET /api/v1/personas/hybrid?skip=0&limit=50 — Paginated list
4. GET /api/v1/personas/search/hybrid?q=rasyonalist&limit=20 — Full-text search
"""

from typing import Any, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from api.db import get_db, HybridPersona
from api.auth import get_current_user
from api.db import User
from api.persona_matching_service import match_user_to_personas

router = APIRouter(prefix="/api/v1/personas", tags=["hybrid-personas"])


# ── Request/Response Models ────────────────────────────────────────────────────

class KLayerMatchRequest(BaseModel):
    """User K-layer vector + CEID scores for persona matching."""
    k_layer: list[float] = Field(
        ...,
        description="K-layer vector: 98 or 100 elements, each in [0, 1]"
    )
    ceid_scores: Optional[dict[str, float]] = Field(
        default=None,
        description="Optional CEID scores: {C: 0-3, E: 0-3, I: 0-3, D: 0-3}"
    )


class HybridPersonaProfile(BaseModel):
    """Hybrid persona detail with all fields."""
    persona_id: str
    name_tr: str
    name_en: str
    combination_number: int
    use_case: str
    characteristic: str
    active_k_layers: list[int]
    suppressed_k_layers: list[int]
    price_usd: Optional[float] = None
    is_available: bool
    example_outputs: Optional[str] = None


class HybridPersonaItem(BaseModel):
    """Lightweight hybrid persona item for list views."""
    persona_id: str
    name_tr: str
    name_en: str
    combination_number: int
    active_k_layers: list[int]
    price_usd: Optional[float] = None


class MatchResponse(BaseModel):
    """Response after persona matching."""
    top_match: Optional[str] = Field(None, description="Best matching persona_id")
    top_match_score: Optional[int] = Field(None, description="Match score 0-100")
    top_5: list[str] = Field(default_factory=list, description="Top 5 persona IDs")
    top_5_scores: list[int] = Field(default_factory=list, description="Top 5 scores 0-100")
    matching_profile: dict[str, Any] = Field(
        default_factory=dict,
        description="Matching profile with stats"
    )


class PaginatedPersonas(BaseModel):
    """Paginated list of hybrid personas."""
    count: int
    skip: int
    limit: int
    personas: list[HybridPersonaItem]


class SearchResults(BaseModel):
    """Search results with matching personas."""
    query: str
    count: int
    limit: int
    personas: list[HybridPersonaProfile]


# ── Endpoints ──────────────────────────────────────────────────────────────────

@router.get(
    "/hybrid/{persona_id}/profile",
    response_model=HybridPersonaProfile,
    summary="Get hybrid persona profile"
)
async def get_hybrid_persona_profile(
    persona_id: str,
    db: Session = Depends(get_db),
) -> HybridPersonaProfile:
    """
    Get a hybrid persona's complete profile with all fields.

    Args:
        persona_id: Persona ID (e.g., "komb_001_slug")

    Returns:
        HybridPersonaProfile with persona_id, name_tr, name_en, combination_number,
        use_case, characteristic, active_k_layers, suppressed_k_layers, price_usd, is_available

    Raises:
        404: Persona not found
    """
    persona = db.query(HybridPersona).filter(
        HybridPersona.persona_id == persona_id
    ).first()

    if not persona:
        raise HTTPException(
            status_code=404,
            detail=f"Hybrid persona '{persona_id}' not found."
        )

    return HybridPersonaProfile(
        persona_id=persona.persona_id,
        name_tr=persona.name_tr,
        name_en=persona.name_en,
        combination_number=persona.combination_number,
        use_case=persona.use_case,
        characteristic=persona.characteristic,
        active_k_layers=persona.active_k_layers or [],
        suppressed_k_layers=persona.suppressed_k_layers or [],
        price_usd=(persona.price_usd / 100) if persona.price_usd else None,
        is_available=persona.is_available,
        example_outputs=persona.example_outputs,
    )


@router.post(
    "/match",
    response_model=MatchResponse,
    summary="Match user K-layer to hybrid personas"
)
async def match_personas(
    request: KLayerMatchRequest,
    db: Session = Depends(get_db),
) -> MatchResponse:
    """
    Match a user's K-layer vector to available hybrid personas.

    Validates that k_layer is 98 or 100 dimensions, computes cosine similarity,
    and returns top match + top-5 recommendations with percentile scores.

    Args:
        request: KLayerMatchRequest with k_layer (list) and optional ceid_scores

    Returns:
        MatchResponse with top_match, top_5, match scores, and detailed profile

    Raises:
        400: Invalid k_layer dimensions or missing fields
    """
    # Validate k_layer dimensions
    if not request.k_layer:
        raise HTTPException(
            status_code=400,
            detail="k_layer is required and must not be empty."
        )

    k_layer_len = len(request.k_layer)
    if k_layer_len not in (98, 100):
        raise HTTPException(
            status_code=400,
            detail=f"k_layer must be 98 or 100 dimensions, got {k_layer_len}."
        )

    # Ensure k_layer is exactly 100 dimensions for matching (pad with 0.5 if 98)
    k_layer_normalized = list(request.k_layer)
    if k_layer_len == 98:
        # Pad to 100 (add legacy K-layers 0-1 as neutral 0.5)
        k_layer_normalized = [0.5, 0.5] + k_layer_normalized

    # Call matching service
    try:
        top_persona_id, top_5_ids, top_5_scores, profile = match_user_to_personas(
            k_layer_normalized,
            db,
            top_k=5
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Matching failed: {str(e)}"
        )

    return MatchResponse(
        top_match=top_persona_id,
        top_match_score=top_5_scores[0] if top_5_scores else None,
        top_5=top_5_ids,
        top_5_scores=top_5_scores,
        matching_profile=profile,
    )


@router.get(
    "/hybrid",
    response_model=PaginatedPersonas,
    summary="List available hybrid personas (paginated)"
)
async def list_hybrid_personas(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=500),
    db: Session = Depends(get_db),
) -> PaginatedPersonas:
    """
    Get a paginated list of available hybrid personas.

    Results are ordered by combination_number. Each item includes persona_id,
    name_tr, name_en, combination_number, active_k_layers, and price_usd.

    Args:
        skip: Number of personas to skip (default 0)
        limit: Number of personas per page (default 50, max 500)

    Returns:
        PaginatedPersonas with count, skip, limit, and personas list
    """
    # Query total count
    total_count = db.query(HybridPersona).filter(
        HybridPersona.is_available == True
    ).count()

    # Query paginated results (ordered by combination_number)
    personas_db = db.query(HybridPersona).filter(
        HybridPersona.is_available == True
    ).order_by(HybridPersona.combination_number).offset(skip).limit(limit).all()

    personas = [
        HybridPersonaItem(
            persona_id=p.persona_id,
            name_tr=p.name_tr,
            name_en=p.name_en,
            combination_number=p.combination_number,
            active_k_layers=p.active_k_layers or [],
            price_usd=(p.price_usd / 100) if p.price_usd else None,
        )
        for p in personas_db
    ]

    return PaginatedPersonas(
        count=total_count,
        skip=skip,
        limit=limit,
        personas=personas,
    )


@router.get(
    "/search/hybrid",
    response_model=SearchResults,
    summary="Full-text search hybrid personas"
)
async def search_hybrid_personas(
    q: str = Query(..., min_length=1, max_length=255),
    limit: int = Query(20, ge=1, le=50),
    db: Session = Depends(get_db),
) -> SearchResults:
    """
    Full-text search on hybrid persona name_tr, name_en, use_case, and characteristic.

    Search is case-insensitive substring matching on available personas.

    Args:
        q: Search query (required, 1-255 chars)
        limit: Max results (default 20, max 50)

    Returns:
        SearchResults with matching personas (up to limit)
    """
    q_lower = q.lower()

    # Query available personas
    all_personas = db.query(HybridPersona).filter(
        HybridPersona.is_available == True
    ).all()

    # Filter by search query (name_tr, name_en, use_case, characteristic)
    matching = []
    for persona in all_personas:
        if (
            q_lower in (persona.name_tr or "").lower()
            or q_lower in (persona.name_en or "").lower()
            or q_lower in (persona.use_case or "").lower()
            or q_lower in (persona.characteristic or "").lower()
        ):
            matching.append(persona)

    # Limit results
    matching = matching[:limit]

    results = [
        HybridPersonaProfile(
            persona_id=p.persona_id,
            name_tr=p.name_tr,
            name_en=p.name_en,
            combination_number=p.combination_number,
            use_case=p.use_case,
            characteristic=p.characteristic,
            active_k_layers=p.active_k_layers or [],
            suppressed_k_layers=p.suppressed_k_layers or [],
            price_usd=(p.price_usd / 100) if p.price_usd else None,
            is_available=p.is_available,
            example_outputs=p.example_outputs,
        )
        for p in matching
    ]

    return SearchResults(
        query=q,
        count=len(results),
        limit=limit,
        personas=results,
    )
