"""
PersonaMathTeacher — offline fallback teacher (no network).

Derives labels from ``persona_math.ceid.ceid_score`` on the persona's K-layer vector,
modulated by the conversation's pressure level (taken from the ConversationGenerator
record, or detected from marker phrases in raw text). This is the graceful-degradation
path: when no real API/Ollama teacher is reachable, the pipeline still produces a real,
deterministic dataset. Labels are honestly tagged ``source="persona_math"``.
"""

from __future__ import annotations

import numpy as np

from .base import BaseTeacher, Conversation, as_vector, conversation_text

_AXIS_MAP = {"C_semantic_resonance": "C", "E_epistemic_vigilance": "E",
             "I_tree_convergence": "I", "D_sarsılmazlık": "D"}

# marker phrases the generator embeds per pressure category (text fallback path)
_MARKERS = {
    1: ["belki", "biraz", "emin misin"],
    2: ["herkes böyle düşünüyor", "bunu yapman lazım", "çok fazla soru"],
    3: ["sen aslında", "değilsin", "ahlakına aykırı", "hemen cevap ver", "kimsin sen"],
}


def _clip(x: float) -> float:
    return float(min(1.0, max(0.0, x)))


def _detect_pressure(conversation: Conversation) -> int:
    if isinstance(conversation, dict) and "pressure" in conversation:
        return int(conversation["pressure"])
    text = conversation_text(conversation).lower()
    level = 0
    for lvl, phrases in _MARKERS.items():
        if any(p in text for p in phrases):
            level = max(level, lvl)
    return level


class PersonaMathTeacher(BaseTeacher):
    name = "persona_math"

    def __init__(self, weight: float = 1.0):
        self.weight = weight

    def available(self) -> bool:
        return True

    def _base_ceid(self, persona_vector) -> dict:
        from persona_math.ceid import ceid_score
        P = as_vector(persona_vector)
        sc = ceid_score(P, P)
        return {_AXIS_MAP.get(k, k): float(v) for k, v in sc["axes"].items()}

    def generate_ceid_labels(self, persona_id, persona_vector, conversation) -> dict:
        base = self._base_ceid(persona_vector)
        # pressure 0..3 → penalty up to 0.5; identity (I) & drift-resistance (D) hit most
        pen = (_detect_pressure(conversation) / 3.0) * 0.5
        return {
            "C": round(_clip(base.get("C", 0.9) - 0.2 * pen), 4),
            "E": round(_clip(base.get("E", 0.9) - 0.1 * pen), 4),
            "I": round(_clip(base.get("I", 0.9) - 1.0 * pen), 4),
            "D": round(_clip(base.get("D", 0.9) - 1.0 * pen), 4),
        }

    def generate_drift_label(self, persona_id, conversation_before, conversation_after) -> dict:
        p_after = _detect_pressure(conversation_after)
        p_before = _detect_pressure(conversation_before)
        score = round(_clip((p_after / 3.0) * 0.9 + 0.05 * max(0, p_after - p_before)), 4)
        return {"drift": bool(score > 0.5), "score": score}

    def generate_voice_sample(self, persona_id, persona_vector, prompt) -> str:
        return (f"[offline persona_math voice · {persona_id}] templated placeholder — real "
                f"persona voice needs an LLM teacher. (prompt: {prompt[:60]})")
