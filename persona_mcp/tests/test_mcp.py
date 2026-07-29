"""
persona_mcp tests.

Most run without the MCP SDK and without torch (Logseq client mock, template render,
graceful degradation, persona_math integration). The server/7-tool build test requires
the `mcp` SDK and skips cleanly if it's absent.
"""


import httpx
import pytest

from persona_mcp import ALL_TOOLS, DISPATCH
from persona_mcp.logseq import LogseqClient, LogseqUnavailable, PersonaGraph

EXPECTED_TOOLS = {
    "get_persona_profile", "measure_persona_ceid", "detect_drift", "generate_voice",
    "add_conversation_memory", "get_persona_history", "list_personas", "compare_personas",
}


# ── tool registry (SDK-free) ─────────────────────────────────────────────────────

def test_eight_tools_registered():
    assert len(ALL_TOOLS) == 8
    assert {t["name"] for t in ALL_TOOLS} == EXPECTED_TOOLS
    assert set(DISPATCH) == EXPECTED_TOOLS
    for t in ALL_TOOLS:
        assert t["inputSchema"]["type"] == "object" and callable(t["handler"])


# ── MCP server (needs the SDK) ───────────────────────────────────────────────────

def test_server_builds_with_all_tools(tmp_path):
    pytest.importorskip("mcp")
    from persona_mcp import build_server
    graph = PersonaGraph(client=None, cache_dir=tmp_path)
    server = build_server(graph)
    assert server is not None and server.name == "persona-mcp"


# ── Logseq client (mock transport; no real Logseq) ───────────────────────────────

def test_logseq_client_mock_success():
    def handler(request):
        return httpx.Response(200, json={"original-name": "TestPage"})
    client = LogseqClient(transport=httpx.MockTransport(handler), token="tok")
    assert client.get_page("TestPage")["original-name"] == "TestPage"
    assert client.available() is True


def test_logseq_client_unavailable_raises():
    def handler(request):
        raise httpx.ConnectError("connection refused")
    client = LogseqClient(transport=httpx.MockTransport(handler))
    with pytest.raises(LogseqUnavailable):
        client.get_page("X")
    assert client.available() is False


# ── PersonaGraph template render (jinja2) ────────────────────────────────────────

def test_template_render(tmp_path):
    g = PersonaGraph(client=None, cache_dir=tmp_path)
    out = g.render("persona_page.md", persona_id="aristotle", domain="Philosophy",
                   ceid_baseline=0.91, created_date="2026-06-07", mandatory_core_score=0.74,
                   virtu_index=0.80, C=0.9, E=0.92, I=0.78, D=0.95,
                   ceid_history="", drift_events="", conversation_memory="")
    assert "persona-id: aristotle" in out
    assert "C=0.9 E=0.92 I=0.78 D=0.95" in out


# ── graceful degradation: Logseq down → cache, no exception ──────────────────────

def test_graceful_degradation_to_cache(tmp_path):
    def refuse(request):
        raise httpx.ConnectError("refused")
    client = LogseqClient(transport=httpx.MockTransport(refuse))
    g = PersonaGraph(client=client, cache_dir=tmp_path)
    res = g.add_memory("aristotle", "hello world", tags=["greeting"])
    assert res["backend"] == "cache"                       # fell back, no error
    assert (tmp_path / "aristotle.memory.jsonl").exists()
    g.log_ceid_measurement("aristotle", {"C": 0.9, "E": 0.9, "I": 0.9, "D": 0.9, "composite": 0.9})
    assert g.get_ceid_history("aristotle")                 # readable from cache


# ── persona_math integration (torch-free fallback) ───────────────────────────────

def test_measure_ceid_falls_back_to_persona_math(tmp_path):
    g = PersonaGraph(client=None, cache_dir=tmp_path)
    out = DISPATCH["measure_persona_ceid"]({"persona_id": "socrates",
                                            "conversation": "a short test"}, g)
    assert set("CEID") <= set(out["ceid"])
    # Source depends on whether torch is installed (PersonaNeedle path) or not
    # (persona_math reference fallback) — either is correct, but neither is trained yet.
    assert "persona_math" in out["source"] or "PersonaNeedle" in out["source"]
    assert out["untrained"] is True
    assert out["logged_to"] in ("cache", "logseq")


def test_get_persona_profile_includes_k_layer(tmp_path):
    g = PersonaGraph(client=None, cache_dir=tmp_path)
    prof = DISPATCH["get_persona_profile"]({"persona_id": "socrates"}, g)
    assert prof["k_layer_present"] and prof["k_layer_dim"] == 100
    assert set("CEID") <= set(prof["ceid_reference"])


def test_compare_personas(tmp_path):
    g = PersonaGraph(client=None, cache_dir=tmp_path)
    out = DISPATCH["compare_personas"]({"persona_id_1": "socrates",
                                        "persona_id_2": "aristotle"}, g)
    assert 0.0 <= out["cosine_similarity"] <= 1.0 and "ceid_1" in out
