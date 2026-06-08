"""
LoRA adapter layers for PersonaNeedle (requires torch).

``LoRALinear`` wraps a frozen ``nn.Linear`` with a trainable low-rank update
``W = W0 + (B @ A) · (alpha / r)`` (B is zero-initialised, so the adapter is an identity
at the start of training). ``LoRAAdapter`` swaps the SAN's attention projections
(``q/k/v/o_proj``) for ``LoRALinear``, freezes everything else, and can ``merge_and_unload``
the learned deltas back into plain Linears so the result is a normal SAN ready for
quantization.

Self-contained (no hard ``peft`` dependency); ``peft`` is listed in requirements as the
drop-in alternative. Not exercised in this repo environment (no torch).
"""

from __future__ import annotations

import math

import torch
import torch.nn as nn

from .config import LoRAConfig


class LoRALinear(nn.Module):
    """Frozen base ``nn.Linear`` + trainable rank-``r`` update."""

    def __init__(self, base: nn.Linear, r: int, alpha: int, dropout: float = 0.0):
        super().__init__()
        self.base = base
        for p in self.base.parameters():
            p.requires_grad = False
        self.r = r
        self.scale = alpha / r
        self.dropout = nn.Dropout(dropout) if dropout > 0 else nn.Identity()
        in_f, out_f = base.in_features, base.out_features
        self.lora_A = nn.Parameter(torch.zeros(r, in_f))
        self.lora_B = nn.Parameter(torch.zeros(out_f, r))
        nn.init.kaiming_uniform_(self.lora_A, a=math.sqrt(5))   # B stays 0 → identity at init

    def forward(self, x):
        update = (self.dropout(x) @ self.lora_A.t()) @ self.lora_B.t()
        return self.base(x) + update * self.scale

    def merged_weight(self) -> torch.Tensor:
        """W0 + (B @ A)·scale — the effective full-rank weight."""
        return self.base.weight.data + (self.lora_B @ self.lora_A) * self.scale


class LoRAAdapter:
    """Apply / report / merge LoRA on a ``PersonaNeedle`` wrapper or a raw ``SAN``."""

    def __init__(self, model, config: LoRAConfig):
        self.model = model
        self.config = config
        self.replaced = 0
        self._applied = False

    def _san(self) -> nn.Module:
        # accept either a PersonaNeedle wrapper (.model) or a bare SAN
        return getattr(self.model, "model", self.model)

    def apply(self):
        """Replace target Linears with LoRALinear and freeze the backbone. Returns ``model``."""
        san = self._san()
        targets = set(self.config.target_modules)
        for module in list(san.modules()):
            for child_name, child in list(module.named_children()):
                if child_name in targets and isinstance(child, nn.Linear):
                    setattr(module, child_name,
                            LoRALinear(child, self.config.r, self.config.alpha, self.config.dropout))
                    self.replaced += 1
        for name, p in san.named_parameters():
            train = name.endswith("lora_A") or name.endswith("lora_B")
            if self.config.bias == "all" and name.endswith(".bias"):
                train = True
            p.requires_grad = train
        self._applied = True
        return self.model

    def trainable_parameters(self) -> int:
        return sum(p.numel() for p in self._san().parameters() if p.requires_grad)

    def frozen_parameters(self) -> int:
        return sum(p.numel() for p in self._san().parameters() if not p.requires_grad)

    def report(self) -> dict:
        t, f = self.trainable_parameters(), self.frozen_parameters()
        total = t + f
        return {
            "replaced_modules": self.replaced,
            "trainable": t,
            "frozen": f,
            "total": total,
            "trainable_pct": round(100.0 * t / total, 3) if total else 0.0,
        }

    def merge_and_unload(self):
        """Fold each LoRALinear's delta into a plain ``nn.Linear`` and unfreeze. Returns ``model``."""
        san = self._san()
        for module in list(san.modules()):
            for child_name, child in list(module.named_children()):
                if isinstance(child, LoRALinear):
                    base = child.base
                    merged = nn.Linear(base.in_features, base.out_features, bias=base.bias is not None)
                    merged.weight.data = child.merged_weight()
                    if base.bias is not None:
                        merged.bias.data = base.bias.data
                    setattr(module, child_name, merged)
        for p in san.parameters():
            p.requires_grad = True
        self._applied = False
        return self.model
