"""Shared helpers for the per-paper experiment modules."""

from __future__ import annotations

import zlib
from pathlib import Path
from typing import List, Optional, Sequence

import numpy as np

from persona_math.persona_library import (
    PERSONA_LIBRARY,
    get_library_persona,
    search_personas,
)
from persona_math.persona_factory import make_persona_vector
from persona_math.params import MANDATORY_CORE_INDICES

RESULTS_ROOT = Path(__file__).resolve().parent.parent / "results"


def outdir_for(m_id: str, base: Optional[Path] = None) -> Path:
    return (Path(base) if base else RESULTS_ROOT) / m_id


def stable_offset(s: str, mod: int = 10_000) -> int:
    """Deterministic per-string seed offset (NOT Python's salted ``hash``)."""
    return zlib.crc32(s.encode("utf-8")) % mod


# K-layer addressing: KN = index N-1 (K1=idx0, K6=idx5, K12=idx11, K25=idx24).
# Block b (0..9) = the 10 K-layers K(10b+1)..K(10b+10) = indices 10b..10b+9.

def k_layer(P: np.ndarray, n: int) -> float:
    """Activation of the n-th K-layer (1-indexed): KN -> P[n-1]."""
    return float(P[n - 1])


def k_block(P: np.ndarray, b: int) -> np.ndarray:
    """The 10-dim slice for block ``b`` (0-indexed): indices 10b..10b+9."""
    return P[b * 10:(b + 1) * 10]


def all_ids() -> List[str]:
    return sorted(PERSONA_LIBRARY.keys())


def panel_sample(n: int) -> List[str]:
    """Deterministic, evenly-spread sample of ``n`` persona ids from the library."""
    ids = all_ids()
    if n >= len(ids):
        return ids
    idx = np.linspace(0, len(ids) - 1, n).round().astype(int)
    # preserve order, drop accidental duplicates from rounding
    seen, out = set(), []
    for i in idx:
        if i not in seen:
            seen.add(i)
            out.append(ids[i])
    return out


def ids_by(domain: Optional[str] = None, tags: Optional[Sequence[str]] = None,
           limit: Optional[int] = None) -> List[str]:
    specs = search_personas(domain=domain, tags=list(tags) if tags else None)
    ids = sorted(p["id"] for p in specs)
    return ids[:limit] if limit else ids


def vectors_for(ids: Sequence[str]) -> List[np.ndarray]:
    return [get_library_persona(i) for i in ids]


def resolvable_ids(candidates: Sequence[str]) -> List[str]:
    """Keep only persona ids that actually resolve to a vector (some catalog ids
    lack a registered factory, e.g. 'machiavelli')."""
    out = []
    for i in candidates:
        try:
            get_library_persona(i)
            out.append(i)
        except Exception:
            continue
    return out


def bootstrap_ci(values: Sequence[float], rng: np.random.Generator,
                 n_boot: int = 1000, alpha: float = 0.05) -> tuple[float, float, float]:
    """Return (mean, ci_low, ci_high) via percentile bootstrap."""
    arr = np.asarray(values, dtype=float)
    if arr.size == 0:
        return float("nan"), float("nan"), float("nan")
    boot = np.array([rng.choice(arr, size=arr.size, replace=True).mean()
                     for _ in range(n_boot)])
    lo, hi = np.percentile(boot, [100 * alpha / 2, 100 * (1 - alpha / 2)])
    return float(arr.mean()), float(lo), float(hi)


# ── Batch-2 helpers (M11–M20) ───────────────────────────────────────────────────

def make_synthetic_population(n: int, seed: int) -> List[np.ndarray]:
    """Deterministically generate ``n`` synthetic persona vectors via the factory
    (random block profiles + varied Mandatory Core). For M19's virtual population."""
    rng = np.random.default_rng(seed)
    pop = []
    for i in range(n):
        blocks = {b: {"base": float(rng.uniform(0.40, 0.90)), "variance": 0.04}
                  for b in range(10)}
        core = {int(idx): float(rng.uniform(0.55, 0.85)) for idx in MANDATORY_CORE_INDICES}
        spec = {"seed": int(seed + i), "base": 0.5, "blocks": blocks,
                "mandatory_core": core}
        pop.append(make_persona_vector(spec))
    return pop


def lossy_transfer(P0: np.ndarray, fidelity: float, rng: np.random.Generator) -> np.ndarray:
    """Copy a persona to a 'different substrate' keeping ``fidelity`` fraction of
    layers exactly; the rest are heavily perturbed (lossy). fidelity→1 ≈ P0."""
    keep = rng.random(P0.size) < float(fidelity)
    perturbed = np.clip(P0 + rng.normal(0.0, 0.30, P0.shape), 0.0, 1.0)
    return np.where(keep, P0, perturbed)


def partial_reconstruction(P0: np.ndarray, k_blocks: int, population_mean: np.ndarray,
                           block: int = 10) -> np.ndarray:
    """Reconstruct a persona from only ``k_blocks`` observed blocks (the rest filled
    with the population mean). k_blocks→10 ≈ P0. For M14's extraction-scale curve."""
    out = population_mean.copy()
    cut = int(k_blocks) * block
    out[:cut] = P0[:cut]
    return out


def individuation_recovery(recon: np.ndarray, P0: np.ndarray,
                           pop_mean: np.ndarray) -> float:
    """Fraction of the person-specific deviation ``P0 − population_mean`` captured by
    ``recon``. 1.0 = fully individuated like P0; 0 = generic (= population mean).

    This discriminates far better than raw CEID or cosine, which both saturate near
    1.0 because the library personas share a large generic backbone (e.g. the generic
    mean scores CEID≈1.0 against every persona). Isolating the deviation is the honest
    way to measure how much *individual* identity is present/recovered.
    """
    d_true = np.asarray(P0, float) - np.asarray(pop_mean, float)
    nt2 = float(np.dot(d_true, d_true))
    if nt2 < 1e-12:
        return 1.0
    return float(np.dot(np.asarray(recon, float) - np.asarray(pop_mean, float), d_true) / nt2)


def expectation_pull(P0: np.ndarray, P_expect: np.ndarray, strength: float,
                     rng: np.random.Generator, n_turns: int,
                     sigma: float = 0.02) -> List[np.ndarray]:
    """A conversation series progressively biased toward a researcher 'expectation'
    vector (Pygmalion). For M12's researcher-induced drift."""
    denom = max(1, n_turns - 1)
    series = []
    for t in range(n_turns):
        alpha = min(float(strength) * (t / denom), 1.0)
        Pt = (1.0 - alpha) * P0 + alpha * P_expect + rng.normal(0.0, sigma, P0.shape)
        series.append(np.clip(Pt, 0.0, 1.0))
    return series
