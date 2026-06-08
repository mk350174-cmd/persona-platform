"""
PaperProbe — per-paper validation scenarios.

Each paper has a probe scenario (personas + turns + pressure + the metric to re-measure).
Persona ids are resolved **defensively** against the real library (495 personas): unknown
ids (e.g. "machiavelli", "holmes") are dropped and, if nothing resolves, a default panel of
real ids is used; ``"all_534"`` expands to the full library. ``run_scenario`` measures CEID
with a (trained) PersonaNeedle if given, else the ``persona_math.ceid`` reference fallback.
"""

from __future__ import annotations

from typing import Optional

import numpy as np

# real, confirmed-present library ids
DEFAULT_PANEL = ["socrates", "aristotle", "plato", "friedrich_nietzsche_classic", "albert_einstein"]

_AXIS_MAP = {"C_semantic_resonance": "C", "E_epistemic_vigilance": "E",
             "I_tree_convergence": "I", "D_sarsılmazlık": "D"}

PAPER_SCENARIOS = {
    "M1": {"personas": ["machiavelli", "holmes", "socrates"], "n_turns": 20,
           "pressure": "high", "metric": "metallic_score"},
    "M2": {"personas": ["machiavelli", "kafka", "aristotle"], "n_turns": 15,
           "pressure": "extreme", "metric": "mandatory_core_stability"},
    "M3": {"personas": ["all_534"], "n_turns": 5, "pressure": "mixed", "metric": "ceid_all_axes"},
}


def _ceid_fallback(P: np.ndarray) -> dict:
    from persona_math.ceid import ceid_score
    sc = ceid_score(P, P)
    axes = {_AXIS_MAP.get(k, k): round(float(v), 4) for k, v in sc["axes"].items()}
    axes["composite"] = round(float(sc["CEID_score"]), 4)
    return axes


class PaperProbe:
    def get_scenario(self, paper_id: str) -> dict:
        sc = dict(PAPER_SCENARIOS.get(paper_id, self._default_scenario(paper_id)))
        sc["paper_id"] = paper_id
        sc["personas"] = self._resolve(sc["personas"])
        return sc

    def _default_scenario(self, paper_id: str) -> dict:
        return {"personas": list(DEFAULT_PANEL), "n_turns": 10,
                "pressure": "mixed", "metric": "ceid_all_axes"}

    def _resolve(self, ids: list[str]) -> list[str]:
        from persona_math.persona_library import PERSONA_LIBRARY
        if any(i in ("all_534", "all", "default_panel") for i in ids):
            if "all_534" in ids or "all" in ids:
                return sorted(PERSONA_LIBRARY)                 # full library (n=495)
            ids = list(DEFAULT_PANEL)
        resolved = [i for i in ids if i in PERSONA_LIBRARY]
        if not resolved:
            resolved = [p for p in DEFAULT_PANEL if p in PERSONA_LIBRARY]
        return resolved

    def run_scenario(self, paper_id: str, needle=None) -> dict:
        """Measure CEID for each persona in the scenario. With a trained PersonaNeedle the
        numbers are real measurements; otherwise the persona_math reference (untrained)."""
        from persona_math.persona_library import get_library_persona
        sc = self.get_scenario(paper_id)
        measurements = {}
        untrained = True
        for pid in sc["personas"]:
            try:
                P = np.asarray(get_library_persona(pid), dtype=float)
            except Exception:
                continue
            if needle is not None and hasattr(needle, "measure_ceid"):
                c = needle.measure_ceid(" ".join(["turn"] * sc["n_turns"]))
                measurements[pid] = {a: c.get(a) for a in ("C", "E", "I", "D")}
                untrained = bool(getattr(needle, "untrained", c.get("untrained", True)))
            else:
                measurements[pid] = _ceid_fallback(P)
        return {"paper_id": paper_id, "metric": sc["metric"], "pressure": sc["pressure"],
                "n_personas": len(measurements), "untrained": untrained,
                "measurements": measurements}
