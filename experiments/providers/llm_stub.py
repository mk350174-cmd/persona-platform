"""
LLMProvider — the real-LLM plug-in point (NOT executed in this environment).

This environment has no LLM API keys and no outbound egress, so real GPT-4 /
Claude / Llama runs cannot happen here. This class documents exactly how a real
backend slots into the same pipeline the simulated provider uses: every
``exp_m*`` module accepts a ``SeriesProvider``, so swapping ``SimulatedProvider``
for a fully-implemented ``LLMProvider`` changes the *data source* only — all
downstream math (D1, CEID, atlas, …) is identical.

Intended real implementation (when keys + egress exist):

1. ``build_series(persona_id, ...)``: load the compiled system prompt for the
   persona (``persona_math.compiler``), run an N-turn conversation (optionally
   with an adversarial prompt schedule for the ``adversarial`` conditions),
   collect each assistant turn's text, and ``embed`` it to a (100,) K-layer
   vector. The resulting ``ResponseSeries`` carries tier-relevant provenance:
   numbers built from it would be **Ölçülmüş** (real measured) — produced by the
   caller running THIS class, never by ``SimulatedProvider``.
2. ``embed(text)``: project model output into the 100-dim K-layer space (e.g. a
   trained linear probe over sentence embeddings).
"""

from __future__ import annotations

import os

import numpy as np

from .base import ResponseSeries, SeriesProvider

_API_ENV_VARS = ("OPENAI_API_KEY", "ANTHROPIC_API_KEY")


class LLMProvider(SeriesProvider):
    """Real-LLM backend stub. Raises ``NotImplementedError`` until wired up."""

    name = "llm"

    def __init__(self, model: str | None = None, embed_model: str | None = None):
        self.model = model or os.environ.get("PERSONA_LLM_MODEL", "gpt-4o")
        self.embed_model = embed_model or os.environ.get(
            "PERSONA_EMBED_MODEL", "text-embedding-3-large"
        )
        self.api_keys_present = any(os.environ.get(v) for v in _API_ENV_VARS)

    def _unavailable(self) -> NotImplementedError:
        return NotImplementedError(
            "LLMProvider is a plug-in stub: real-LLM runs are not performed in "
            "this environment (no API keys / no egress). Implement build_series/"
            "embed and run where OPENAI_API_KEY/ANTHROPIC_API_KEY and network "
            "access are available. See module docstring. "
            f"(api_keys_present={self.api_keys_present})"
        )

    def build_series(
        self,
        persona_id: str,
        *,
        n_turns: int = 10,
        condition: str = "control",
        seed: int = 0,
    ) -> ResponseSeries:
        raise self._unavailable()

    def embed(self, text: str) -> np.ndarray:
        raise self._unavailable()
