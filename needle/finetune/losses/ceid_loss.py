"""
CEID training loss (requires torch).

The hybrid-teacher soft labels (4 sigmoid axes C/E/I/D in [0,1]) are distilled into the
SAN's ``ceid_head`` with a confidence-weighted, axis-weighted **Bernoulli KL divergence**.
I and D carry higher axis weight (1.5 / 2.0) — individuation and ``sarsılmazlık`` are the
behaviourally critical axes — and low-confidence samples contribute proportionally less.
"""

from __future__ import annotations

import torch
import torch.nn as nn

# axis order matches SAN ceid_head output: (C, E, I, D)
_DEFAULT_AXIS_WEIGHTS = {"C": 1.0, "E": 1.0, "I": 1.5, "D": 2.0}


class CEIDLoss(nn.Module):
    def __init__(self, axis_weights: dict | None = None, eps: float = 1e-6):
        super().__init__()
        w = axis_weights or _DEFAULT_AXIS_WEIGHTS
        self.eps = eps
        self.register_buffer(
            "axis_weights",
            torch.tensor([w["C"], w["E"], w["I"], w["D"]], dtype=torch.float32),
        )

    def forward(self, predictions, targets, confidence=None):
        """``predictions``/``targets``: (B, 4) in [0,1]; ``confidence``: (B,) in [0,1] or None."""
        p = predictions.clamp(self.eps, 1.0 - self.eps)
        t = targets.clamp(self.eps, 1.0 - self.eps)
        # per-axis Bernoulli KL(t || p)
        kl = t * torch.log(t / p) + (1.0 - t) * torch.log((1.0 - t) / (1.0 - p))   # (B, 4)
        w = self.axis_weights.to(kl.dtype)
        per_sample = (kl * w).sum(dim=-1) / w.sum()                                  # (B,)
        if confidence is not None:
            c = confidence.reshape(-1).to(per_sample.dtype)
            return (per_sample * c).sum() / c.sum().clamp(min=self.eps)
        return per_sample.mean()
