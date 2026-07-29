"""
PersonaNeedle fine-tune + quantization tests.

Torch-free tests (LoRA config + analytic estimator, bundler manifest / size, Android export)
always run — they verify the pieces that need no torch. The LoRA-adapter / loss / trainer /
quantizer tests require torch (and gguf) and skip cleanly where they are not installed.
"""

import json

import pytest

from needle.finetune import LoRAConfig, PersonaBundler, AndroidExporter, validate_size
from needle.finetune.lora.config import estimate_lora_trainable_params, n_attention_blocks
from needle.finetune.export.persona_bundler import default_model_size_mb
from needle.architecture.config import PersonaNeedleConfig, estimate_param_count

try:
    import torch  # noqa: F401
    HAS_TORCH = True
except Exception:
    HAS_TORCH = False

requires_torch = pytest.mark.skipif(not HAS_TORCH, reason="torch not installed")

CFG = PersonaNeedleConfig(persona_id="machiavelli")
EXAMPLE_SIZES = {"model": 13.15, "k_layer": 0.8, "visual": 3.9, "audio": 2.1}   # → 19.95 MB


# ── torch-free: LoRA config + analytic estimator ─────────────────────────────────

def test_lora_config_defaults():
    c = LoRAConfig()
    assert c.r == 8 and c.alpha == 16 and c.scale == 2.0
    assert c.target_modules == ["q_proj", "k_proj", "v_proj", "o_proj"]   # attention-only
    assert c.bias == "none"


def test_lora_config_validation_raises():
    with pytest.raises(ValueError):
        LoRAConfig(r=0)
    with pytest.raises(ValueError):
        LoRAConfig(dropout=1.0)
    with pytest.raises(ValueError):
        LoRAConfig(target_modules=[])
    with pytest.raises(ValueError):
        LoRAConfig(target_modules=["mlp"])           # SAN has no FFN
    with pytest.raises(ValueError):
        LoRAConfig(bias="sometimes")


def test_estimate_lora_trainable_params():
    n = estimate_lora_trainable_params(CFG, LoRAConfig())
    assert n_attention_blocks(CFG) == 12 + 2 * 8          # 28 attention blocks
    assert n == 802_816                                    # 28 · (6·r·h + 2·r·kv_dim), r=8
    assert 0.5e6 < n < 1.0e6                               # ~0.8M (honest; not 0.5M)
    assert n < 0.10 * estimate_param_count(CFG)            # ≪ frozen backbone (~3%)


# ── torch-free: PersonaBundler manifest + size ───────────────────────────────────

def test_default_model_size_is_honest_13mb():
    assert 12.0 < default_model_size_mb() < 14.0          # ≈13.15 MB INT4 of the 26M SAN


def test_bundler_manifest_schema_and_size_ok():
    m = PersonaBundler().build_manifest("machiavelli", EXAMPLE_SIZES)
    assert m["persona_id"] == "machiavelli" and m["version"] == "1.0"
    assert set(m["components"]) == {"model", "k_layer", "visual", "audio"}
    for comp in m["components"].values():
        assert "path" in comp and "size_mb" in comp
    assert m["total_size_mb"] == pytest.approx(19.95)
    assert m["size_ok"] is True and m["untrained"] is False


def test_bundler_size_validation_bounds():
    assert validate_size(15.0) and validate_size(20.0) and validate_size(18.95)
    assert not validate_size(14.99) and not validate_size(20.01)
    too_small = PersonaBundler().build_manifest("p", {"model": 5.0, "k_layer": 0, "visual": 0, "audio": 0})
    assert too_small["size_ok"] is False                  # 5 MB < 15 MB band


def test_manifest_json_roundtrips(tmp_path):
    gguf = tmp_path / "machiavelli.gguf"
    gguf.write_bytes(b"\x00" * 300_000)   # ~0.3 MB
    klayer = tmp_path / "k.npy"
    klayer.write_bytes(b"\x00" * 50_000)  # ~0.05 MB
    PersonaBundler().bundle("machiavelli", str(gguf), str(klayer), "", "",
                            output_dir=str(tmp_path / "out"))
    manifest_file = tmp_path / "out" / "machiavelli" / "manifest.json"
    assert manifest_file.exists()
    reloaded = json.loads(manifest_file.read_text())
    assert reloaded["persona_id"] == "machiavelli"
    assert reloaded["components"]["model"]["size_mb"] > 0  # real gguf bytes measured
    assert "visual" in reloaded["components"]              # missing component still present


# ── torch-free: AndroidExporter output structure ─────────────────────────────────

def test_android_exporter_output_structure(tmp_path):
    bundle = tmp_path / "bundle"
    bundle.mkdir()
    (bundle / "machiavelli.gguf").write_bytes(b"\x00" * 512)
    manifest = PersonaBundler().build_manifest("machiavelli", EXAMPLE_SIZES)
    (bundle / "manifest.json").write_text(json.dumps(manifest))

    result = AndroidExporter().export(str(bundle), str(tmp_path / "assets"))
    assert result["asset_path"] == "assets/personas/machiavelli/"
    out_dir = tmp_path / "assets" / "personas" / "machiavelli"
    assert (out_dir / "machiavelli.gguf").exists() and (out_dir / "manifest.json").exists()
    assert result["compatibility"]["arm64_v8a"] is True
    assert result["compatibility"]["gguf_present"] is True and result["compatibility"]["ready"] is True
    assert "arm64-v8a" in result["build_gradle_note"]


# ── torch-required: LoRA adapter / losses / trainer / quantizer ──────────────────

def _tiny_cfg():
    return PersonaNeedleConfig(persona_id="p", vocab_size=256, hidden_dim=64, encoder_layers=2,
                               decoder_layers=2, num_heads=4, kv_heads=2, max_context=32)


@requires_torch
def test_lora_adapter_trainable_matches_estimate():
    from needle.architecture.san import SAN
    from needle.finetune.lora.adapter import LoRAAdapter
    cfg, lcfg = _tiny_cfg(), LoRAConfig()
    adapter = LoRAAdapter(SAN(cfg), lcfg)
    adapter.apply()
    assert adapter.trainable_parameters() == estimate_lora_trainable_params(cfg, lcfg)
    assert adapter.trainable_parameters() < 0.10 * adapter.frozen_parameters()   # ≪ frozen
    assert adapter.report()["replaced_modules"] == 4 * n_attention_blocks(cfg)


@requires_torch
def test_ceid_and_drift_loss_forward():
    import torch
    from needle.finetune.losses.ceid_loss import CEIDLoss
    from needle.finetune.losses.drift_loss import DriftLoss
    pred = torch.rand(5, 4)
    tgt = torch.rand(5, 4)
    conf = torch.rand(5)
    ceid_loss = CEIDLoss()(pred, tgt, conf)
    assert ceid_loss.shape == () and float(ceid_loss) >= 0.0
    drift_loss = DriftLoss()(torch.randn(5), torch.randint(0, 2, (5,)).float(), conf)
    assert drift_loss.shape == () and float(drift_loss) >= 0.0


@requires_torch
def test_voice_loss_returns_loss_and_perplexity():
    import torch
    from needle.finetune.losses.voice_loss import VoiceLoss
    out = VoiceLoss()(torch.randn(2, 6, 32), torch.randint(0, 32, (2, 6)))
    assert "loss" in out and "perplexity" in out
    assert out["loss"].shape == () and out["perplexity"] > 0.0


@requires_torch
def test_trainer_one_step_smoke(tmp_path):
    from needle import PersonaNeedle
    from needle.finetune.trainer import PersonaNeedleTrainer

    def _write(name, rows):
        (tmp_path / name).write_text("\n".join(json.dumps(r) for r in rows))

    ceid = [{"persona_id": "p", "conversation": "hello world", "k_layer_vector": [0.1] * 100,
             "ceid_labels": {"C": 0.5, "E": 0.5, "I": 0.5, "D": 0.5, "composite": 0.5},
             "confidence": 0.9} for _ in range(2)]
    _write("train.jsonl", ceid)
    _write("val.jsonl", ceid[:1])
    _write("drift_dataset.jsonl", [{"persona_id": "p", "conversation_after": "x", "drift": True}])
    _write("voice_dataset.jsonl", [{"persona_id": "p", "prompt": "hi", "voice": "I am a persona"}])

    pn = PersonaNeedle(_tiny_cfg())
    trainer = PersonaNeedleTrainer(pn, lora_config=LoRAConfig(), epochs=1, batch_size=2,
                                   gradient_accumulation=1, device="cpu",
                                   checkpoint_dir=str(tmp_path / "ckpt"))
    stats = trainer.train(str(tmp_path / "train.jsonl"), str(tmp_path / "val.jsonl"))
    assert stats["history"] and "val_loss" in stats["history"][0]
    assert set(stats["losses_used"]) == {"ceid", "drift", "voice"}
    ev = trainer.evaluate(str(tmp_path / "val.jsonl"))
    assert ev["untrained"] is False and pn.untrained is False


@requires_torch
def test_int4_quantizer_real_compression():
    from needle.architecture.san import SAN
    from needle.finetune.quantize.int4 import INT4Quantizer
    qm = INT4Quantizer().quantize(SAN(_tiny_cfg()))
    assert qm.report["int4_mb"] < qm.report["fp32_mb"] * 0.4   # genuine 4-bit compression
    assert qm.report["n_int4_params"] > 0


@requires_torch
def test_gguf_write_read_roundtrip(tmp_path):
    pytest.importorskip("gguf")
    import gguf
    from needle.architecture.san import SAN
    from needle.finetune.quantize.int4 import INT4Quantizer
    from needle.finetune.quantize.gguf_writer import GGUFWriter
    cfg = _tiny_cfg()
    qm = INT4Quantizer().quantize(SAN(cfg))
    path = tmp_path / "p.gguf"
    report = GGUFWriter().write(qm, cfg, str(path), persona_id="p")
    assert path.exists() and report["size_mb"] > 0 and len(report["sha256"]) == 64
    reader = gguf.GGUFReader(str(path))
    assert any("persona_id" in f for f in reader.fields)      # metadata round-tripped
