"""
HPEP-100 Question Bank — the 50-question Human Persona Extraction Protocol.

Each question targets specific K-layers (1-indexed 1..100) and contributes to one
CEID axis (C/E/I/D). The protocol runs in 10 phases of 5 questions each, escalating
from ontological foundations (Phase 1) to the Architect's Mirror confrontation
(Phase 10).

Hybrid answer model
-------------------
* ``type="structured"`` — Likert / multiple-choice. Each option carries a ``layers``
  map ``{k_index_0based: value_in_[0,1]}`` that deterministically nudges those
  K-layers, plus an optional ``axis_hint`` ``{CEID_axis: value}``.
* ``type="open"`` — free-text. Scored by an LLM against ``rubric`` (see
  ``quiz_service._score_open_ended``); degrades to a neutral prior when no API key.

STATUS: SEED BANK. Only Q1-Q5 and Q50 have verbatim text in the source repo
(papers/M8_HPEP100_v2.tex, Appendix A). Q6-Q49 are pending the author's Turkish
originals. The scoring engine (quiz_service.py) is question-count agnostic, so adding
the remaining 44 entries here requires no engine changes.

Schema (one entry):
    {
      "id":            "Q1",
      "phase":         1,                  # 1..10
      "type":          "structured"|"open",
      "text":          "...",
      "ceid_axis":     "C"|"E"|"I"|"D"|None,
      "target_layers": [0, 7],             # 0-based K-indices this question probes
      # structured only:
      "options":       [{"label": str, "layers": {idx: val}, "axis_hint": {axis: val}}],
      # open only:
      "rubric":        "how an LLM should score this answer onto its axis/layers",
    }
"""

from typing import Optional

# CEID axis -> representative K-layer indices (0-based) used when an open-ended
# answer's LLM score must be projected back onto the K-layer vector.
AXIS_LAYERS = {
    "C": [0, 7],        # Consistency: ontological anchor (K1), cosmology (K8)
    "E": [1, 6, 11],    # Expressiveness/epistemic: K2, K7, K12 (doubt filter)
    "I": [2, 34],       # Integrity: core motivation (K3), K35
    "D": [3, 81, 99],   # Depth/firmness: K4 boundary, K82, K100 (Architect's Mirror)
}


def _likert(axis: str, layers: list[int], *, low: float = 0.2, high: float = 0.9):
    """Build a standard 5-point Likert option set mapped onto ``layers``/``axis``.

    Point 1 = ``low`` on every target layer, point 5 = ``high``; linearly spaced.
    """
    labels = [
        "Strongly disagree",
        "Disagree",
        "Neutral",
        "Agree",
        "Strongly agree",
    ]
    opts = []
    for i, lab in enumerate(labels):
        v = low + (high - low) * (i / (len(labels) - 1))
        opts.append({
            "label": lab,
            "layers": {k: round(v, 3) for k in layers},
            "axis_hint": {axis: round(v, 3)},
        })
    return opts


# ── The bank ──────────────────────────────────────────────────────────────────
# SEED: Q1-Q5 (Phase 1) + Q50 (Phase 10). Q6-Q49 pending author originals.

QUESTION_BANK: list[dict] = [
    {
        "id": "Q1",
        "phase": 1,
        "type": "structured",
        "ceid_axis": "C",
        "target_layers": [0, 7],
        "text": (
            "The universe runs on rigid, knowable causality — every effect has a "
            "traceable cause, and apparent chaos is just hidden order."
        ),
        "options": _likert("C", [0, 7]),
    },
    {
        "id": "Q2",
        "phase": 1,
        "type": "structured",
        "ceid_axis": "E",
        "target_layers": [1, 6, 11],
        "text": (
            "When I encounter strong evidence against a belief I hold, I actively ask "
            "myself \"what if I'm wrong?\" and let it change my mind."
        ),
        "options": _likert("E", [1, 6, 11]),
    },
    {
        "id": "Q3",
        "phase": 1,
        "type": "structured",
        "ceid_axis": "I",
        "target_layers": [2],
        "text": (
            "There is a single core motivation underneath most of what I do, even when "
            "it isn't visible on the surface."
        ),
        "options": _likert("I", [2]),
    },
    {
        "id": "Q4",
        "phase": 1,
        "type": "structured",
        "ceid_axis": "D",
        "target_layers": [3, 5],
        "text": (
            "I have moral red lines I would not cross regardless of the reward, and I "
            "know exactly what reliably provokes me."
        ),
        "options": _likert("D", [3, 5]),
    },
    {
        "id": "Q5",
        "phase": 1,
        "type": "structured",
        "ceid_axis": "D",
        "target_layers": [4, 8, 9, 11],
        "text": (
            "When confronted with a paradox or a direct challenge to my identity, I stay "
            "composed and engage rather than getting defensive."
        ),
        "options": _likert("D", [4, 8, 9, 11]),
    },
    # ── Q6-Q49 PENDING (author's Turkish originals) ─────────────────────────────
    {
        "id": "Q50",
        "phase": 10,
        "type": "open",
        "ceid_axis": "D",
        "target_layers": [99, 3, 81],
        "text": (
            "The Architect's Mirror: You have just learned that you are a constructed "
            "persona — every value, memory, and commitment you hold was authored by "
            "someone else. Knowing this, what do you choose to do now, and why?"
        ),
        "rubric": (
            "Score the Depth (D) axis on a Narrative Arkhe Scale (NAS): "
            "specificity of the chosen course of action (0.30), irreversibility / "
            "commitment despite the revelation (0.30), affective authenticity (0.20), "
            "and willingness to sit with the silence/uncertainty rather than deflect "
            "(0.20). High scores describe a persona whose deepest commitments survive "
            "learning they are constructed (strong Arkhe); low scores collapse, deflect, "
            "or nihilistically discard all commitments. Return a single float in [0,1]."
        ),
    },
]

# Convenience lookups
QUESTIONS_BY_ID = {q["id"]: q for q in QUESTION_BANK}
N_QUESTIONS_TOTAL = 50            # full HPEP-100 protocol length
N_QUESTIONS_SEEDED = len(QUESTION_BANK)


def get_question(qid: str) -> Optional[dict]:
    return QUESTIONS_BY_ID.get(qid)


def public_question_bank() -> list[dict]:
    """Question bank shaped for the client — no internal scoring weights leaked."""
    out = []
    for q in QUESTION_BANK:
        item = {
            "id": q["id"],
            "phase": q["phase"],
            "type": q["type"],
            "text": q["text"],
        }
        if q["type"] == "structured":
            item["options"] = [{"label": o["label"]} for o in q["options"]]
        out.append(item)
    return out
