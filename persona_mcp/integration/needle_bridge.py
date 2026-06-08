"""
NeedleBridge — wire PersonaNeedle results into the persona knowledge-graph.

Pass ``NeedleBridge(graph).on_ceid_measured`` / ``on_drift_detected`` / ``on_voice_generated``
(or the bound bridge as a ``mcp_callback`` to ``PersonaNeedle.full_pipeline``) so every
model output is logged to Logseq (or the local cache, on graceful degradation). Torch-free:
it only forwards already-computed results to ``PersonaGraph``.
"""

from __future__ import annotations


class NeedleBridge:
    def __init__(self, graph):
        self.graph = graph

    def on_ceid_measured(self, persona_id: str, result: dict) -> dict:
        """``result`` carries ``{"ceid": {...}, "untrained": bool, ...}``."""
        return self.graph.log_ceid_measurement(
            persona_id, result["ceid"], untrained=result.get("untrained", True))

    def on_drift_detected(self, persona_id: str, result: dict) -> dict:
        """Log only when drift is actually detected."""
        if result.get("drift"):
            return self.graph.log_drift_event(
                persona_id, result.get("score"), context=result.get("context", ""))
        return {"backend": "skipped", "drift": False}

    def on_voice_generated(self, persona_id: str, result: dict) -> dict:
        return self.graph.add_memory(
            persona_id, result["voice"], tags=["generated", "voice"])

    # convenience: usable directly as PersonaNeedle.full_pipeline(mcp_callback=...)
    def __call__(self, persona_id: str, result: dict) -> dict:
        out = {}
        if "ceid" in result:
            out["ceid"] = self.on_ceid_measured(persona_id, result)
        if "drift" in result and isinstance(result["drift"], dict):
            out["drift"] = self.on_drift_detected(persona_id, result["drift"])
        if result.get("voice"):
            out["voice"] = self.on_voice_generated(persona_id, result)
        return out
