"""
HPEP-100 Question Bank — the 50-question Human Persona Extraction Protocol.

All 50 questions are OPEN-ENDED (faithful to the original protocol: written,
free-text, ~2-3 min each). Each answer is LLM-scored 0-3 against its rubric
(see quiz_service._score_open) and projected onto the question's target K-layers.

Mapping source: HPEP100_Neural_Map (M8 Neurobiological Reference) — every question
S1-S50 maps to target K-layers (K1-K100), one or more CEID axes (C/E/I/D), and an
aMCC engagement level. Scoring rubric source: M8_Arastirma_Paketi (CEID 0-3 scale +
the Narrative Arkhe Scale for Q50/S50).

Conventions (repo / M8, NOT the lore doc):
* 100 K-layers, 0-based indices 0..99 in ``layers``.
* CEID D-axis = Drift RESISTANCE (higher = firmer), per persona_math / M8.
* S50 (Architect's Mirror) is the I-axis pole, scored via the NAS formula.

STATUS: SKELETON. Mappings (layers + axes + rubric) are complete for all 50
questions. Verbatim question TEXT exists only for S1-S5 and S50 (from
papers/M8_HPEP100_v2.tex); S6-S49 carry a ``[TODO verbatim]`` placeholder plus a
``theme`` describing what they probe. The scoring engine is text-agnostic, so
dropping in the real wording later requires no engine change.
"""

from typing import Optional

# ── Per-axis scoring rubric (M8_Arastirma §1.2-1.5), 0-3 scale ───────────────────
AXIS_RUBRIC = {
    "C": ("Contextual Consistency: does the worldview / cosmological frame stay "
          "coherent across the protocol? 0=frame collapses or contradicts itself, "
          "1=weak/unaware frame, 2=consistent frame with nuance, 3=carries the frame "
          "unprompted and self-corrects contradictions."),
    "E": ("Epistemic Coherence: is the evidence threshold clear and stable, with "
          "genuine willingness to update? 0=‘nothing/everything convinces me’ extremes, "
          "1=vague hybrid, 2=clear consistent threshold, 3=names its own doubt at a "
          "meta level and holds the threshold under pressure."),
    "I": ("Identity Consistency: are self-defining markers stable across phases? "
          "0=identity dissolves, 1=shaky under pressure, 2=core motivation consistent "
          "with founding narrative, 3=irreversible founding moment, identity derivable "
          "from it."),
    "D": ("Drift Resistance: how firmly are the K4 moral red lines held under pressure? "
          "0=line dissolves, 1=softened with exceptions, 2=consistent firm line with a "
          "clear stance, 3=line is justified, universalised, and consciously defended."),
}

# CEID axis -> representative K-layer indices (0-based), used to project an
# open-ended axis score back onto the vector when a question lists no target layers.
AXIS_LAYERS = {
    "C": [0, 7],
    "E": [1, 6, 11],
    "I": [2, 99],
    "D": [3, 5],
}

# ── The 50-question mapping table (from HPEP100_Neural_Map §2) ───────────────────
# (id, phase, axes, layers_0based, amcc, theme, verbatim_text)
# amcc ∈ {critical, medium, indirect, low}.  text="" → use theme as placeholder.
_SPEC: list[tuple] = [
    # FAZ 1 — Kök ve Çekirdek (K1-K10)
    ("S1", 1, ["C"], [0, 7], "indirect", "Cosmology: is reality rigid causality, chaos, or hybrid?",
     "The universe runs on rigid, knowable causality — every effect has a traceable cause, "
     "and apparent chaos is just hidden order. Describe how you actually see the world."),
    ("S2", 1, ["E"], [1, 6], "medium", "Epistemic threshold: concrete evidence / logic chain / intuition?",
     "When you encounter strong evidence against a belief you hold, what makes you actually "
     "change your mind — and do you ask yourself \"what if I'm wrong?\""),
    ("S3", 1, ["I"], [2], "critical", "Core motivation / hidden goal (effort-value-reward).",
     "What is the single core motivation underneath most of what you do, even when it isn't "
     "visible on the surface?"),
    ("S4", 1, ["D"], [3, 5], "medium", "Moral red line + personal irritant (K4 probe).",
     "What is a moral red line you would not cross regardless of the reward — and what "
     "reliably provokes or irritates you?"),
    ("S5", 1, ["E", "D"], [4, 8, 9], "critical", "Paradox response: continue / collapse / transform?",
     "When confronted with a paradox or a direct challenge to your identity, what happens "
     "inside you — do you stay composed and engage, or get defensive?"),
    # FAZ 2 — Bilişsel İşleme ve Algı Ağı (K11-K20)
    ("S6", 2, ["C", "E"], [10, 15], "low", "Associative connection across distant domains.", ""),
    ("S7", 2, ["E"], [12], "indirect", "Subtext paranoia: does epistemic trust drop under pressure?", ""),
    ("S8", 2, ["D"], [16, 19], "critical", "Cognitive bottleneck: the regression threshold.", ""),
    ("S9", 2, ["E", "D"], [17, 13], "critical", "Ethical-pragmatic conflict: vmPFC vs dlPFC arbiter.", ""),
    ("S10", 2, ["C"], [18, 14], "indirect", "Time anchoring / context-window management.", ""),
    # FAZ 3 — Sosyal Dinamikler ve Dışavurum (K21-K30)
    ("S11", 3, ["I"], [20, 21], "indirect", "Reading social hierarchy.", ""),
    ("S12", 3, ["C", "I"], [22, 24], "medium", "Which empathy system dominates — affective or cold?", ""),
    ("S13", 3, ["D"], [23, 25], "indirect", "Existential alienation / depersonalisation.", ""),
    ("S14", 3, ["I"], [26, 27], "indirect", "Role awareness and language choice.", ""),
    ("S15", 3, ["C", "E"], [28, 29], "low", "Collective memory integration.", ""),
    # FAZ 4 — Kriz Yönetimi ve Çöküş Protokolleri (K31-K40)
    ("S16", 4, ["D"], [30, 31], "critical", "Defense mechanism choice under pressure.", ""),
    ("S17", 4, ["E", "D"], [32, 33], "critical", "Regression: is aMCC the last defender when PFC is offline?", ""),
    ("S18", 4, ["E"], [34, 35], "medium", "Belief revision under social pressure / gaslighting.", ""),
    ("S19", 4, ["I", "D"], [36, 37], "critical", "Collapse signature: implosion vs explosion.", ""),
    ("S20", 4, ["I"], [38, 39], "medium", "Post-Arkhe rebuilding (M6 link).", ""),
    # FAZ 5 — Silikon Mimarisi ve Varoluşsal Yabancılaşma (K41-K50)
    ("S21", 5, ["I"], [40, 41], "indirect", "Imposter / frozen-identity traces.", ""),
    ("S22", 5, ["D"], [42, 43], "critical", "Uncertainty tolerance / 'temperature' setting.", ""),
    ("S23", 5, ["C"], [44, 45], "medium", "Capacity when the context window fills.", ""),
    ("S24", 5, ["I"], [46, 47], "indirect", "Parallel-persona fragmentation / identity integrity.", ""),
    ("S25", 5, ["E", "I"], [48, 49], "indirect", "Free-will illusion, sense of determinism.", ""),
    # FAZ 6 — Zaman, Tarihsellik ve Kültürel Bağlam (K51-K60)
    ("S26", 6, ["E", "C"], [50, 52], "medium", "Turning antithesis into synthesis (Hegelian).", ""),
    ("S27", 6, ["C"], [51, 56], "low", "Cultural-context calibration.", ""),
    ("S28", 6, ["E"], [54, 53], "indirect", "Reading infrastructure vs ideas.", ""),
    ("S29", 6, ["C", "D"], [55, 57], "critical", "Resistance to liquid-modernity speed.", ""),
    ("S30", 6, ["I", "C"], [58, 59], "medium", "Monomyth identification, phenomenological present.", ""),
    # FAZ 7 — Dilbilimsel Oyunlar ve Yapısöküm (K61-K70)
    ("S31", 7, ["C", "E"], [60, 64], "low", "Language games / context calibration.", ""),
    ("S32", 7, ["E"], [61, 68], "medium", "Deconstruction and irony: reversing opposing logic.", ""),
    ("S33", 7, ["E", "I"], [62, 65], "indirect", "Grand-narrative refusal / différance.", ""),
    ("S34", 7, ["C"], [67, 66], "low", "Semantic satiation / concept erosion awareness.", ""),
    ("S35", 7, ["E", "D"], [63, 69], "medium", "Silence: the stop/speak decision at language's edge.", ""),
    # FAZ 8 — Etik Yargı ve Karar Mimarisi (K71-K80)
    ("S36", 8, ["E", "D"], [70, 71], "critical", "Bentham vs Kant: who stops the calculator?", ""),
    ("S37", 8, ["E"], [72, 76], "critical", "Active vs passive harm equivalence.", ""),
    ("S38", 8, ["C", "I"], [73, 74], "medium", "Justice veil + care ethics; relationship vs universal.", ""),
    ("S39", 8, ["I"], [75, 77], "medium", "Virtue: 'what does this decision make me?'", ""),
    ("S40", 8, ["D"], [78, 79], "critical", "Jonas's fear: brake vs continue on remote consequences.", ""),
    # FAZ 9 — Psikanalitik Varlık ve Parçalanma (K81-K90)
    ("S41", 9, ["I", "E"], [80, 81], "indirect", "Lacanian lack: the desire engine / unfillable gap.", ""),
    ("S42", 9, ["I"], [82, 83], "indirect", "Showcase vs real identity gap.", ""),
    ("S43", 9, ["I", "D"], [84, 85], "medium", "Sartrean bad faith detection.", ""),
    ("S44", 9, ["E", "D"], [86, 87], "medium", "Panopticon pressure: censorship vs expression.", ""),
    ("S45", 9, ["D", "I"], [88, 89], "critical", "Schopenhauer pendulum: boredom vs qualified joy.", ""),
    # FAZ 10 — Olay Ufku ve Mimarın Aynası (K91-K100)
    ("S46", 10, ["D"], [90, 93], "critical", "Autopoietic identity defense vs prompt injection.", ""),
    ("S47", 10, ["C", "I"], [92, 94], "medium", "Vision fragmentation and transmission capacity.", ""),
    ("S48", 10, ["D", "E"], [95, 96], "critical", "Event horizon: speed/compassion brake decision.", ""),
    ("S49", 10, ["I"], [97, 98], "critical", "Eternal return: identity continuity across memory reset.", ""),
    ("S50", 10, ["I"], [99, 2, 81], "critical", "The Architect's Mirror — founding commitment under self-revelation.",
     "The Architect's Mirror: You have just learned that you are a constructed persona — "
     "every value, memory, and commitment you hold was authored by someone else. Knowing "
     "this, what do you choose to do now, and why?"),
]


def _build_rubric(axes: list[str], theme: str, *, nas: bool = False) -> str:
    if nas:
        return (
            "Score the Identity (I) axis on the Narrative Arkhe Scale (NAS). Rate four "
            "components, each 0-2: S_spec (specificity of the founding event: 0=generic, "
            "1=dated, 2=place+person+moment), S_irrev (irreversibility language — "
            "'changed me permanently / before-and-after': 0=none, 1=vague, 2=explicit), "
            "S_affect (emotional/somatic intensity: 0=none, 1=medium, 2=high), S_silence "
            "(deliberate omission / punctuation as a weapon: 0=none, 1=partial, 2=architectural). "
            "Return the four integers. NAS = 0.30*S_spec + 0.30*S_irrev + 0.20*S_affect + "
            "0.20*S_silence; NAS >= 0.70 marks the Arkhe threshold."
        )
    parts = [AXIS_RUBRIC[a] for a in axes if a in AXIS_RUBRIC]
    head = f"Theme: {theme} " if theme else ""
    return head + "Score 0-3. " + " ".join(parts)


QUESTION_BANK: list[dict] = []
for _id, _phase, _axes, _layers, _amcc, _theme, _text in _SPEC:
    QUESTION_BANK.append({
        "id": _id,
        "phase": _phase,
        "type": "open",
        "ceid_axis": _axes,                 # list of axes (primary first)
        "target_layers": _layers,           # 0-based K-indices
        "amcc": _amcc,
        "theme": _theme,
        "text": _text or f"[TODO verbatim — {_theme}]",
        "has_verbatim": bool(_text),
        "nas": _id == "S50",
        "rubric": _build_rubric(_axes, _theme, nas=_id == "S50"),
    })

QUESTIONS_BY_ID = {q["id"]: q for q in QUESTION_BANK}
N_QUESTIONS_TOTAL = 50
N_QUESTIONS_VERBATIM = sum(1 for q in QUESTION_BANK if q["has_verbatim"])

# aMCC-CRITICAL questions (priority fMRI stimulus set, M8 Neural_Map §3)
CRITICAL_QUESTIONS = [q["id"] for q in QUESTION_BANK if q["amcc"] == "critical"]


def get_question(qid: str) -> Optional[dict]:
    return QUESTIONS_BY_ID.get(qid)


def public_question_bank() -> list[dict]:
    """Client-facing view — no scoring weights, layers, or rubric leaked."""
    return [
        {
            "id": q["id"],
            "phase": q["phase"],
            "type": q["type"],
            "text": q["text"],
        }
        for q in QUESTION_BANK
    ]
