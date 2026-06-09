"""
Platform ↔ needle integration tests (torch-free).

Verifies the FastAPI bridge (needle_service + persona_router), the Android ApiClient URL
contract, and Android manifest-schema compatibility. PersonaNeedle needs torch (absent
here), so needle_service exercises the persona_math fallback path.
"""

import re
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parent.parent


# ── needle_service (torch-free fallback) ─────────────────────────────────────────

def test_needle_service_works_torch_free():
    from api import needle_service
    out = needle_service.measure_ceid("socrates", "a short conversation")
    assert set("CEID").issubset(out), out
    assert out["untrained"] is True
    assert "persona_math" in out.get("source", "")        # fell back (no torch here)


def test_needle_service_ceid_format_and_unknown():
    from api import needle_service
    out = needle_service.measure_ceid("socrates", "hello")
    assert all(isinstance(out[a], float) and 0.0 <= out[a] <= 1.0 for a in "CEID")
    # unknown persona → no crash, flagged
    bad = needle_service.measure_ceid("not_a_real_persona_xyz", "hi")
    assert bad.get("error") or bad.get("untrained") is True


# ── persona_router (FastAPI) ─────────────────────────────────────────────────────

def test_persona_router_imports_with_routes():
    from api.routers.persona_router import router
    paths = {r.path for r in router.routes}
    for expected in ("/personas/", "/personas/{persona_id}/ceid",
                     "/personas/{persona_id}/drift", "/personas/{persona_id}/voice",
                     "/personas/{persona_id}/profile", "/personas/{persona_id}/history"):
        assert expected in paths, f"missing route {expected} in {paths}"


def test_main_includes_persona_router():
    text = (_REPO / "api" / "main.py").read_text(encoding="utf-8")
    assert "persona_router" in text and 'include_router(persona_router' in text


# ── Android ApiClient URL contract ───────────────────────────────────────────────

def test_apiclient_url_format():
    kt = (_REPO / "mobile" / "android" / "runtime" / "ApiClient.kt").read_text(encoding="utf-8")
    assert "/api/v1" in kt                                  # mounts under /api/v1
    assert re.search(r"/personas/\$personaId/ceid", kt)     # ceid endpoint
    assert "/voice" in kt and "/profile" in kt
    assert re.search(r"https?://[\w.]+:\d+", kt)            # has a host:port base URL


# ── Android manifest schema (what PersonaAssetManager reads) ─────────────────────

def test_android_manifest_schema_compat():
    from needle.finetune.export.persona_bundler import PersonaBundler
    m = PersonaBundler().build_manifest("socrates",
                                        {"model": 13.15, "k_layer": 0.8, "visual": 3.9, "audio": 2.1})
    assert "components" in m and "total_size_mb" in m and "untrained" in m
    assert set(m["components"]) == {"model", "k_layer", "visual", "audio"}
