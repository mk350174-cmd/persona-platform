"""
INT4 post-training quantization (requires torch).

Group-wise asymmetric 4-bit weight quantization of the SAN's Linear layers; embeddings and
LayerNorms are kept in FP16 (small, precision-sensitive). Builds a ``QuantizedModel``
container plus an honest size report (reusing the torch-free estimators in
``needle/architecture/config.py``) and a quality check against the FP32 model.

Not run in this repo environment (no torch). The group-wise math mirrors
``needle/architecture/quantizer.quantize_int4`` (symmetric) with an added zero-point.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from needle.architecture.config import (
    PersonaNeedleConfig, estimate_int4_size_mb, estimate_fp32_size_mb,
)
from .validator import QuantizationValidator

# layers kept in FP16 rather than INT4 (matched by substring of the parameter name)
_KEEP_FP16 = ("token_embed", "norm", "_norm")


@dataclass
class QuantizedModel:
    packed: dict = field(default_factory=dict)        # name -> (q_uint8, scale, zero_point)
    fp16_keep: dict = field(default_factory=dict)     # name -> half tensor
    config: Optional[PersonaNeedleConfig] = None
    report: dict = field(default_factory=dict)


class INT4Quantizer:
    def __init__(self, group_size: int = 128, scheme: str = "asymmetric"):
        if scheme not in ("asymmetric", "symmetric"):
            raise ValueError("scheme must be 'asymmetric' or 'symmetric'")
        self.group_size = group_size
        self.scheme = scheme

    def quantize(self, model, calibration_data: Optional[list] = None) -> QuantizedModel:
        """Quantize a SAN (or PersonaNeedle wrapper). ~100 calibration samples suffice for
        activation ranges; weight-only quant here does not strictly require them."""
        import torch
        import torch.nn as nn
        san = getattr(model, "model", model)
        cfg = getattr(san, "cfg", None)
        qm = QuantizedModel(config=cfg)
        n_int4 = n_fp16 = 0

        for name, mod in san.named_modules():
            if isinstance(mod, nn.Linear):
                w = mod.weight.data
                out_f, in_f = w.shape
                g = self.group_size if in_f % self.group_size == 0 else in_f
                wv = w.view(out_f, in_f // g, g)
                wmax = wv.amax(dim=-1, keepdim=True)
                wmin = wv.amin(dim=-1, keepdim=True)
                if self.scheme == "asymmetric":
                    scale = ((wmax - wmin) / 15.0).clamp(min=1e-8)
                    zero = torch.round(-wmin / scale)
                    q = torch.clamp(torch.round(wv / scale) + zero, 0, 15).to(torch.uint8)
                else:
                    scale = (wv.abs().amax(dim=-1, keepdim=True) / 7.0).clamp(min=1e-8)
                    zero = torch.zeros_like(scale)
                    q = torch.clamp(torch.round(wv / scale), -7, 7).to(torch.int8)
                qm.packed[name] = (q, scale.squeeze(-1), zero.squeeze(-1))
                n_int4 += w.numel()

        for pname, p in san.named_parameters():
            if any(k in pname for k in _KEEP_FP16):
                qm.fp16_keep[pname] = p.data.half()
                n_fp16 += p.numel()

        int4_mb = estimate_int4_size_mb(n_int4) + n_fp16 * 2 / 1e6
        fp32_mb = estimate_fp32_size_mb(n_int4 + n_fp16)
        qm.report = {
            "scheme": self.scheme, "group_size": self.group_size,
            "n_int4_params": int(n_int4), "n_fp16_params": int(n_fp16),
            "fp32_mb": round(fp32_mb, 2), "int4_mb": round(int4_mb, 2),
            "compression_ratio": round(int4_mb / fp32_mb, 4) if fp32_mb else None,
        }
        return qm

    def validate_accuracy(self, original, quantized: QuantizedModel, test_data: list) -> dict:
        """CEID MAE Δ < 0.05 and drift-accuracy Δ < 2% vs the FP32 model, else warn."""
        return QuantizationValidator().validate(original, quantized, test_data)


def main(argv=None) -> int:
    import argparse
    ap = argparse.ArgumentParser(description="INT4-quantize a PersonaNeedle checkpoint")
    ap.add_argument("--model", required=True, help="checkpoint dir (config.json + weights)")
    ap.add_argument("--output", required=True)
    ap.add_argument("--group-size", type=int, default=128)
    ap.add_argument("--scheme", default="asymmetric")
    ap.add_argument("--calibration", default=None, help="optional calibration JSONL (~100 samples)")
    args = ap.parse_args(argv)

    import json
    import torch
    from pathlib import Path
    from needle import PersonaNeedle
    cfg_dict = json.loads((Path(args.model) / "config.json").read_text())
    cfg = PersonaNeedleConfig(**cfg_dict)
    pn = PersonaNeedle(cfg).load_checkpoint(str(Path(args.model) / "pytorch_model.bin"))
    qm = INT4Quantizer(args.group_size, args.scheme).quantize(pn)
    out = Path(args.output)
    out.mkdir(parents=True, exist_ok=True)
    torch.save({"packed": qm.packed, "fp16_keep": qm.fp16_keep}, out / "quantized.pt")
    (out / "size_report.json").write_text(json.dumps(qm.report, indent=2))
    (out / "config.json").write_text(json.dumps(cfg_dict, indent=2))   # so gguf_writer finds it
    print(json.dumps(qm.report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
