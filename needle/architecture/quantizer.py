"""
INT4 quantization + GGUF export (TEMPLATE + honest size estimator).

Targets edge deployment (Android/tablet) via GGUF + llama.cpp / llama.rn. At ~26M
parameters, INT4 (4-bit ⇒ 0.5 byte/param) is **≈13MB** of weights — so the realistic
on-device footprint is the README's **15–20MB total** (model + K-layer + visual + audio),
not 8MB. Functions here:

* ``size_report`` / ``estimate_int4_size_mb`` — honest, torch-free size math;
* ``quantize_int4`` — a functional group-wise 4-bit weight-quant scaffold (needs torch);
* ``export_gguf`` — a metadata/tensor writer scaffold (needs torch + the ``gguf`` lib;
  full on-device inference also needs llama.cpp architecture support).

Nothing is exported in this repo environment (no trained weights, no torch).
"""

from __future__ import annotations

from typing import Optional

from .config import PersonaNeedleConfig, estimate_int4_size_mb, estimate_fp32_size_mb

__all__ = ["size_report", "estimate_int4_size_mb", "quantize_int4", "export_gguf"]


def size_report(cfg_or_model) -> dict:
    """Honest size report. Accepts a config (torch-free) or a torch model."""
    if isinstance(cfg_or_model, PersonaNeedleConfig):
        n = None
        from .config import estimate_param_count
        n = estimate_param_count(cfg_or_model)
    else:
        n = sum(p.numel() for p in cfg_or_model.parameters())
    int4 = estimate_int4_size_mb(n)
    fp32 = estimate_fp32_size_mb(n)
    return {
        "n_params": int(n),
        "fp32_mb": round(fp32, 2),
        "int4_mb": round(int4, 2),
        "compression_ratio": round(int4 / fp32, 4),     # ~0.125
        "note": "INT4 ≈ params×0.5 byte; ~13MB at 26M. Edge total 15–20MB with assets.",
    }


def quantize_int4(model, group_size: int = 64):
    """Group-wise symmetric 4-bit weight quantization of Linear layers (scaffold).

    Returns a dict of packed {name: (q_int4, scales)} for each Linear weight. Real
    deployment would use bitsandbytes / llama.cpp kernels; this demonstrates the math.
    """
    import torch
    import torch.nn as nn
    packed = {}
    for name, mod in model.named_modules():
        if isinstance(mod, nn.Linear):
            w = mod.weight.data
            out_f, in_f = w.shape
            g = group_size if in_f % group_size == 0 else in_f
            wv = w.view(out_f, in_f // g, g)
            scale = wv.abs().amax(dim=-1, keepdim=True).clamp(min=1e-8) / 7.0   # int4: [-7,7]
            q = torch.clamp(torch.round(wv / scale), -7, 7).to(torch.int8)
            packed[name] = (q, scale.squeeze(-1))
    return packed


def export_gguf(model, path: str, cfg: Optional[PersonaNeedleConfig] = None):
    """Write a GGUF file with metadata + (quantized) tensors (scaffold).

    Requires the ``gguf`` package and torch. NOTE: llama.cpp does not ship a 'SAN'
    architecture, so on-device inference needs a custom op set or a conversion to a
    supported arch — documented as future work. This writes a loadable GGUF container
    so the pipeline end-to-end can be exercised where the toolchain exists.
    """
    import gguf  # noqa: F401  (installable; import deferred)
    cfg = cfg or getattr(model, "cfg", None)
    writer = gguf.GGUFWriter(path, arch="persona-needle-san")
    if cfg is not None:
        writer.add_uint32("hidden_dim", cfg.hidden_dim)
        writer.add_uint32("encoder_layers", cfg.encoder_layers)
        writer.add_uint32("decoder_layers", cfg.decoder_layers)
        writer.add_uint32("num_heads", cfg.num_heads)
        writer.add_uint32("kv_heads", cfg.kv_heads)
        writer.add_uint32("vocab_size", cfg.vocab_size)
        writer.add_string("quantization", cfg.quantization)
    for name, p in model.state_dict().items():
        writer.add_tensor(name, p.detach().cpu().numpy())
    writer.write_header_to_file()
    writer.write_kv_data_to_file()
    writer.write_tensors_to_file()
    writer.close()
    return path
