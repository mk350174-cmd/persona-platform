"""
SAN — Simple Attention Network for persona evaluation.

Adapts the (Cactus) Needle idea — attention-only layers, no feed-forward blocks —
to a small encoder/decoder for persona scoring + voice. ~26M parameters:

* token embedding (8192 × 512), persona-vector projection (100 → 512) prepended as a
  persona-prefix token;
* 12 **attention-only** encoder layers (RoPE + grouped-query attention, NO FFN);
* 8 decoder layers (masked self-attention + cross-attention to the encoder memory);
* three heads — ceid (4-dim, sigmoid), drift (2 logits), voice (tied to the embedding).

Requires PyTorch (see ``needle/requirements.txt``). Untrained until distilled
(``needle/architecture/distillation.py``). The analytic parameter/size budget lives,
torch-free, in ``config.py`` and is kept in sync with this module.
"""

from __future__ import annotations

import torch
import torch.nn as nn
import torch.nn.functional as F

from .config import PersonaNeedleConfig


# ── Rotary positional embedding (RoPE) ───────────────────────────────────────────

def _rope_freqs(seq_len: int, head_dim: int, device, dtype, base: float = 10000.0):
    inv_freq = 1.0 / (base ** (torch.arange(0, head_dim, 2, device=device).float() / head_dim))
    t = torch.arange(seq_len, device=device).float()
    freqs = torch.outer(t, inv_freq)                       # (T, head_dim/2)
    emb = torch.cat((freqs, freqs), dim=-1)                # (T, head_dim)
    return emb.cos().to(dtype), emb.sin().to(dtype)


def _rotate_half(x):
    x1, x2 = x.chunk(2, dim=-1)
    return torch.cat((-x2, x1), dim=-1)


def _apply_rope(x, cos, sin):
    # x: (B, n_heads, T, head_dim); cos/sin: (T, head_dim)
    cos = cos[None, None, :, :]
    sin = sin[None, None, :, :]
    return x * cos + _rotate_half(x) * sin


# ── Grouped-query attention (bias-free; matches config estimator) ────────────────

class GQAttention(nn.Module):
    def __init__(self, cfg: PersonaNeedleConfig):
        super().__init__()
        self.h = cfg.hidden_dim
        self.n_heads = cfg.num_heads
        self.kv_heads = cfg.kv_heads
        self.head_dim = cfg.head_dim
        self.n_rep = cfg.num_heads // cfg.kv_heads
        self.q_proj = nn.Linear(self.h, self.n_heads * self.head_dim, bias=False)
        self.k_proj = nn.Linear(self.h, self.kv_heads * self.head_dim, bias=False)
        self.v_proj = nn.Linear(self.h, self.kv_heads * self.head_dim, bias=False)
        self.o_proj = nn.Linear(self.n_heads * self.head_dim, self.h, bias=False)

    def forward(self, x, kv=None, causal=False, rope=True):
        kv = x if kv is None else kv
        B, Tq, _ = x.shape
        Tk = kv.shape[1]
        q = self.q_proj(x).view(B, Tq, self.n_heads, self.head_dim).transpose(1, 2)
        k = self.k_proj(kv).view(B, Tk, self.kv_heads, self.head_dim).transpose(1, 2)
        v = self.v_proj(kv).view(B, Tk, self.kv_heads, self.head_dim).transpose(1, 2)
        if rope:
            cos_q, sin_q = _rope_freqs(Tq, self.head_dim, x.device, x.dtype)
            cos_k, sin_k = _rope_freqs(Tk, self.head_dim, x.device, x.dtype)
            q = _apply_rope(q, cos_q, sin_q)
            k = _apply_rope(k, cos_k, sin_k)
        # expand KV heads to query heads (GQA)
        k = k.repeat_interleave(self.n_rep, dim=1)
        v = v.repeat_interleave(self.n_rep, dim=1)
        out = F.scaled_dot_product_attention(q, k, v, is_causal=causal)
        out = out.transpose(1, 2).contiguous().view(B, Tq, self.n_heads * self.head_dim)
        return self.o_proj(out)


class EncoderLayer(nn.Module):
    """Attention-only (NO FFN) — the defining SAN/Needle choice."""

    def __init__(self, cfg: PersonaNeedleConfig):
        super().__init__()
        self.norm = nn.LayerNorm(cfg.hidden_dim)
        self.attn = GQAttention(cfg)

    def forward(self, x):
        return x + self.attn(self.norm(x), causal=False)


class DecoderLayer(nn.Module):
    """Masked self-attention + cross-attention to encoder memory (no FFN)."""

    def __init__(self, cfg: PersonaNeedleConfig):
        super().__init__()
        self.norm_self = nn.LayerNorm(cfg.hidden_dim)
        self.self_attn = GQAttention(cfg)
        self.norm_cross = nn.LayerNorm(cfg.hidden_dim)
        self.cross_attn = GQAttention(cfg)

    def forward(self, x, memory):
        x = x + self.self_attn(self.norm_self(x), causal=True)
        x = x + self.cross_attn(self.norm_cross(x), kv=memory, causal=False, rope=False)
        return x


class SAN(nn.Module):
    def __init__(self, cfg: PersonaNeedleConfig):
        super().__init__()
        self.cfg = cfg
        self.token_embed = nn.Embedding(cfg.vocab_size, cfg.hidden_dim)
        self.persona_proj = nn.Linear(cfg.k_layer_dim, cfg.hidden_dim, bias=False)
        self.encoder = nn.ModuleList(EncoderLayer(cfg) for _ in range(cfg.encoder_layers))
        self.decoder = nn.ModuleList(DecoderLayer(cfg) for _ in range(cfg.decoder_layers))
        self.enc_norm = nn.LayerNorm(cfg.hidden_dim)
        self.dec_norm = nn.LayerNorm(cfg.hidden_dim)
        self.ceid_head = nn.Linear(cfg.hidden_dim, 4)      # C/E/I/D, sigmoid → [0,1]
        self.drift_head = nn.Linear(cfg.hidden_dim, 2)     # binary logits
        # voice_head is tied to the token embedding (saves vocab×hidden params → ~26M)
        self.tie_voice_head = cfg.tie_voice_head
        if not cfg.tie_voice_head:
            self.voice_head = nn.Linear(cfg.hidden_dim, cfg.vocab_size, bias=False)

    def encode(self, persona_vector, input_ids):
        tok = self.token_embed(input_ids)                              # (B, T, H)
        persona = self.persona_proj(persona_vector).unsqueeze(1)       # (B, 1, H)
        x = torch.cat([persona, tok], dim=1)                           # persona-prefix
        for layer in self.encoder:
            x = layer(x)
        return self.enc_norm(x)

    def _voice_logits(self, h):
        if self.tie_voice_head:
            return F.linear(h, self.token_embed.weight)                # tied
        return self.voice_head(h)

    def forward(self, persona_vector, input_ids, decoder_input_ids=None):
        memory = self.encode(persona_vector, input_ids)               # (B, 1+T, H)
        pooled = memory[:, 0]                                          # persona-prefix token
        out = {
            "ceid": torch.sigmoid(self.ceid_head(pooled)),            # (B, 4) in [0,1]
            "drift_logits": self.drift_head(pooled),                  # (B, 2)
            "memory": memory,
        }
        if decoder_input_ids is not None:
            d = self.token_embed(decoder_input_ids)
            for layer in self.decoder:
                d = layer(d, memory)
            out["voice_logits"] = self._voice_logits(self.dec_norm(d))  # (B, Td, vocab)
        return out

    def num_parameters(self) -> int:
        return sum(p.numel() for p in self.parameters())
