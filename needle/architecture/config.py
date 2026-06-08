"""
PersonaNeedle configuration + torch-free size/parameter estimators.

This module is intentionally **pure Python** (no torch import) so that the
parameter-count and INT4-size estimates can be computed and tested in any
environment — including this one, where torch is not installed.
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Dict, Optional

# K-layer (HPEP-100) persona vectors are 100-dimensional (persona_math).
K_LAYER_DIM = 100


def _default_ceid_weights() -> Dict[str, float]:
    return {"C": 0.25, "E": 0.25, "I": 0.25, "D": 0.25}


@dataclass
class PersonaNeedleConfig:
    """One config per persona. Architecture defaults match the ~26M SAN spec."""

    persona_id: str = "generic"
    k_layer_path: Optional[str] = None          # path to a saved K-layer vector (optional)
    hidden_dim: int = 512
    encoder_layers: int = 12                     # attention-only (NO FFN)
    decoder_layers: int = 8                      # masked self-attn + cross-attn
    num_heads: int = 8
    kv_heads: int = 4                            # grouped-query attention
    vocab_size: int = 8192                       # persona-specific BPE
    max_context: int = 2048
    k_layer_dim: int = K_LAYER_DIM
    quantization: str = "INT4"                   # post-training; ≈13MB at ~26M params
    tie_voice_head: bool = True                  # voice_head shares the token embedding
    ceid_weights: Dict[str, float] = field(default_factory=_default_ceid_weights)

    def __post_init__(self):
        if self.hidden_dim % self.num_heads != 0:
            raise ValueError("hidden_dim must be divisible by num_heads")
        if self.num_heads % self.kv_heads != 0:
            raise ValueError("num_heads must be divisible by kv_heads (GQA)")

    @property
    def head_dim(self) -> int:
        return self.hidden_dim // self.num_heads

    @property
    def kv_dim(self) -> int:
        return self.kv_heads * self.head_dim

    def to_dict(self) -> dict:
        return asdict(self)


# ── torch-free analytic estimators (kept in sync with san.py) ────────────────────

def _attn_params(cfg: PersonaNeedleConfig) -> int:
    """Q/K/V/O projection weights for one (G)QA attention block (bias-free)."""
    h, kv = cfg.hidden_dim, cfg.kv_dim
    return h * h + h * kv + h * kv + h * h        # q + k + v + o


def _norm_params(cfg: PersonaNeedleConfig, n: int) -> int:
    return n * 2 * cfg.hidden_dim                  # LayerNorm weight+bias


def estimate_param_count(cfg: PersonaNeedleConfig) -> int:
    """Analytic parameter count matching ``san.SAN`` (voice_head tied to embedding)."""
    h = cfg.hidden_dim
    embed = cfg.vocab_size * h
    persona_proj = cfg.k_layer_dim * h
    # encoder: attention-only, 1 norm/layer
    enc = cfg.encoder_layers * (_attn_params(cfg) + _norm_params(cfg, 1))
    # decoder: self-attn + cross-attn, 2 norms/layer
    dec = cfg.decoder_layers * (2 * _attn_params(cfg) + _norm_params(cfg, 2))
    final_norms = _norm_params(cfg, 2)             # encoder + decoder final norm
    ceid_head = h * 4 + 4
    drift_head = h * 2 + 2
    voice_head = 0 if cfg.tie_voice_head else cfg.vocab_size * h
    return embed + persona_proj + enc + dec + final_norms + ceid_head + drift_head + voice_head


def estimate_int4_size_mb(cfg_or_n) -> float:
    """INT4 (4-bit ⇒ 0.5 byte/param) size estimate in MB (decimal)."""
    n = cfg_or_n if isinstance(cfg_or_n, int) else estimate_param_count(cfg_or_n)
    return n * 0.5 / 1e6


def estimate_fp32_size_mb(cfg_or_n) -> float:
    n = cfg_or_n if isinstance(cfg_or_n, int) else estimate_param_count(cfg_or_n)
    return n * 4 / 1e6
