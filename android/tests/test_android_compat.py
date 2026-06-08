"""
Android compatibility tests (PATCH-08) — torch-free Python checks.

Validate that the Python-side bundle/catalog/export artifacts match what the Kotlin
Android runtime (PersonaNeedleRuntime / PersonaAssetManager / McpBridge) expects. The
Kotlin itself is not compiled here; we assert on the artifacts it consumes and on the
.kt source for the WebSocket URL contract.
"""

import re
from pathlib import Path

from needle.finetune.export.persona_bundler import PersonaBundler
from needle.finetune.export.android_export import AndroidExporter
from needle.pipeline import BulkBundler, PlaceholderFactory

_REPO = Path(__file__).resolve().parents[2]
_RUNTIME = _REPO / "android" / "runtime"
EXAMPLE_SIZES = {"model": 13.15, "k_layer": 0.8, "visual": 3.9, "audio": 2.1}


def test_manifest_schema_android_compat():
    """Bundle manifest carries the data PersonaAssetManager reads, and the Kotlin maps it."""
    m = PersonaBundler().build_manifest("socrates", EXAMPLE_SIZES)
    assert "components" in m and "total_size_mb" in m and "untrained" in m
    assert set(m["components"]) == {"model", "k_layer", "visual", "audio"}
    # Kotlin side declares the camelCase mapping (total_size_mb→sizeMb, untrained→isUntrained)
    kt = (_RUNTIME / "PersonaAssetManager.kt").read_text(encoding="utf-8")
    for field in ("sizeMb", "isUntrained", "components", "total_size_mb", "untrained"):
        assert field in kt, f"PersonaAssetManager.kt missing {field}"


def test_android_assets_structure(tmp_path):
    bb = BulkBundler(output_dir=str(tmp_path / "bundles"))
    bb.create_bundle("socrates")
    bundle_dir = Path(bb.output_dir) / "socrates"
    result = AndroidExporter().export(str(bundle_dir), str(tmp_path / "assets"))
    out = tmp_path / "assets" / "personas" / "socrates"
    assert result["asset_path"] == "assets/personas/socrates/"
    assert (out / "manifest.json").exists()
    assert any(p.suffix == ".gguf" for p in out.iterdir())
    assert result["compatibility"]["arm64_v8a"] is True


def test_gguf_magic_bytes_arm64(tmp_path):
    path = Path(PlaceholderFactory(out_dir=tmp_path).create_untrained_gguf("socrates"))
    # GGUF is architecture-agnostic; the magic header is the on-device load contract
    assert path.read_bytes()[:4] == b"GGUF"


def test_catalog_schema_for_asset_manager(tmp_path):
    cat = BulkBundler(output_dir=str(tmp_path / "bundles")).generate_catalog(limit=5)
    assert {"generated_at", "total_personas", "personas"} <= set(cat)
    for e in cat["personas"]:
        assert {"id", "size_mb", "untrained", "components"} <= set(e)


def test_mcp_bridge_websocket_url_format():
    kt = (_RUNTIME / "McpBridge.kt").read_text(encoding="utf-8")
    assert re.search(r"https?://[\w.]+:\d+", kt), "no http(s)://host:port default URL"
    assert "ws://" in kt and "wss://" in kt, "connect() must derive a ws(s):// URL"
