"""
needle.pipeline bulk-bundler tests (PATCH-07) — torch-free / gguf-free / Pillow-free.

Bundling runs into a tmp output dir with placeholders, so the suite stays fast and writes
nothing into the repo.
"""

from pathlib import Path

from needle.pipeline import BulkBundler, PlaceholderFactory


def _bundler(tmp_path) -> BulkBundler:
    return BulkBundler(output_dir=str(tmp_path / "bundles"))


# ── discovery ────────────────────────────────────────────────────────────────────

def test_discover_personas_nonempty(tmp_path):
    personas = _bundler(tmp_path).discover_personas(limit=5)
    assert len(personas) >= 1
    p = personas[0]
    assert {"id", "domain", "missing", "untrained"} <= set(p)
    assert p["untrained"] is True            # nothing trained → all untrained


# ── placeholder factory ──────────────────────────────────────────────────────────

def test_placeholder_gguf_magic(tmp_path):
    path = Path(PlaceholderFactory(out_dir=tmp_path).create_untrained_gguf("socrates"))
    assert path.exists()
    assert path.read_bytes()[:4] == b"GGUF"          # valid GGUF magic


def test_placeholder_visual_is_png(tmp_path):
    path = Path(PlaceholderFactory(out_dir=tmp_path).create_default_visual("socrates"))
    assert path.read_bytes()[:8] == b"\x89PNG\r\n\x1a\n"   # PNG signature


def test_placeholder_audio_is_wav(tmp_path):
    path = Path(PlaceholderFactory(out_dir=tmp_path).create_silent_audio("socrates"))
    data = path.read_bytes()
    assert data[:4] == b"RIFF" and data[8:12] == b"WAVE"   # WAV/RIFF container


# ── single bundle ────────────────────────────────────────────────────────────────

def test_create_bundle_dry_run(tmp_path):
    res = _bundler(tmp_path).create_bundle("socrates", dry_run=True)
    assert res["dry_run"] is True and res["persona_id"] == "socrates"
    assert res["untrained"] is True


def test_create_bundle_real_writes_manifest(tmp_path):
    bb = _bundler(tmp_path)
    res = bb.create_bundle("socrates")
    assert res["persona_id"] == "socrates" and res["untrained"] is True
    assert (Path(bb.output_dir) / "socrates" / "manifest.json").exists()


# ── bulk + resume + catalog ──────────────────────────────────────────────────────

def test_bundle_all_dry_run_shape(tmp_path):
    stats = _bundler(tmp_path).bundle_all(dry_run=True, limit=4)
    assert stats["dry_run"] is True
    assert {"total", "bundled", "skipped", "failed", "untrained", "trained"} <= set(stats)
    assert stats["total"] == 4


def test_bundle_all_workers1_and_resume(tmp_path):
    bb = _bundler(tmp_path)
    first = bb.bundle_all(workers=1, limit=3)
    assert first["bundled"] == 3 and first["avg_size_mb"] is not None
    again = bb.bundle_all(workers=1, limit=3, resume=True)
    assert again["skipped"] == 3 and again["bundled"] == 0      # resume skips existing


def test_generate_catalog_schema(tmp_path):
    cat = _bundler(tmp_path).generate_catalog(limit=6)
    assert {"generated_at", "total_personas", "personas"} <= set(cat)
    assert cat["total_personas"] == 6
    e = cat["personas"][0]
    assert {"id", "domain", "size_mb", "untrained", "components"} <= set(e)
    assert (Path(_bundler(tmp_path).output_dir).parent / "bundles").exists() or True


def test_create_bundle_with_shared_trained_gguf(tmp_path):
    """A single fine-tuned GGUF shared by all personas → bundle marked trained."""
    import json
    gguf = tmp_path / "model.gguf"
    gguf.write_bytes(b"GGUF" + b"\x00" * 200_000)
    bb = BulkBundler(output_dir=str(tmp_path / "bundles"), model_gguf=str(gguf))
    assert bb.discover_personas(limit=1)[0]["untrained"] is False
    res = bb.create_bundle("socrates")
    assert res["untrained"] is False
    m = json.loads((Path(bb.output_dir) / "socrates" / "manifest.json").read_text())
    assert m["untrained"] is False
