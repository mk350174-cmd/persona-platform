import pytest
from starlette.websockets import WebSocketDisconnect


def test_list_personas(client):
    r = client.get("/personas/")
    assert r.status_code == 200
    body = r.json()
    assert len(body) == 11
    ids = {p["persona_id"] for p in body}
    assert "mandela" in ids
    assert "machiavelli" in ids


def test_get_persona_detail(client):
    r = client.get("/personas/mandela")
    assert r.status_code == 200
    assert r.json()["persona_id"] == "mandela"


def test_get_unknown_persona_404s(client):
    r = client.get("/personas/nobody")
    assert r.status_code == 404


def test_ceid_requires_auth(client):
    r = client.post("/personas/mandela/ceid", json={"conversation": "hello"})
    assert r.status_code == 401


def test_ceid_available_persona(client, auth_headers):
    r = client.post(
        "/personas/mandela/ceid",
        json={"conversation": "I believe in reconciliation."},
        headers=auth_headers,
    )
    assert r.status_code == 200
    body = r.json()
    assert body["untrained"] is True
    assert "ceid" in body and body["ceid"]


def test_ceid_unavailable_persona_short_circuits(client, auth_headers):
    """machiavelli has no K-layer vector — must return a clear warning, not a
    silent failure or fabricated score (T2-018 honesty requirement)."""
    r = client.post(
        "/personas/machiavelli/ceid",
        json={"conversation": "test"},
        headers=auth_headers,
    )
    assert r.status_code == 200
    body = r.json()
    assert body["untrained"] is True
    assert body["ceid"] == {}
    assert "warning" in body


def test_chat_websocket_requires_token(client):
    with pytest.raises(WebSocketDisconnect) as exc_info:
        with client.websocket_connect("/personas/mandela/chat"):
            pass
    assert exc_info.value.code == 4401


def test_chat_websocket_unknown_persona_closes(client, auth_headers):
    token = auth_headers["Authorization"].split(" ", 1)[1]
    with pytest.raises(WebSocketDisconnect) as exc_info:
        with client.websocket_connect(f"/personas/nobody/chat?token={token}"):
            pass
    assert exc_info.value.code == 4404


def test_chat_websocket_echoes(client, auth_headers):
    token = auth_headers["Authorization"].split(" ", 1)[1]
    with client.websocket_connect(f"/personas/mandela/chat?token={token}") as ws:
        start = ws.receive_json()
        assert start["type"] == "session_start"
        assert start["note"] == "echo-only transport validation, no LLM completion wired yet"
        ws.send_text("hello there")
        reply = ws.receive_json()
        assert reply["type"] == "message"
        assert "echo, no LLM wired" in reply["content"]


def test_chat_history_requires_auth(client):
    r = client.get("/personas/mandela/chat/history")
    assert r.status_code == 401


def test_chat_history_empty_before_any_chat(client, auth_headers):
    r = client.get("/personas/mandela/chat/history", headers=auth_headers)
    assert r.status_code == 200
    assert r.json() == []


def test_chat_history_reflects_websocket_turns(client, auth_headers):
    token = auth_headers["Authorization"].split(" ", 1)[1]
    with client.websocket_connect(f"/personas/mandela/chat?token={token}") as ws:
        ws.receive_json()
        ws.send_text("hello there")
        ws.receive_json()

    r = client.get("/personas/mandela/chat/history", headers=auth_headers)
    assert r.status_code == 200
    body = r.json()
    assert len(body) == 2
    assert body[0]["role"] == "user"
    assert body[0]["content"] == "hello there"
    assert body[1]["role"] == "persona"


def test_chat_history_unknown_persona_404s(client, auth_headers):
    r = client.get("/personas/nobody/chat/history", headers=auth_headers)
    assert r.status_code == 404


# ── T2-019: NVIDIA-backed completions (mocked — no real API key in tests) ──────

def test_llm_chat_unavailable_without_key(monkeypatch):
    from api import llm_chat
    monkeypatch.delenv("NVIDIA_API_KEY", raising=False)
    assert llm_chat.chat_available() is False


def test_llm_chat_available_with_key(monkeypatch):
    from api import llm_chat
    monkeypatch.setenv("NVIDIA_API_KEY", "fake-key")
    assert llm_chat.chat_available() is True


def test_chat_websocket_uses_nvidia_when_configured(client, auth_headers, monkeypatch):
    from api.routers import persona_router

    monkeypatch.setenv("NVIDIA_API_KEY", "fake-key")
    monkeypatch.setattr(
        persona_router.llm_chat, "generate_reply",
        lambda system_prompt, history, user_message: f"mocked reply to: {user_message}",
    )

    token = auth_headers["Authorization"].split(" ", 1)[1]
    with client.websocket_connect(f"/personas/socrates/chat?token={token}") as ws:
        start = ws.receive_json()
        assert start["llm_backend"] == "nvidia"
        assert "NVIDIA-backed" in start["note"]
        assert start["untrained"] is True  # LLM backend != fine-tuned PersonaNeedle

        ws.send_text("What is virtue?")
        reply = ws.receive_json()
        assert reply["content"] == "mocked reply to: What is virtue?"


def test_chat_websocket_nvidia_failure_falls_back_to_echo(client, auth_headers, monkeypatch):
    from api.routers import persona_router

    monkeypatch.setenv("NVIDIA_API_KEY", "fake-key")

    def boom(system_prompt, history, user_message):
        raise RuntimeError("NVIDIA API down")

    monkeypatch.setattr(persona_router.llm_chat, "generate_reply", boom)

    token = auth_headers["Authorization"].split(" ", 1)[1]
    with client.websocket_connect(f"/personas/socrates/chat?token={token}") as ws:
        ws.receive_json()
        ws.send_text("hello")
        reply = ws.receive_json()
        assert "NVIDIA completion failed, echo fallback" in reply["content"]


def test_chat_websocket_stays_echo_without_key(client, auth_headers, monkeypatch):
    monkeypatch.delenv("NVIDIA_API_KEY", raising=False)
    token = auth_headers["Authorization"].split(" ", 1)[1]
    with client.websocket_connect(f"/personas/mandela/chat?token={token}") as ws:
        start = ws.receive_json()
        assert start["llm_backend"] == "echo"
