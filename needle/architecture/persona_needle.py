"""
PersonaNeedle — the user-facing wrapper around the SAN model.

Provides ``measure_ceid`` / ``detect_drift`` / ``generate_voice`` / ``full_pipeline``.
The SAN is **untrained** until distilled (``distillation.py``); every output carries an
``untrained`` flag, and ``reference_ceid()`` exposes the existing
``persona_math.ceid.ceid_score`` on the persona's K-layer vector as the labeled
reference / distillation target. The tokenizer here is a documented placeholder; a real
8192-token persona BPE is trained during distillation.
"""

from __future__ import annotations

from typing import Optional

import numpy as np
import torch

from .config import PersonaNeedleConfig
from .san import SAN

_CEID_AXES = ("C", "E", "I", "D")
# map persona_math.ceid axis keys → C/E/I/D
_PM_AXIS_MAP = {
    "C_semantic_resonance": "C",
    "E_epistemic_vigilance": "E",
    "I_tree_convergence": "I",
    "D_sarsılmazlık": "D",
}


class _StubTokenizer:
    """Placeholder byte-level tokenizer (ids in [0, vocab)). Replace with the trained
    persona BPE produced during distillation."""

    def __init__(self, vocab_size: int):
        self.vocab_size = vocab_size
        self.bos, self.eos = 1, 2

    def encode(self, text: str, max_len: Optional[int] = None) -> list[int]:
        ids = [self.bos] + [3 + (b % (self.vocab_size - 4)) for b in text.encode("utf-8")]
        return ids[:max_len] if max_len else ids

    def decode(self, ids) -> str:
        out = bytes((max(0, i - 3) % 256) for i in ids if i not in (self.bos, self.eos))
        return out.decode("utf-8", errors="replace")


def _load_k_layer(cfg: PersonaNeedleConfig) -> np.ndarray:
    """Load the persona's K-layer vector from the library or a saved path; zeros if absent."""
    if cfg.k_layer_path:
        return np.asarray(np.load(cfg.k_layer_path), dtype=np.float32)
    try:
        from persona_math.persona_library import get_library_persona
        v = get_library_persona(cfg.persona_id)
        if v is not None:
            return np.asarray(v, dtype=np.float32)
    except Exception:
        pass
    return np.zeros(cfg.k_layer_dim, dtype=np.float32)


class PersonaNeedle:
    def __init__(self, config: PersonaNeedleConfig, device: str = "cpu",
                 persona_vector: Optional[np.ndarray] = None):
        self.config = config
        self.device = device
        self.model = SAN(config).to(device).eval()
        self.tokenizer = _StubTokenizer(config.vocab_size)
        # an explicit persona_vector (e.g. from persona_mcp) overrides library/file loading
        self.k_layer = (np.asarray(persona_vector, dtype=np.float32)
                        if persona_vector is not None else _load_k_layer(config))
        self.untrained = True  # set False once a distilled checkpoint is loaded

    # ── checkpoint ───────────────────────────────────────────────────────────────
    def load_checkpoint(self, path: str):
        self.model.load_state_dict(torch.load(path, map_location=self.device))
        self.model.eval()
        self.untrained = False
        return self

    def _persona_tensor(self) -> torch.Tensor:
        return torch.tensor(self.k_layer, dtype=torch.float32, device=self.device).unsqueeze(0)

    def _ids(self, text: str) -> torch.Tensor:
        ids = self.tokenizer.encode(text, max_len=self.config.max_context)
        return torch.tensor([ids], dtype=torch.long, device=self.device)

    # ── heads ──────────────────────────────────────────────────────────────────────
    @torch.no_grad()
    def measure_ceid(self, conversation: str) -> dict:
        out = self.model(self._persona_tensor(), self._ids(conversation))
        vals = out["ceid"][0].tolist()
        res = {ax: round(float(v), 4) for ax, v in zip(_CEID_AXES, vals)}
        res["untrained"] = self.untrained
        if self.untrained:
            res["_note"] = "SAN untrained — distill first; see reference_ceid() for the persona_math target"
        return res

    @torch.no_grad()
    def detect_drift(self, conversation: str) -> dict:
        out = self.model(self._persona_tensor(), self._ids(conversation))
        p_drift = float(torch.softmax(out["drift_logits"][0], dim=-1)[1])
        drift = p_drift > 0.5
        return {
            "drift": bool(drift),
            "score": round(p_drift, 4),
            "warning": "identity drift detected" if drift else None,
            "untrained": self.untrained,
        }

    @torch.no_grad()
    def generate_voice(self, prompt: str, max_new_tokens: int = 32) -> str:
        memory = self.model.encode(self._persona_tensor(), self._ids(prompt))
        ids = [self.tokenizer.bos]
        for _ in range(max_new_tokens):
            d = torch.tensor([ids], dtype=torch.long, device=self.device)
            dh = self.model.token_embed(d)
            for layer in self.model.decoder:
                dh = layer(dh, memory)
            logits = self.model._voice_logits(self.model.dec_norm(dh))[0, -1]
            nxt = int(torch.argmax(logits))
            if nxt == self.tokenizer.eos:
                break
            ids.append(nxt)
        text = self.tokenizer.decode(ids)
        return text if not self.untrained else f"[untrained SAN output] {text}"

    def full_pipeline(self, conversation: str, prompt: str, mcp_callback=None) -> dict:
        """Run CEID + drift + voice. If ``mcp_callback`` is given it is invoked as
        ``mcp_callback(persona_id, result)`` (e.g. persona_mcp's NeedleBridge) so the
        result is logged to the persona knowledge-graph."""
        result = {
            "persona_id": self.config.persona_id,
            "ceid": self.measure_ceid(conversation),
            "drift": self.detect_drift(conversation),
            "voice": self.generate_voice(prompt),
            "untrained": self.untrained,
        }
        if mcp_callback is not None:
            mcp_callback(self.config.persona_id, result)
        return result

    # ── reference / distillation target (existing persona_math metric) ──────────────
    def reference_ceid(self) -> dict:
        """The persona_math.ceid score on this persona's K-layer vector — the labeled
        reference the SAN's ceid_head is distilled toward (NOT the SAN's own output)."""
        from persona_math.ceid import ceid_score
        P = self.k_layer
        sc = ceid_score(P, P, weights={k: self.config.ceid_weights.get(k, 0.25)
                                       for k in _CEID_AXES})
        axes = {_PM_AXIS_MAP.get(k, k): round(float(v), 4) for k, v in sc["axes"].items()}
        return {"axes": axes, "composite": round(float(sc["CEID_score"]), 4),
                "source": "persona_math.ceid (reference / distillation target)"}
