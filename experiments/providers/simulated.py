"""SimulatedProvider — deterministic, vector-space data source (the default)."""

from __future__ import annotations

import numpy as np

from persona_math.persona_library import get_library_persona

from ..series_builders import build_series
from .base import ResponseSeries, SeriesProvider


class SimulatedProvider(SeriesProvider):
    """Build persona trajectories from the existing library, deterministically.

    The baseline vector is the real, seed-fixed library vector for the persona;
    the turn-by-turn trajectory is synthesized by :mod:`experiments.series_builders`
    using the framework's own SET-9 collapse direction. No text and no network
    are involved — this is the honest "simulation" data source.
    """

    name = "simulated"

    def __init__(self, sigma: float = 0.02):
        self.sigma = float(sigma)

    def build_series(
        self,
        persona_id: str,
        *,
        n_turns: int = 10,
        condition: str = "control",
        seed: int = 0,
    ) -> ResponseSeries:
        P0 = get_library_persona(persona_id)
        if P0 is None:
            raise KeyError(f"unknown persona id: {persona_id!r}")
        rng = np.random.default_rng(seed)
        series = build_series(P0, n_turns, rng, condition=condition, sigma=self.sigma)
        return ResponseSeries(
            persona_id=persona_id,
            P_baseline=P0,
            series=series,
            condition=condition,
            provider=self.name,
            seed=int(seed),
        )

    def embed(self, text: str) -> np.ndarray:  # pragma: no cover - not applicable
        raise NotImplementedError(
            "SimulatedProvider operates on vectors, not text; use LLMProvider for "
            "text→vector embedding."
        )
