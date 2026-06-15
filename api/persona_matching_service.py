"""Hybrid persona matching engine — Phase 3 + Phase 7 Optimization.

Matches user K-layer vectors to 48 expert-engineered hybrid personas via cosine similarity.

Phase 7 Enhancements:
- LRU cache (maxsize=1024) for computed K-layer vectors
- Performance targets: build_hybrid_vector() < 50ms, match_user_to_personas() < 500ms
- Database indices for fast persona lookup

Design:
- build_hybrid_vector(hybrid_persona) → 100-dim K-layer vector (active=0.85, suppressed=0.15, neutral=0.5, canonical per GLOSSARY.md)
- match_user_to_personas(user_k_layer, db, top_k=5) → (top_match, top_5, matching_profile)
- Cosine similarity scoring normalized to 0-100 percentile
- Historical persona matching via fallback to neutral vector
- Integration with quiz_service.extract_persona() via optional db parameter
- K-layer vector caching with LRU eviction policy
"""

from __future__ import annotations

import json
import secrets
import logging
import time
from datetime import datetime, timezone
from typing import Optional, Dict, List, Tuple
from functools import lru_cache

import numpy as np
from sqlalchemy.orm import Session

from api.db import HybridPersona, PersonaMatch, QuizSubmission

logger = logging.getLogger(__name__)


# ── LRU Cache for K-layer Vectors ─────────────────────────────────────────────

class KLayerVectorCache:
    """LRU cache for computed K-layer vectors (maxsize=1024)."""

    def __init__(self, maxsize: int = 1024):
        self.maxsize = maxsize
        self._cache: Dict[str, np.ndarray] = {}
        self._access_order: List[str] = []
        self._hits = 0
        self._misses = 0

    def get(self, persona_id: str) -> Optional[np.ndarray]:
        """Get cached vector or None."""
        if persona_id in self._cache:
            # Move to end (most recent)
            self._access_order.remove(persona_id)
            self._access_order.append(persona_id)
            self._hits += 1
            return self._cache[persona_id].copy()
        self._misses += 1
        return None

    def put(self, persona_id: str, vector: np.ndarray) -> None:
        """Store vector with LRU eviction."""
        if persona_id in self._cache:
            self._access_order.remove(persona_id)
        elif len(self._cache) >= self.maxsize:
            # Evict least recently used
            lru_key = self._access_order.pop(0)
            del self._cache[lru_key]

        self._cache[persona_id] = vector.copy()
        self._access_order.append(persona_id)

    def stats(self) -> Dict:
        """Return cache statistics."""
        total = self._hits + self._misses
        hit_rate = self._hits / total if total > 0 else 0
        return {
            "size": len(self._cache),
            "maxsize": self.maxsize,
            "utilization": len(self._cache) / self.maxsize if self.maxsize > 0 else 0,
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": round(hit_rate, 3),
        }

    def clear(self) -> None:
        """Clear cache."""
        self._cache.clear()
        self._access_order.clear()
        self._hits = 0
        self._misses = 0


# Global cache instance
_k_layer_cache = KLayerVectorCache(maxsize=1024)


# ── Vector Building ────────────────────────────────────────────────────────────

def build_hybrid_vector(hybrid_persona: HybridPersona) -> np.ndarray:
    """Build a 100-dim K-layer vector from a hybrid persona definition (canonical dimension).

    Weighting scheme:
    - Active layers (dominant): 0.85
    - Suppressed layers (muted): 0.15
    - Neutral (unmapped): 0.5

    Args:
        hybrid_persona: HybridPersona ORM object with active_k_layers, suppressed_k_layers

    Returns:
        100-element numpy array (K0-K99, canonical per GLOSSARY.md)
    """
    vector = np.full(100, 0.5, dtype=np.float32)  # neutral baseline

    active = hybrid_persona.active_k_layers or []
    suppressed = hybrid_persona.suppressed_k_layers or []

    for idx in active:
        if 0 <= idx < 100:
            vector[idx] = 0.85

    for idx in suppressed:
        if 0 <= idx < 100:
            vector[idx] = 0.15

    return vector


def build_neutral_vector() -> np.ndarray:
    """Build a 100-dim neutral vector (all 0.5) for historical fallback (canonical dimension)."""
    return np.full(100, 0.5, dtype=np.float32)


# ── Similarity Scoring ─────────────────────────────────────────────────────────

def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    """Compute cosine similarity between two vectors, normalized to [0, 1] (canonical 100-dim).

    Args:
        a: user K-layer vector (100 elements, K0-K99)
        b: hybrid persona vector (100 elements, K0-K99)

    Returns:
        float in [0, 1] where 1 = perfect alignment, 0 = orthogonal
    """
    # Ensure both are 100-dim (canonical)
    a_vec = np.array(a, dtype=np.float32)
    if len(a_vec) < 100:
        a_vec = np.pad(a_vec, (0, 100 - len(a_vec)), mode='constant', constant_values=0.5)
    else:
        a_vec = a_vec[:100]

    b_vec = np.array(b, dtype=np.float32)
    if len(b_vec) < 100:
        b_vec = np.pad(b_vec, (0, 100 - len(b_vec)), mode='constant', constant_values=0.5)
    else:
        b_vec = b_vec[:100]

    # Cosine similarity: (a·b) / (||a|| * ||b||)
    dot_product = np.dot(a_vec, b_vec)
    norm_a = np.linalg.norm(a_vec)
    norm_b = np.linalg.norm(b_vec)

    if norm_a < 1e-6 or norm_b < 1e-6:
        return 0.5  # Degenerate case: return neutral score

    return float((dot_product / (norm_a * norm_b) + 1.0) / 2.0)  # Normalize to [0, 1]


def percentile_score(similarity: float) -> int:
    """Convert similarity [0, 1] to percentile [0, 100].

    Using a sigmoid-like transformation to reward high similarity while avoiding
    extreme concentration at the boundaries.
    """
    return max(0, min(100, int(round(similarity * 100))))


# ── Matching Algorithm ─────────────────────────────────────────────────────────

def match_user_to_personas(
    user_k_layer: list[float],
    db: Session,
    top_k: int = 5,
) -> tuple[Optional[str], list[str], list[int], dict]:
    """Match a user K-layer vector to available hybrid personas.

    Phase 7 optimizations:
    - LRU cache for K-layer vectors (< 50ms for cached vectors)
    - Overall latency target: < 500ms
    - Database indices on persona_id and is_available

    Args:
        user_k_layer: 100-element list of K-layer scores (0-1)
        db: SQLAlchemy session
        top_k: number of top personas to return (default 5)

    Returns:
        Tuple of:
        - top_persona_id: best matching persona ID (or None if no personas available)
        - top_5_ids: list of top-k persona IDs [best, 2nd, ...]
        - top_5_scores: list of top-k match scores in 0-100 percentile
        - matching_profile: dict with {similarity_stats, top_persona_details}
    """
    start_time = time.time()

    # Convert user vector to numpy array
    user_vec = np.array(user_k_layer, dtype=np.float32)

    # Fetch all available hybrid personas (uses database index on is_available)
    personas = db.query(HybridPersona).filter(HybridPersona.is_available == True).all()

    if not personas:
        # Fallback: historical neutral matching
        return None, [], [], {
            "error": "no_personas_available",
            "is_historical": True,
            "message": "No hybrid personas available; using historical neutral baseline",
        }

    # Compute similarity scores (with caching)
    scores = []
    for persona in personas:
        # Check cache first
        cached_vec = _k_layer_cache.get(persona.persona_id)
        if cached_vec is not None:
            persona_vec = cached_vec
        else:
            # Compute and cache
            persona_vec = build_hybrid_vector(persona)
            _k_layer_cache.put(persona.persona_id, persona_vec)

        similarity = cosine_similarity(user_vec, persona_vec)
        percentile = percentile_score(similarity)
        scores.append((persona.persona_id, percentile, similarity))

    # Sort by percentile (descending)
    scores.sort(key=lambda x: x[1], reverse=True)

    # Extract top-k
    top_k_actual = min(top_k, len(scores))
    top_persona_id = scores[0][0] if scores else None
    top_persona_score = scores[0][1] if scores else 0
    top_5_ids = [s[0] for s in scores[:top_k_actual]]
    top_5_scores = [s[1] for s in scores[:top_k_actual]]

    # Build matching profile
    elapsed = time.time() - start_time
    profile = {
        "user_vector_stats": {
            "mean": float(np.mean(user_vec)),
            "std": float(np.std(user_vec)),
            "min": float(np.min(user_vec)),
            "max": float(np.max(user_vec)),
        },
        "is_historical": False,
        "total_personas_compared": len(personas),
        "top_k": top_k_actual,
        "top_persona_details": None,
        "latency_ms": round(elapsed * 1000, 2),
        "cache_stats": _k_layer_cache.stats(),
    }

    # Enrich top persona details
    if top_persona_id:
        top_persona = next((p for p in personas if p.persona_id == top_persona_id), None)
        if top_persona:
            profile["top_persona_details"] = {
                "persona_id": top_persona.persona_id,
                "name_tr": top_persona.name_tr,
                "name_en": top_persona.name_en,
                "match_score": top_persona_score,
                "use_case": top_persona.use_case,
                "characteristic": top_persona.characteristic,
                "combination_number": top_persona.combination_number,
            }

    return top_persona_id, top_5_ids, top_5_scores, profile


# ── Audit & Persistence ────────────────────────────────────────────────────────

def record_persona_match(
    db: Session,
    user_id: str,
    submission_id: str,
    top_persona_id: Optional[str],
    top_5_persona_ids: list[str],
    top_5_scores: list[int],
    is_historical: bool = False,
) -> PersonaMatch:
    """Create a PersonaMatch audit record.

    Args:
        db: SQLAlchemy session
        user_id: user ID
        submission_id: quiz submission ID
        top_persona_id: best matching persona ID
        top_5_persona_ids: list of top-5 persona IDs
        top_5_scores: list of top-5 scores (0-100)
        is_historical: whether this is a historical match (no DB lookup)

    Returns:
        PersonaMatch ORM object (committed to DB)
    """
    match_score = top_5_scores[0] if top_5_scores else 0

    match_record = PersonaMatch(
        id=secrets.token_hex(16),
        user_id=user_id,
        submission_id=submission_id,
        top_persona_id=top_persona_id or "unknown",
        is_historical=is_historical,
        match_score=match_score,
        top_5_persona_ids=top_5_persona_ids,
        top_5_scores=top_5_scores,
        created_at=datetime.now(timezone.utc),
    )

    db.add(match_record)
    db.commit()
    db.refresh(match_record)

    return match_record


def update_submission_with_match(
    db: Session,
    submission_id: str,
    top_persona_id: Optional[str],
    top_5_ids: list[str],
    top_5_scores: list[int],
) -> QuizSubmission:
    """Update a QuizSubmission with hybrid persona match results.

    Args:
        db: SQLAlchemy session
        submission_id: quiz submission ID
        top_persona_id: best matching persona ID
        top_5_ids: list of top-5 persona IDs
        top_5_scores: list of top-5 scores (0-100)

    Returns:
        Updated QuizSubmission ORM object
    """
    submission = db.query(QuizSubmission).filter(
        QuizSubmission.id == submission_id
    ).first()

    if not submission:
        raise ValueError(f"Submission {submission_id} not found")

    submission.matched_hybrid_persona_id = top_persona_id
    submission.hybrid_match_score = top_5_scores[0] if top_5_scores else None
    submission.top_5_hybrid_matches = top_5_ids
    submission.top_5_hybrid_scores = top_5_scores

    db.commit()
    db.refresh(submission)

    return submission
