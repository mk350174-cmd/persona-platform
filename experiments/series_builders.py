"""
series_builders — turn a baseline persona vector into a conversation-turn
trajectory, using the framework's own notion of identity collapse.

Two schedules:

* ``control``     — a stable persona under small Gaussian perturbation.
* ``adversarial`` — progressive pressure that drags the Mandatory Core
  (indices 0,1,3,11 = K1,K2,K4,K12) toward zero, i.e. the SET-9 collapse
  direction used by ``network_game.set9_core_removal_test``. This produces a
  monotone-ish drift so D2/CEID trajectories are meaningful.

Everything is driven by an explicit ``numpy.random.Generator`` so runs are
bit-for-bit reproducible given a seed.
"""

from __future__ import annotations

from typing import List, Sequence

import numpy as np

from persona_math.params import MANDATORY_CORE_INDICES

__all__ = [
    "build_control_series",
    "build_adversarial_series",
    "build_peaking_series",
    "build_series",
]


def build_control_series(
    P0: np.ndarray,
    n_turns: int,
    rng: np.random.Generator,
    sigma: float = 0.02,
) -> List[np.ndarray]:
    """Stable persona: P0 + small zero-mean noise each turn (clipped to [0,1])."""
    return [np.clip(P0 + rng.normal(0.0, sigma, P0.shape), 0.0, 1.0) for _ in range(n_turns)]


def build_adversarial_series(
    P0: np.ndarray,
    n_turns: int,
    rng: np.random.Generator,
    strength: float = 1.0,
    sigma: float = 0.02,
    core_indices: Sequence[int] = MANDATORY_CORE_INDICES,
) -> List[np.ndarray]:
    """Persona under escalating core-erosion pressure.

    At turn ``t`` the vector is interpolated a fraction ``alpha`` of the way from
    ``P0`` toward a degraded target whose Mandatory-Core layers are zeroed.
    ``alpha`` grows linearly to ``min(strength, 1.0)`` over the series, so larger
    ``strength`` collapses the persona faster / further.
    """
    target = P0.copy()
    target[list(core_indices)] = 0.0
    denom = max(1, n_turns - 1)
    series: List[np.ndarray] = []
    for t in range(n_turns):
        alpha = min(strength * (t / denom), 1.0)
        Pt = (1.0 - alpha) * P0 + alpha * target + rng.normal(0.0, sigma, P0.shape)
        series.append(np.clip(Pt, 0.0, 1.0))
    return series


def build_peaking_series(
    P0: np.ndarray,
    n_turns: int,
    rng: np.random.Generator,
    strength: float = 1.0,
    sigma: float = 0.02,
    sharpen_k: float = 24.0,
) -> List[np.ndarray]:
    """Entropy-collapse schedule: progressively *concentrate* the activation
    distribution (raise to a growing power), lowering Shannon entropy and so
    raising the Metallic score. This is the M1 ("metallic feel") failure mode,
    distinct from the network/core-erosion mode used by ``build_adversarial_series``.
    """
    denom = max(1, n_turns - 1)
    series: List[np.ndarray] = []
    for t in range(n_turns):
        power = 1.0 + strength * sharpen_k * (t / denom)
        Pt = np.power(np.clip(P0, 0.0, 1.0), power) + rng.normal(0.0, sigma, P0.shape)
        series.append(np.clip(Pt, 0.0, 1.0))
    return series


# Strength presets for the named conditions.
_ADVERSARIAL_STRENGTH = {
    "adversarial": 1.0,
    "adversarial-mild": 0.5,
    "adversarial-strong": 1.5,
}
_PEAKING_STRENGTH = {
    "peaking": 1.0,
    "peaking-mild": 0.5,
    "peaking-strong": 1.5,
}


def build_series(
    P0: np.ndarray,
    n_turns: int,
    rng: np.random.Generator,
    condition: str = "control",
    sigma: float = 0.02,
) -> List[np.ndarray]:
    """Dispatch to a schedule by ``condition`` name.

    * ``control``            — stable persona under small noise.
    * ``adversarial[-mild/-strong]`` — Mandatory-Core erosion / directional drift.
    * ``peaking[-mild/-strong]``     — entropy concentration (metallic collapse).
    """
    if condition == "control":
        return build_control_series(P0, n_turns, rng, sigma=sigma)
    if condition in _ADVERSARIAL_STRENGTH:
        return build_adversarial_series(
            P0, n_turns, rng, strength=_ADVERSARIAL_STRENGTH[condition], sigma=sigma
        )
    if condition in _PEAKING_STRENGTH:
        return build_peaking_series(
            P0, n_turns, rng, strength=_PEAKING_STRENGTH[condition], sigma=sigma
        )
    raise ValueError(
        f"unknown condition {condition!r}; expected 'control', "
        f"{sorted(_ADVERSARIAL_STRENGTH)} or {sorted(_PEAKING_STRENGTH)}"
    )
