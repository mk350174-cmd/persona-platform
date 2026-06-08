"""
GGUF export for the quantized PersonaNeedle (requires the ``gguf`` package; torch for tensors).

Writes a llama.cpp-style GGUF container: header + persona metadata
(persona_id, k_layer_hash, ceid_baseline, version) + the INT4 weight blocks (with their
per-group scales / zero-points) + the FP16-kept tensors, then verifies a checksum and
reports the file size.

NOTE: llama.cpp does not ship a 'SAN' architecture, so on-device inference needs a custom
op set or a conversion to a supported arch — documented future work (see
``needle/architecture/quantizer.export_gguf``). Not run here (no torch / no gguf).
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Optional

from needle.architecture.config import PersonaNeedleConfig


def _sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _k_layer_hash(persona_id: str) -> str:
    try:
        import numpy as np
        from persona_math.persona_library import get_library_persona
        v = np.asarray(get_library_persona(persona_id), dtype=np.float32)
        return hashlib.sha256(v.tobytes()).hexdigest()[:16]
    except Exception:
        return "unknown"


class GGUFWriter:
    VERSION = "1.0"

    def write(self, quantized_model, config: PersonaNeedleConfig, output_path: str,
              persona_id: Optional[str] = None, ceid_baseline: Optional[dict] = None) -> dict:
        import gguf

        persona_id = persona_id or getattr(config, "persona_id", "generic")
        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)

        writer = gguf.GGUFWriter(str(out), arch="persona-needle-san")
        # architecture
        writer.add_uint32("hidden_dim", config.hidden_dim)
        writer.add_uint32("encoder_layers", config.encoder_layers)
        writer.add_uint32("decoder_layers", config.decoder_layers)
        writer.add_uint32("num_heads", config.num_heads)
        writer.add_uint32("kv_heads", config.kv_heads)
        writer.add_uint32("vocab_size", config.vocab_size)
        writer.add_string("quantization", "INT4")
        # persona metadata
        writer.add_string("persona_id", persona_id)
        writer.add_string("k_layer_hash", _k_layer_hash(persona_id))
        writer.add_string("version", self.VERSION)
        if ceid_baseline:
            writer.add_string("ceid_baseline", str(ceid_baseline))

        # INT4 weight blocks (+ scales / zero-points) and FP16-kept tensors
        for name, (q, scale, zero) in getattr(quantized_model, "packed", {}).items():
            writer.add_tensor(f"{name}.weight_int4", q.cpu().numpy())
            writer.add_tensor(f"{name}.scale", scale.cpu().float().numpy())
            writer.add_tensor(f"{name}.zero", zero.cpu().float().numpy())
        for name, t in getattr(quantized_model, "fp16_keep", {}).items():
            writer.add_tensor(name, t.cpu().float().numpy())

        writer.write_header_to_file()
        writer.write_kv_data_to_file()
        writer.write_tensors_to_file()
        writer.close()

        size_mb = out.stat().st_size / 1e6
        return {"path": str(out), "persona_id": persona_id, "version": self.VERSION,
                "size_mb": round(size_mb, 2), "sha256": _sha256(str(out))}


def main(argv=None) -> int:
    import argparse
    import json
    import torch
    ap = argparse.ArgumentParser(description="Write a GGUF for a quantized PersonaNeedle")
    ap.add_argument("--quantized", required=True, help="dir with quantized.pt + size_report.json")
    ap.add_argument("--config", default=None,
                    help="config.json (default: <quantized>/config.json, written by int4)")
    ap.add_argument("--persona-id", default=None)
    ap.add_argument("--output", default=None)
    args = ap.parse_args(argv)

    from .int4 import QuantizedModel
    config_path = Path(args.config) if args.config else Path(args.quantized) / "config.json"
    cfg = PersonaNeedleConfig(**json.loads(config_path.read_text()))
    blob = torch.load(Path(args.quantized) / "quantized.pt")
    qm = QuantizedModel(packed=blob["packed"], fp16_keep=blob["fp16_keep"], config=cfg)
    pid = args.persona_id or cfg.persona_id
    output = args.output or f"needle/finetune/export/output/{pid}.gguf"
    report = GGUFWriter().write(qm, cfg, output, persona_id=pid)
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
