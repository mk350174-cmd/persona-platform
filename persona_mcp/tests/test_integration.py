"""
persona_mcp ↔ PersonaNeedle integration tests (PATCH-06) — torch-free + SDK-free.

The real PersonaNeedle path needs torch (absent here), so the bridge/handler tests use the
persona_math fallback or monkeypatched builders; they exercise the wiring (graph logging,
NEEDLE_CACHE, untrained/trained blocks, the new generate_voice tool) without torch.
"""

import pytest

from persona_mcp.logseq import PersonaGraph
from persona_mcp.integration import NeedleBridge
from persona_mcp.tools import ALL_TOOLS, DISPATCH, persona_tools

CEID = {"C": 0.9, "E": 0.92, "I": 0.78, "D": 0.95, "composite": 0.89}


def _graph(tmp_path):
    return PersonaGraph(client=None, cache_dir=tmp_path)        # no Logseq → cache


def test_needle_bridge_init(tmp_path):
    g = _graph(tmp_path)
    assert NeedleBridge(g).graph is g


def test_bridge_ceid_logs_to_graph(tmp_path):
    g = _graph(tmp_path)
    res = NeedleBridge(g).on_ceid_measured("machiavelli", {"ceid": CEID, "untrained": True})
    assert res["backend"] == "cache"                            # graceful degradation
    hist = g.get_ceid_history("machiavelli")
    assert len(hist) == 1 and hist[0]["untrained"] is True


def test_bridge_drift_logs_only_on_drift(tmp_path):
    g = _graph(tmp_path)
    bridge = NeedleBridge(g)
    bridge.on_drift_detected("p", {"drift": True, "score": 0.81})
    bridge.on_drift_detected("p", {"drift": False, "score": 0.10})   # must NOT log
    events = g.get_drift_events("p")
    assert len(events) == 1 and events[0]["score"] == 0.81


def test_bridge_voice_adds_memory(tmp_path):
    g = _graph(tmp_path)
    NeedleBridge(g).on_voice_generated("p", {"voice": "I am the Prince."})
    mem = g.get_memories("p")
    assert len(mem) == 1 and "voice" in (mem[0]["tags"] or [])


def test_generate_voice_tool_registered():
    assert "generate_voice" in DISPATCH
    assert "generate_voice" in {t["name"] for t in ALL_TOOLS}


def test_needle_cache_single_instance(monkeypatch):
    """Same persona twice → one PersonaNeedle instance (cache hit)."""
    calls = {"n": 0}

    class _Dummy:
        def __init__(self, pid):
            self.pid = pid

    def fake_build(pid):
        calls["n"] += 1
        return _Dummy(pid)

    persona_tools.NEEDLE_CACHE.clear()
    monkeypatch.setattr(persona_tools, "_build_needle", fake_build)
    a = persona_tools._get_needle("machiavelli")
    b = persona_tools._get_needle("machiavelli")
    assert a is b and calls["n"] == 1
    persona_tools.NEEDLE_CACHE.clear()


def test_untrained_yellow_trained_green(tmp_path):
    g = _graph(tmp_path)
    yellow = g.log_ceid_measurement("p", CEID, untrained=True)
    green = g.log_ceid_measurement("p", CEID, untrained=False)
    assert yellow["marker"] == "🟡" and "UNTRAINED" in yellow["block"]
    assert green["marker"] == "🟢" and "TRAINED" in green["block"]


def test_measure_handler_torch_free_fallback(tmp_path):
    """No torch here → measure_persona_ceid falls back to persona_math, untrained=True."""
    g = _graph(tmp_path)
    out = DISPATCH["measure_persona_ceid"](
        {"persona_id": "socrates", "conversation": "a short test"}, g)   # real library id
    assert out["persona_id"] == "socrates"
    assert set("CEID").issubset(out["ceid"]) and out["untrained"] is True
    assert "persona_math" in out["source"] or "PersonaNeedle" in out["source"]
