"""HPEP Studio API — integration tests."""

import pytest
from fastapi.testclient import TestClient

from api.main import app
from persona_math.compiler import SUPPORTED_PLATFORMS, SUPPORTED_TIERS


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="module")
def registered(client):
    """Register a user and return (api_key, workspace_id) with team plan."""
    r = client.post(
        "/auth/register",
        json={"email": "test_suite@hpep.studio", "workspace_name": "Test Workspace"},
    )
    assert r.status_code in (200, 201), r.text
    data = r.json()
    api_key, ws_id = data["api_key"], data["workspace_id"]

    # Upgrade workspace to team plan so quota never blocks tests
    from api.db import SessionLocal, Workspace as WsModel
    db = SessionLocal()
    try:
        ws = db.query(WsModel).filter(WsModel.id == ws_id).first()
        if ws:
            ws.plan_tier = "team"
            db.commit()
    finally:
        db.close()

    return api_key, ws_id


# ── Health ────────────────────────────────────────────────────────────────────

class TestHealth:
    def test_health_ok(self, client):
        r = client.get("/health")
        assert r.status_code == 200
        body = r.json()
        assert body["status"] in ("ok", "degraded")
        assert "db" in body
        assert "library_personas" in body


# ── Auth ──────────────────────────────────────────────────────────────────────

class TestAuth:
    def test_register_creates_user_and_workspace(self, client):
        r = client.post(
            "/auth/register",
            json={"email": "newuser@hpep.studio", "workspace_name": "My WS"},
        )
        assert r.status_code in (200, 201)
        body = r.json()
        assert body["api_key"].startswith("hpep_")
        assert "workspace_id" in body

    def test_register_duplicate_email(self, client):
        payload = {"email": "dup@hpep.studio", "workspace_name": "WS"}
        client.post("/auth/register", json=payload)  # first
        r = client.post("/auth/register", json=payload)  # duplicate
        assert r.status_code == 409

    def test_me_with_valid_key(self, client, registered):
        api_key, _ = registered
        r = client.get("/me", headers={"X-API-Key": api_key})
        assert r.status_code == 200
        assert r.json()["email"] == "test_suite@hpep.studio"

    def test_me_with_invalid_key(self, client):
        r = client.get("/me", headers={"X-API-Key": "bad_key"})
        assert r.status_code == 401


# ── Workspaces ────────────────────────────────────────────────────────────────

class TestWorkspaces:
    def test_list_workspaces(self, client, registered):
        api_key, ws_id = registered
        r = client.get("/workspaces", headers={"X-API-Key": api_key})
        assert r.status_code == 200
        ws_list = r.json()["workspaces"]
        assert any(w["id"] == ws_id for w in ws_list)

    def test_get_workspace(self, client, registered):
        api_key, ws_id = registered
        r = client.get(f"/workspaces/{ws_id}", headers={"X-API-Key": api_key})
        assert r.status_code == 200
        body = r.json()
        assert body["id"] == ws_id
        assert "limits" in body
        assert "persona_count" in body

    def test_get_wrong_workspace_returns_403(self, client, registered):
        api_key, _ = registered
        r = client.get("/workspaces/nonexistent-id", headers={"X-API-Key": api_key})
        assert r.status_code in (403, 404)


# ── Custom Personas ───────────────────────────────────────────────────────────

class TestPersonas:
    def _headers(self, api_key):
        return {"X-API-Key": api_key}

    def test_create_persona(self, client, registered):
        api_key, ws_id = registered
        r = client.post(
            f"/workspaces/{ws_id}/personas",
            headers=self._headers(api_key),
            json={
                "name": "Strategic Thinker",
                "blocks": {"B1": 0.9, "B3": 0.85, "B7": 0.75},
                "description": "A high-C analytical persona",
            },
        )
        assert r.status_code == 201, r.text
        body = r.json()
        assert body["name"] == "Strategic Thinker"
        assert isinstance(body["ceid_score"], float)
        assert 0.0 <= body["ceid_score"] <= 1.0
        assert body["version"] == 1

    def test_create_persona_with_k_overrides(self, client, registered):
        api_key, ws_id = registered
        r = client.post(
            f"/workspaces/{ws_id}/personas",
            headers=self._headers(api_key),
            json={
                "name": "Overridden",
                "blocks": {"B1": 0.8},
                "k_overrides": {"0": 0.95, "9": 0.1},
            },
        )
        assert r.status_code == 201
        assert r.json()["name"] == "Overridden"

    def test_list_personas(self, client, registered):
        api_key, ws_id = registered
        r = client.get(
            f"/workspaces/{ws_id}/personas",
            headers=self._headers(api_key),
        )
        assert r.status_code == 200
        assert "personas" in r.json()

    def test_get_persona(self, client, registered):
        api_key, ws_id = registered
        # Create first
        rc = client.post(
            f"/workspaces/{ws_id}/personas",
            headers=self._headers(api_key),
            json={"name": "GetMe", "blocks": {"B2": 0.7}},
        )
        persona_id = rc.json()["id"]
        # Then get
        r = client.get(
            f"/workspaces/{ws_id}/personas/{persona_id}",
            headers=self._headers(api_key),
        )
        assert r.status_code == 200
        assert r.json()["id"] == persona_id

    def test_update_persona(self, client, registered):
        api_key, ws_id = registered
        rc = client.post(
            f"/workspaces/{ws_id}/personas",
            headers=self._headers(api_key),
            json={"name": "Updatable", "blocks": {"B1": 0.5}},
        )
        persona_id = rc.json()["id"]
        r = client.put(
            f"/workspaces/{ws_id}/personas/{persona_id}",
            headers=self._headers(api_key),
            json={"name": "Updated Name", "blocks": {"B1": 0.9, "B5": 0.8}},
        )
        assert r.status_code == 200
        body = r.json()
        assert body["name"] == "Updated Name"
        assert body["version"] == 2

    def test_delete_persona(self, client, registered):
        api_key, ws_id = registered
        rc = client.post(
            f"/workspaces/{ws_id}/personas",
            headers=self._headers(api_key),
            json={"name": "DeleteMe", "blocks": {}},
        )
        persona_id = rc.json()["id"]
        r = client.delete(
            f"/workspaces/{ws_id}/personas/{persona_id}",
            headers=self._headers(api_key),
        )
        assert r.status_code == 204
        # Confirm gone
        r2 = client.get(
            f"/workspaces/{ws_id}/personas/{persona_id}",
            headers=self._headers(api_key),
        )
        assert r2.status_code == 404

    def test_create_persona_missing_name_returns_422(self, client, registered):
        api_key, ws_id = registered
        r = client.post(
            f"/workspaces/{ws_id}/personas",
            headers=self._headers(api_key),
            json={"blocks": {"B1": 0.5}},
        )
        assert r.status_code == 422


# ── CEID Diagnostic ───────────────────────────────────────────────────────────

class TestCeid:
    def _create_persona(self, client, api_key, ws_id, name, blocks):
        r = client.post(
            f"/workspaces/{ws_id}/personas",
            headers={"X-API-Key": api_key},
            json={"name": name, "blocks": blocks},
        )
        assert r.status_code == 201
        return r.json()["id"]

    def test_ceid_diagnostic_axes(self, client, registered):
        api_key, ws_id = registered
        pid = self._create_persona(client, api_key, ws_id, "CeidTest", {"B1": 0.9, "B3": 0.8})
        r = client.get(
            f"/workspaces/{ws_id}/personas/{pid}/ceid",
            headers={"X-API-Key": api_key},
        )
        assert r.status_code == 200
        body = r.json()
        for axis in ("c_axis", "e_axis", "i_axis", "d_axis", "overall"):
            assert axis in body, f"Missing key: {axis}"
            assert 0.0 <= body[axis] <= 1.0, f"{axis} out of range: {body[axis]}"

    def test_compare_personas(self, client, registered):
        api_key, ws_id = registered
        pid1 = self._create_persona(client, api_key, ws_id, "P1", {"B1": 0.9})
        pid2 = self._create_persona(client, api_key, ws_id, "P2", {"B1": 0.1})
        r = client.get(
            f"/workspaces/{ws_id}/personas/{pid1}/compare",
            headers={"X-API-Key": api_key},
            params={"with_id": pid2},
        )
        assert r.status_code == 200
        body = r.json()
        assert "cosine_similarity" in body
        assert 0.0 <= body["cosine_similarity"] <= 1.0


# ── Compile ───────────────────────────────────────────────────────────────────

class TestCompile:
    def _setup(self, client, api_key, ws_id):
        r = client.post(
            f"/workspaces/{ws_id}/personas",
            headers={"X-API-Key": api_key},
            json={"name": "CompileTarget", "blocks": {"B1": 0.8, "B2": 0.7}},
        )
        return r.json()["id"]

    def test_compile_single(self, client, registered):
        api_key, ws_id = registered
        pid = self._setup(client, api_key, ws_id)
        r = client.post(
            f"/workspaces/{ws_id}/personas/{pid}/compile",
            headers={"X-API-Key": api_key},
            json={"platform": "claude", "tier": "standard"},
        )
        assert r.status_code == 200
        body = r.json()
        assert "system_instruction" in body
        assert len(body["system_instruction"]) > 50

    def test_compile_all_returns_nine_outputs(self, client, registered):
        api_key, ws_id = registered
        pid = self._setup(client, api_key, ws_id)
        r = client.post(
            f"/workspaces/{ws_id}/personas/{pid}/compile/all",
            headers={"X-API-Key": api_key},
            json={},
        )
        assert r.status_code == 200
        body = r.json()
        # Response has by_platform (4 keys) and by_tier (3 keys)
        assert "by_platform" in body
        assert "by_tier" in body
        assert len(body["by_platform"]) == len(SUPPORTED_PLATFORMS)
        assert len(body["by_tier"]) == len(SUPPORTED_TIERS)


# ── Export ────────────────────────────────────────────────────────────────────

class TestExport:
    def _setup(self, client, api_key, ws_id):
        r = client.post(
            f"/workspaces/{ws_id}/personas",
            headers={"X-API-Key": api_key},
            json={"name": "ExportTarget", "blocks": {"B1": 0.6, "B4": 0.8}},
        )
        return r.json()["id"]

    def test_export_json(self, client, registered):
        api_key, ws_id = registered
        pid = self._setup(client, api_key, ws_id)
        r = client.get(
            f"/workspaces/{ws_id}/personas/{pid}/export",
            headers={"X-API-Key": api_key},
            params={"format": "json"},
        )
        assert r.status_code == 200
        body = r.json()
        assert "persona" in body
        assert body["persona"]["name"] == "ExportTarget"
        assert "blocks" in body["persona"]

    def test_export_character_sheet(self, client, registered):
        api_key, ws_id = registered
        pid = self._setup(client, api_key, ws_id)
        r = client.get(
            f"/workspaces/{ws_id}/personas/{pid}/export",
            headers={"X-API-Key": api_key},
            params={"format": "character-sheet"},
        )
        assert r.status_code == 200
        body = r.json()
        assert "character_sheet" in body
        assert "B1" in body["character_sheet"]


# ── Library ───────────────────────────────────────────────────────────────────

class TestLibrary:
    def test_list_library(self, client, registered):
        api_key, _ = registered
        r = client.get("/library", headers={"X-API-Key": api_key})
        assert r.status_code == 200
        body = r.json()
        assert "personas" in body
        assert body["total"] > 0

    def test_library_search(self, client, registered):
        api_key, _ = registered
        r = client.get("/library", headers={"X-API-Key": api_key}, params={"q": "aristotle"})
        assert r.status_code == 200

    def test_library_import(self, client, registered):
        api_key, ws_id = registered
        # Get first library persona id
        lib_r = client.get("/library", headers={"X-API-Key": api_key}, params={"limit": 1})
        assert lib_r.status_code == 200
        personas = lib_r.json()["personas"]
        if not personas:
            pytest.skip("Library empty")
        lib_id = personas[0]["id"]
        r = client.post(
            f"/workspaces/{ws_id}/personas/import/{lib_id}",
            headers={"X-API-Key": api_key},
        )
        assert r.status_code in (200, 201)
        assert "persona_id" in r.json()
