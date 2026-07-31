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
