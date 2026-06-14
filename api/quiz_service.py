"""
Quiz scoring engine — turns HPEP-100 answers into a K-layer vector + CEID scores.

Pipeline:
    answers (dict[qid -> value])
      → structured answers contribute deterministic per-K-layer nudges
      → open-ended answers are LLM-scored against their rubric (axis float in [0,1]),
        projected back onto representative K-layers (AXIS_LAYERS)
      → aggregate into a persona_math spec → make_persona_vector → P  (shape (100,))
      → ceid_score(P) → {C, E, I, D, composite, classification}

Design constraints (mirrors api/needle_service.py):
* Torch-free. Only persona_math + numpy are required.
* API-free graceful degradation: if ANTHROPIC_API_KEY is unset (or the SDK/network
  is unavailable), open-ended answers fall back to a neutral 0.5 prior instead of
  raising — the structured core still yields a usable persona.
"""

from __future__ import annotations

import os
from typing import Optional

import numpy as np

from persona_math.persona_factory import make_persona_vector
from persona_math.ceid import ceid_score

from api.quiz_questions import (
    QUESTION_BANK,
    AXIS_LAYERS,
)

# CEID axis key normalisation: persona_math returns descriptive axis names.
_AXIS_MAP = {
    "C_semantic_resonance": "C",
    "E_epistemic_vigilance": "E",
    "I_tree_convergence": "I",
    "D_sarsılmazlık": "D",
}


# ── Open-ended (LLM) scoring ────────────────────────────────────────────────────

def _score_open_ended(question: dict, answer_text: str) -> float:
    """Score one open-ended answer onto its CEID axis, returning a float in [0,1].

    Uses the Anthropic API when ANTHROPIC_API_KEY is present; otherwise (or on any
    error) returns a neutral 0.5 so the rest of the pipeline still works.
    """
    answer_text = (answer_text or "").strip()
    if not answer_text:
        return 0.5

    api_key = os.getenv("ANTHROPIC_API_KEY", "").strip()
    if not api_key:
        return 0.5

    try:
        import anthropic  # lazy: keep module import API-free

        client = anthropic.Anthropic(api_key=api_key)
        prompt = (
            f"You are scoring a persona-extraction interview answer.\n\n"
            f"QUESTION: {question['text']}\n\n"
            f"SCORING RUBRIC ({question.get('ceid_axis')}-axis): {question.get('rubric', '')}\n\n"
            f"ANSWER: {answer_text}\n\n"
            f"Return ONLY a single float between 0 and 1 (e.g. 0.73). No other text."
        )
        resp = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=10,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = resp.content[0].text.strip()
        val = float(raw.split()[0])
        return max(0.0, min(1.0, val))
    except Exception:
        # Network down, bad key, unparseable output → neutral prior.
        return 0.5


# ── Core scoring ────────────────────────────────────────────────────────────────

def _aggregate_layers(answers: dict) -> tuple[dict[int, list[float]], dict[str, list[float]]]:
    """Walk the answer set, accumulating per-K-layer values and per-axis values.

    Returns (layer_values, axis_values) where each maps key -> list of contributions
    (later averaged). Unanswered questions are skipped.
    """
    layer_values: dict[int, list[float]] = {}
    axis_values: dict[str, list[float]] = {}

    def _push_layer(idx: int, val: float):
        layer_values.setdefault(idx, []).append(float(val))

    def _push_axis(axis: Optional[str], val: float):
        if axis:
            axis_values.setdefault(axis, []).append(float(val))

    for q in QUESTION_BANK:
        if q["id"] not in answers:
            continue
        ans = answers[q["id"]]

        if q["type"] == "structured":
            # ans is an option index (int) or label (str)
            opts = q["options"]
            opt = None
            if isinstance(ans, int) and 0 <= ans < len(opts):
                opt = opts[ans]
            else:
                opt = next((o for o in opts if o["label"] == ans), None)
            if opt is None:
                continue
            for idx, val in opt.get("layers", {}).items():
                _push_layer(int(idx), val)
            for axis, val in opt.get("axis_hint", {}).items():
                _push_axis(axis, val)

        elif q["type"] == "open":
            score = _score_open_ended(q, str(ans))
            axis = q.get("ceid_axis")
            _push_axis(axis, score)
            # Project the open-ended score onto the question's target layers, falling
            # back to the axis's representative layers when none are specified.
            target = q.get("target_layers") or AXIS_LAYERS.get(axis, [])
            for idx in target:
                _push_layer(int(idx), score)

    return layer_values, axis_values


def build_persona_vector(answers: dict, *, base: float = 0.5, seed: int = 42) -> np.ndarray:
    """Build a (100,) K-layer vector from an answer set."""
    layer_values, _ = _aggregate_layers(answers)
    mandatory_core = {idx: float(np.mean(vals)) for idx, vals in layer_values.items()}

    spec = {
        "base": base,
        "seed": seed,
        "mandatory_core": mandatory_core,
    }
    return make_persona_vector(spec, default_base=base)


def _normalise_ceid(raw: dict) -> dict:
    """Map persona_math's ceid_score() output to a flat {C,E,I,D,composite,...} dict."""
    axes = raw.get("axes", {})
    out = {short: float(axes[long]) for long, short in _AXIS_MAP.items() if long in axes}
    out["composite"] = float(raw.get("CEID_score", 0.0))
    out["classification"] = raw.get("classification", "UNKNOWN")
    return out


def extract_persona(answers: dict, *, base: float = 0.5, seed: int = 42) -> dict:
    """Full extraction: answers -> {k_layer, ceid, n_answered, n_total}.

    This is the public entry point used by the quiz router.
    """
    P = build_persona_vector(answers, base=base, seed=seed)
    ceid = _normalise_ceid(ceid_score(P))

    return {
        "k_layer": [round(float(x), 4) for x in P.tolist()],
        "ceid": ceid,
        "n_answered": sum(1 for q in QUESTION_BANK if q["id"] in answers),
        "n_total": len(QUESTION_BANK),
        "source": "hpep_quiz",
        "untrained": True,   # honest tier: reference scoring, not a trained model
    }
