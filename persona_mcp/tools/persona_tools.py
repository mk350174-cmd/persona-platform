"""
Persona MCP tools (6): get_persona_profile, measure_persona_ceid, detect_drift,
generate_voice, list_personas, compare_personas.

Each tool is a plain dict ``{name, description, inputSchema, handler}`` — SDK-free, so it
can be tested without the MCP SDK. Handlers take ``(arguments: dict, graph: PersonaGraph)``
and return a JSON-serializable dict.

PersonaNeedle is used for real CEID / drift / voice when torch is available — one instance
per persona, cached in ``NEEDLE_CACHE``. When torch (or PersonaNeedle) is unavailable we
fall back to ``persona_math.ceid.ceid_score`` (the reference) and report the result as
``untrained`` / ``degraded`` rather than raising.
"""

from __future__ import annotations

from typing import Optional

import numpy as np

_AXIS_MAP = {"C_semantic_resonance": "C", "E_epistemic_vigilance": "E",
             "I_tree_convergence": "I", "D_sarsılmazlık": "D"}

# persona_id → PersonaNeedle instance (built lazily; requires torch)
NEEDLE_CACHE: dict = {}


# ── PersonaNeedle access (cached; torch-only) ────────────────────────────────────

def _build_needle(persona_id: str):
    """Construct a PersonaNeedle for a persona (requires torch). Raises without torch."""
    from needle.architecture.persona_needle import PersonaNeedle
    from needle.architecture.config import PersonaNeedleConfig
    persona = _k_layer(persona_id)
    config = PersonaNeedleConfig(persona_id=persona_id)
    return PersonaNeedle(config, persona_vector=persona)


def _get_needle(persona_id: str):
    """Return the cached PersonaNeedle for a persona (one instance each).

    Raises (ImportError without torch / any build error) so handlers fall back to the
    persona_math reference."""
    if persona_id not in NEEDLE_CACHE:
        NEEDLE_CACHE[persona_id] = _build_needle(persona_id)
    return NEEDLE_CACHE[persona_id]


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


def _measure(persona_id: str, conversation: str) -> tuple[dict, str, bool]:
    """Return (ceid C/E/I/D[+composite], source, untrained). Uses PersonaNeedle when
    torch is available, else the persona_math reference."""
    try:
        needle = _get_needle(persona_id)
        c = needle.measure_ceid(conversation)
        ceid = {a: c[a] for a in ("C", "E", "I", "D")}
        ceid["composite"] = round(float(np.mean([ceid[a] for a in ("C", "E", "I", "D")])), 4)
        untrained = bool(c.get("untrained", True))
        return ceid, ("PersonaNeedle (untrained)" if untrained else "PersonaNeedle"), untrained
    except Exception:
        P = _k_layer(persona_id)
        if P is None:
            return {}, "unavailable (unknown persona)", True
        return (_ceid_reference(P),
                "persona_math.ceid (fallback; PersonaNeedle/torch unavailable)", True)


# ── handlers ─────────────────────────────────────────────────────────────────────

def get_persona_profile(arguments: dict, graph) -> dict:
    pid = arguments["persona_id"]
    P = _k_layer(pid)
    return {
        "persona_id": pid,
        "k_layer_present": P is not None,
        "k_layer_dim": int(P.shape[0]) if P is not None else None,
        "k_layer_preview": [round(float(x), 3) for x in P[:8]] if P is not None else None,
        "ceid_reference": _ceid_reference(P) if P is not None else None,
        "ceid_history": graph.get_ceid_history(pid, limit=10),
        "recent_conversations": graph.get_memories(pid, limit=5),
        "drift_events": graph.get_drift_events(pid),
    }


def measure_persona_ceid(arguments: dict, graph) -> dict:
    pid, conversation = arguments["persona_id"], arguments["conversation"]
    ceid, source, untrained = _measure(pid, conversation)
    logged = (graph.log_ceid_measurement(pid, ceid, untrained=untrained)
              if ceid else {"backend": "skipped"})
    return {"persona_id": pid, "ceid": ceid, "untrained": untrained, "source": source,
            "logged_to": logged.get("backend"), "trend": logged.get("trend")}


def detect_drift(arguments: dict, graph) -> dict:
    pid, conversation = arguments["persona_id"], arguments["conversation"]
    try:
        needle = _get_needle(pid)
        d = needle.detect_drift(conversation)
        if d.get("drift"):
            graph.log_drift_event(pid, d.get("score"), context=conversation[:120])
        return {"persona_id": pid, **d}
    except Exception:
        return {"persona_id": pid, "drift": None, "score": None, "warning": None,
                "degraded": True, "note": "drift detection needs PersonaNeedle (torch); unavailable"}


def generate_voice(arguments: dict, graph) -> dict:
    pid, prompt = arguments["persona_id"], arguments["prompt"]
    try:
        needle = _get_needle(pid)
        voice = needle.generate_voice(prompt)
        graph.add_memory(pid, voice, tags=["generated", "voice"])
        return {"persona_id": pid, "voice": voice,
                "untrained": bool(getattr(needle, "untrained", True))}
    except Exception:
        return {"persona_id": pid, "voice": None, "degraded": True,
                "note": "voice generation needs PersonaNeedle (torch); unavailable"}


def list_personas(arguments: dict, graph) -> dict:
    from persona_math.persona_library import search_personas, PERSONA_LIBRARY
    domain = arguments.get("domain")
    tags = arguments.get("tags")
    query = arguments.get("query", "")
    specs = search_personas(query=query, domain=domain, tags=tags) if (domain or tags or query) \
        else [PERSONA_LIBRARY[k] for k in sorted(PERSONA_LIBRARY)]
    out = [{"id": s["id"], "domain": s.get("domain"), "tags": s.get("tags")} for s in specs]
    return {"count": len(out), "personas": out[:200]}


def compare_personas(arguments: dict, graph) -> dict:
    from persona_math.metrics import drift, cosine_similarity
    p1, p2 = arguments["persona_id_1"], arguments["persona_id_2"]
    P1, P2 = _k_layer(p1), _k_layer(p2)
    if P1 is None or P2 is None:
        return {"error": "one or both personas not found", "p1_found": P1 is not None,
                "p2_found": P2 is not None}
    ceid1, ceid2 = _ceid_reference(P1), _ceid_reference(P2)
    ceid_diff = {a: round(ceid1[a] - ceid2[a], 4) for a in ("C", "E", "I", "D", "composite")}
    sim = round(float(cosine_similarity(P1, P2)), 4)
    return {
        "persona_id_1": p1, "persona_id_2": p2,
        "similarity": sim, "cosine_similarity": sim,        # K-layer cosine similarity
        "drift_distance": round(float(drift(P1, P2)), 4),
        "ceid_diff": ceid_diff,
        "ceid_1": ceid1, "ceid_2": ceid2,
    }


TOOLS = [
    {"name": "get_persona_profile",
     "description": "K-layer vector + CEID reference + CEID history + recent conversations for a persona.",
     "inputSchema": {"type": "object", "properties": {"persona_id": {"type": "string"}},
                     "required": ["persona_id"]},
     "handler": get_persona_profile},
    {"name": "measure_persona_ceid",
     "description": "Measure CEID (C/E/I/D) for a conversation via PersonaNeedle (else persona_math); logs to Logseq/cache with the untrained flag.",
     "inputSchema": {"type": "object", "properties": {
         "persona_id": {"type": "string"}, "conversation": {"type": "string"}},
         "required": ["persona_id", "conversation"]},
     "handler": measure_persona_ceid},
    {"name": "detect_drift",
     "description": "Detect identity drift for a conversation via PersonaNeedle; logs a red alert to Logseq/cache if drift is found.",
     "inputSchema": {"type": "object", "properties": {
         "persona_id": {"type": "string"}, "conversation": {"type": "string"}},
         "required": ["persona_id", "conversation"]},
     "handler": detect_drift},
    {"name": "generate_voice",
     "description": "Generate text in a persona's voice via PersonaNeedle; appends the output to the persona's memory.",
     "inputSchema": {"type": "object", "properties": {
         "persona_id": {"type": "string"}, "prompt": {"type": "string"}},
         "required": ["persona_id", "prompt"]},
     "handler": generate_voice},
    {"name": "list_personas",
     "description": "List personas, optionally filtered by domain / tags / free-text query.",
     "inputSchema": {"type": "object", "properties": {
         "domain": {"type": "string"}, "tags": {"type": "array", "items": {"type": "string"}},
         "query": {"type": "string"}}},
     "handler": list_personas},
    {"name": "compare_personas",
     "description": "Compare two personas: K-layer cosine similarity + per-axis CEID difference.",
     "inputSchema": {"type": "object", "properties": {
         "persona_id_1": {"type": "string"}, "persona_id_2": {"type": "string"}},
         "required": ["persona_id_1", "persona_id_2"]},
     "handler": compare_personas},
]
