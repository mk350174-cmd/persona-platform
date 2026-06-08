"""
M01-M04: Foundational Mathematical Infrastructure
=================================================
M01  Vector Space Representation   P = (k1,...,kn) ∈ ℝⁿ,  kᵢ ∈ [0,1]
M02  Mandatory Core Axioms         C = {K1, K2, K4, K12}
M03  Shannon Entropy               H(P) = -Σ kᵢ log₂ kᵢ
M04  Kolmogorov Complexity         K(P) = min{|prog| : U(prog) = P}
"""

import numpy as np
from typing import Sequence
from .params import MANDATORY_CORE_THRESHOLD

# ── M01: Vector Space Representation ──────────────────────────────────────────


def vector_p(layer_weights: Sequence[float], n: int = 100) -> np.ndarray:
    """
    Construct persona vector P ∈ ℝⁿ with kᵢ ∈ [0,1].

    Parameters
    ----------
    layer_weights : sequence of floats, len ≤ n
    n             : dimensionality (default 100 K-layers)

    Returns
    -------
    P : np.ndarray shape (n,)  — clipped to [0, 1]
    """
    P = np.zeros(n)
    weights = np.array(layer_weights, dtype=float)
    length = min(len(weights), n)
    P[:length] = np.clip(weights[:length], 0.0, 1.0)
    return P


def identity_strength(P: np.ndarray) -> float:
    """‖P‖ = √(Σ kᵢ²) — overall identity strength."""
    return float(np.linalg.norm(P))


# ── M02: Mandatory Core Axioms ─────────────────────────────────────────────────

def mandatory_core_check(P: np.ndarray, epsilon: float = MANDATORY_CORE_THRESHOLD) -> dict:
    """
    Verify M02 axiom: ∀i ∈ C : kᵢ(P) > ε.
    C = {K1(idx 0), K2(idx 1), K4(idx 3), K12(idx 11)}

    Returns
    -------
    dict with keys: 'passed', 'violations', 'core_values'
    """
    core_values = {
        "K1": P[0] if len(P) > 0 else 0.0,
        "K2": P[1] if len(P) > 1 else 0.0,
        "K4": P[3] if len(P) > 3 else 0.0,
        "K12": P[11] if len(P) > 11 else 0.0,
    }
    violations = [k for k, v in core_values.items() if v <= epsilon]
    return {
        "passed": len(violations) == 0,
        "violations": violations,
        "core_values": core_values,
        "epsilon": epsilon,
    }


# ── M03: Shannon Entropy ────────────────────────────────────────────────────────

def shannon_h(P: np.ndarray, base: float = 2.0) -> float:
    """
    H(P) = -Σ kᵢ log_base(kᵢ)   (zero terms skipped).

    Parameters
    ----------
    P    : persona vector (non-negative)
    base : logarithm base (default 2, bits)

    Returns
    -------
    H : float ≥ 0
    """
    p = np.array(P, dtype=float)
    p = p[p > 0]
    if len(p) == 0:
        return 0.0
    p_norm = p / p.sum()
    return float(-np.sum(p_norm * np.log(p_norm) / np.log(base)))


def shannon_h_max(n: int, base: float = 2.0) -> float:
    """H_max = log_base(n) — maximum entropy for n equal layers."""
    return float(np.log(n) / np.log(base))


def metallic_score_raw(P: np.ndarray) -> float:
    """
    Metallic Feel Score = 1 − H(P)/H_max.
    0 = maximally rich persona; 1 = fully Metallic (collapsed to one layer).
    """
    n = len(P)
    if n == 0:
        return 1.0
    h = shannon_h(P)
    h_max = shannon_h_max(n)
    if h_max == 0:
        return 1.0
    return float(1.0 - h / h_max)


# ── M04: Kolmogorov Complexity (bounds) ────────────────────────────────────────

def kolmogorov_bound(P: np.ndarray, precision: int = 3) -> dict:
    """
    Approximate Kolmogorov complexity via compression ratio.
    True K(P) is uncomputable; we use lossless compression length as upper bound.

    Parameters
    ----------
    P         : persona vector
    precision : decimal places for rounding before compression

    Returns
    -------
    dict with 'upper_bound_bytes', 'compression_ratio', 'interpretation'
    """
    import zlib
    raw = np.round(P, precision)
    raw_bytes = raw.tobytes()
    compressed = zlib.compress(raw_bytes, level=9)
    ratio = len(compressed) / max(len(raw_bytes), 1)
    # M7 claim: Deep persona has LOW K (compact rules, wide behaviour);
    # Metallic has HIGH K (must enumerate every canned response).
    # Proxy: entropy-based K = H_max - H(P). High value → sparse/concentrated
    # → Metallic (many bits needed to describe all canned responses).
    # Low value → uniform → Deep (few bits: "distribute evenly across K-layers").
    h_proxy = shannon_h_max(len(P)) - shannon_h(np.clip(P, 1e-12, None))
    h_max_val = shannon_h_max(len(P)) if len(P) > 0 else 1.0
    k_normalised = h_proxy / h_max_val if h_max_val > 0 else 0.0
    interpretation = (
        "Deep persona (low K — compact description, wide behaviour)" if k_normalised < 0.4 else
        "Intermediate" if k_normalised < 0.7 else
        "Metallic persona (high K — verbose description, narrow behaviour)"
    )
    return {
        "upper_bound_bytes": len(compressed),
        "raw_bytes": len(raw_bytes),
        "compression_ratio": round(ratio, 4),
        "k_normalised": round(k_normalised, 4),
        "interpretation": interpretation,
    }


# ── Convenience summary ─────────────────────────────────────────────────────────

def persona_summary(P: np.ndarray, epsilon: float = 0.15) -> dict:
    """
    Full M01-M04 diagnostic for a persona vector P.
    """
    n = len(P)
    h = shannon_h(P)
    h_max = shannon_h_max(n)
    ms = metallic_score_raw(P)
    core = mandatory_core_check(P, epsilon)
    kb = kolmogorov_bound(P)

    return {
        "n_layers": n,
        "identity_strength": round(identity_strength(P), 4),
        "shannon_H": round(h, 4),
        "H_max": round(h_max, 4),
        "metallic_score": round(ms, 4),
        "mandatory_core": core,
        "kolmogorov": kb,
        "status": (
            "METALLIC — persona collapse risk" if ms > 0.7 else
            "SHALLOW" if ms > 0.4 else
            "DEEP persona"
        ),
    }
