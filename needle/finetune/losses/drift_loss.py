"""
Drift training loss (requires torch).

Binary cross-entropy on the drift logit with ``pos_weight=2.0`` — drift detection should be
biased against false negatives (missing a real identity drift is worse than a false alarm).
Confidence-weighted like the CEID loss.
"""

from __future__ import annotations

import torch
import torch.nn as nn
import torch.nn.functional as F


class DriftLoss(nn.Module):
    def __init__(self, pos_weight: float = 2.0, eps: float = 1e-6):
        super().__init__()
        self.eps = eps
        self.register_buffer("pos_weight", torch.tensor(float(pos_weight)))

    def forward(self, predictions, targets, confidence=None):
        """``predictions``: (B,) or (B,1) logits; ``targets``: (B,) or (B,1) in {0,1}."""
        pred = predictions.reshape(-1)
        tgt = targets.reshape(-1).to(pred.dtype)
        per = F.binary_cross_entropy_with_logits(
            pred, tgt, pos_weight=self.pos_weight.to(pred.dtype), reduction="none")
        if confidence is not None:
            c = confidence.reshape(-1).to(per.dtype)
            return (per * c).sum() / c.sum().clamp(min=self.eps)
        return per.mean()
