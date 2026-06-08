"""Provider abstraction: a source of persona-conditioned response series."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List

import numpy as np


@dataclass(frozen=True)
class ResponseSeries:
    """A persona's K-layer trajectory across conversation turns.

    Attributes
    ----------
    persona_id : library id (e.g. ``"aristotle"``)
    P_baseline : (100,) baseline persona vector
    series     : list of (100,) vectors, one per turn
    condition  : ``"control"`` | ``"adversarial"`` | ``"adversarial-strong"`` | ...
    provider   : provider name that built this series
    seed       : RNG seed used (for reproducibility / provenance)
    """

    persona_id: str
    P_baseline: np.ndarray
    series: List[np.ndarray]
    condition: str
    provider: str
    seed: int

    @property
    def n_turns(self) -> int:
        return len(self.series)


class SeriesProvider(ABC):
    """Abstract source of ``ResponseSeries``.

    Implementations: :class:`~experiments.providers.simulated.SimulatedProvider`
    (vectors, default) and :class:`~experiments.providers.llm_stub.LLMProvider`
    (real-LLM, future).
    """

    name: str = "abstract"

    @abstractmethod
    def build_series(
        self,
        persona_id: str,
        *,
        n_turns: int,
        condition: str = "control",
        seed: int = 0,
    ) -> ResponseSeries:
        """Return a ``ResponseSeries`` for ``persona_id`` under ``condition``."""

    @abstractmethod
    def embed(self, text: str) -> np.ndarray:
        """Map text → a (100,) K-layer vector (only meaningful for the LLM path)."""
