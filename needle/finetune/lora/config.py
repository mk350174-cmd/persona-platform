"""
LoRA configuration + a torch-free analytic estimator for the trainable-parameter count.

Pure Python (no torch import) so the LoRA budget can be computed and tested in any
environment — including this one, where torch is not installed. The estimate is kept in
sync with ``adapter.LoRAAdapter`` (the torch-guarded test asserts they agree exactly).
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import List

from needle.architecture.config import PersonaNeedleConfig

# attention projections LoRA may target (SAN is attention-only — no FFN)
_ATTN_MODULES = ("q_proj", "k_proj", "v_proj", "o_proj")
_VALID_BIAS = ("none", "all", "lora_only")


def _default_target_modules() -> List[str]:
    return list(_ATTN_MODULES)


@dataclass
class LoRAConfig:
    """Low-Rank Adaptation config. Defaults match the spec (attention-only fine-tune)."""

    r: int = 8                       # LoRA rank
    alpha: int = 16                  # LoRA alpha (scale = alpha / r)
    dropout: float = 0.1
    target_modules: List[str] = field(default_factory=_default_target_modules)
    bias: str = "none"               # none | all | lora_only
    task_type: str = "PERSONA_EVAL"

    def __post_init__(self):
        if self.r <= 0:
            raise ValueError("LoRA rank r must be positive")
        if self.alpha <= 0:
            raise ValueError("LoRA alpha must be positive")
        if not (0.0 <= self.dropout < 1.0):
            raise ValueError("dropout must be in [0, 1)")
        if not self.target_modules:
            raise ValueError("target_modules must not be empty")
        unknown = [m for m in self.target_modules if m not in _ATTN_MODULES]
        if unknown:
            raise ValueError(f"unknown target_modules {unknown}; SAN exposes {list(_ATTN_MODULES)}")
        if self.bias not in _VALID_BIAS:
            raise ValueError(f"bias must be one of {_VALID_BIAS}")

    @property
    def scale(self) -> float:
        return self.alpha / self.r

    def to_dict(self) -> dict:
        return asdict(self)


# ── torch-free analytic estimator (kept in sync with adapter.LoRAAdapter) ─────────

def _module_io(cfg: PersonaNeedleConfig, name: str):
    """(in_features, out_features) of a SAN attention projection, matching ``san.GQAttention``."""
    h = cfg.hidden_dim
    q_out = cfg.num_heads * cfg.head_dim     # = hidden_dim
    kv_out = cfg.kv_heads * cfg.head_dim     # grouped-query KV width
    return {
        "q_proj": (h, q_out),
        "k_proj": (h, kv_out),
        "v_proj": (h, kv_out),
        "o_proj": (q_out, h),
    }.get(name)


def n_attention_blocks(cfg: PersonaNeedleConfig) -> int:
    """Encoder has 1 attention block/layer; each decoder layer has self- + cross-attention."""
    return cfg.encoder_layers + 2 * cfg.decoder_layers


def estimate_lora_trainable_params(cfg: PersonaNeedleConfig, lora_cfg: LoRAConfig) -> int:
    """Trainable LoRA parameters: Σ_blocks Σ_targets r·(in + out).

    For the default config (r=8, all four attention projections, 12 enc + 8×2 dec = 28
    attention blocks) this is ≈ 0.80M — about 3% of the ~26M frozen backbone.
    """
    per_block = 0
    for name in lora_cfg.target_modules:
        io = _module_io(cfg, name)
        if io is None:
            continue
        in_f, out_f = io
        per_block += lora_cfg.r * (in_f + out_f)
    return n_attention_blocks(cfg) * per_block
