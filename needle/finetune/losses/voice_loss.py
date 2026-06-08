"""
Voice training loss (requires torch).

Next-token cross-entropy with teacher forcing and label smoothing (0.1); also reports
perplexity (``exp(loss)``) as the readable generation-quality metric.
"""

from __future__ import annotations

import torch
import torch.nn as nn


class VoiceLoss(nn.Module):
    def __init__(self, label_smoothing: float = 0.1, ignore_index: int = -100):
        super().__init__()
        self.ce = nn.CrossEntropyLoss(label_smoothing=label_smoothing, ignore_index=ignore_index)

    def forward(self, logits, targets) -> dict:
        """``logits``: (B, T, V); ``targets``: (B, T). Returns {"loss", "perplexity"}."""
        b, t, v = logits.shape
        loss = self.ce(logits.reshape(b * t, v), targets.reshape(b * t))
        return {"loss": loss, "perplexity": float(torch.exp(loss.detach()))}
