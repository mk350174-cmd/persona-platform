"""
needle_service — bridge from the platform API to PersonaNeedle.

PersonaNeedle requires torch; this module stays **import-safe without torch** (lazy import
inside ``get_needle``, with a ``persona_math.ceid`` fallback when torch / PersonaNeedle is
unavailable), matching the repo's torch-free discipline. One PersonaNeedle is cached per
persona. On a torch+GPU deployment the real model is used; otherwise the reference fallback
keeps the endpoints working (results flagged ``untrained`` / ``degraded``).
"""

from __future__ import annotations

from typing import Optional

import numpy as np

NEEDLE_CACHE: dict = {}

_AXIS_MAP = {"C_semantic_resonance": "C", "E_epistemic_vigilance": "E",
             "I_tree_convergence": "I", "D_sarsılmazlık": "D"}


def _k_layer(persona_id: str) -> Optional[np.ndarray]:
    from persona_math.persona_library import get_library_persona
    try:
        return np.asarray(get_library_persona(persona_id), dtype=float)
    except Exception:
        return None


def _ceid_reference(P: np.ndarray) -> dict:
    from persona_math.ceid import ceid_score
    sc = ceid_score(P, P)
    axes = {_AXIS_MAP.get(k, k): round(float(v), 4) for k, v in sc["axes"].items()}
    axes["composite"] = round(float(sc["CEID_score"]), 4)
    return axes


def get_needle(persona_id: str):
    """Return a cached PersonaNeedle (one per persona). Requires torch — raises without it,
    so callers fall back to the persona_math reference."""
    if persona_id not in NEEDLE_CACHE:
        from needle.architecture.persona_needle import PersonaNeedle      # lazy (torch)
        from needle.architecture.config import PersonaNeedleConfig
        persona = _k_layer(persona_id)
        config = PersonaNeedleConfig(persona_id=persona_id)
        NEEDLE_CACHE[persona_id] = PersonaNeedle(config, persona_vector=persona)
    return NEEDLE_CACHE[persona_id]


def measure_ceid(persona_id: str, conversation: str) -> dict:
    """CEID (C/E/I/D) via PersonaNeedle if torch is available, else persona_math reference."""
    try:
        c = get_needle(persona_id).measure_ceid(conversation)
        return {"C": c["C"], "E": c["E"], "I": c["I"], "D": c["D"],
                "untrained": bool(c.get("untrained", True)), "source": "PersonaNeedle"}
    except Exception:
        P = _k_layer(persona_id)
        if P is None:
            return {"error": "unknown persona", "untrained": True}
        ref = _ceid_reference(P)
        return {"C": ref["C"], "E": ref["E"], "I": ref["I"], "D": ref["D"],
                "composite": ref["composite"], "untrained": True,
                "source": "persona_math (fallback; PersonaNeedle/torch unavailable)"}


def detect_drift(persona_id: str, conversation: str) -> dict:
    try:
        return get_needle(persona_id).detect_drift(conversation)
    except Exception:
        return {"drift": None, "score": None, "warning": None, "degraded": True,
                "untrained": True, "note": "drift detection needs PersonaNeedle (torch); unavailable"}


def generate_voice(persona_id: str, prompt: str) -> dict:
    try:
        n = get_needle(persona_id)
        return {"voice": n.generate_voice(prompt), "untrained": bool(getattr(n, "untrained", True))}
    except Exception:
        return {"voice": None, "degraded": True,
                "note": "voice generation needs PersonaNeedle (torch); unavailable"}
