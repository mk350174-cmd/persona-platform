"""Scale Transform — M37-M39: renormalization group, effective sample size, criticality index."""

import numpy as np


def renormalization_group(P, n_steps=4):
    """M37: RG flow coarse-graining via successive pair-averaging."""
    P = np.asarray(P, dtype=float)
    P = P / P.sum()

    trajectory = [P.copy()]
    dominant_mode_sequence = [int(np.argmax(P))]

    current = P.copy()
    for _ in range(n_steps):
        n = len(current)
        if n < 2:
            break
        pairs = n // 2
        coarse = (current[:2 * pairs:2] + current[1:2 * pairs:2]) / 2.0
        if n % 2 == 1:
            coarse = np.append(coarse, current[-1])
        s = coarse.sum()
        if s > 0:
            coarse /= s
        trajectory.append(coarse.copy())
        dominant_mode_sequence.append(int(np.argmax(coarse)))
        current = coarse

    last = trajectory[-1]
    prev = trajectory[-2] if len(trajectory) >= 2 else last
    min_len = min(len(last), len(prev))
    fixed_point_distance = round(float(np.linalg.norm(last[:min_len] - prev[:min_len])), 6)

    def entropy(v):
        return float(-np.sum(v[v > 0] * np.log(v[v > 0])))

    return {
        "coarse_graining_trajectory": [arr.tolist() for arr in trajectory],
        "fixed_point_distance": fixed_point_distance,
        "rg_stable": fixed_point_distance < 0.05,
        "dominant_mode_sequence": dominant_mode_sequence,
        "entropy_sequence": [round(entropy(arr), 6) for arr in trajectory],
    }


def effective_sample_size(P):
    """M38: ESS for persona distribution."""
    P = np.asarray(P, dtype=float)
    P = np.abs(P)
    total = P.sum()
    if total == 0:
        return {"ESS": 0.0, "normalized_ESS": 0.0, "interpretation": "concentrated"}

    ess = float((total ** 2) / np.sum(P ** 2))
    n = len(P)
    norm_ess = round(ess / n, 6)
    ess = round(ess, 6)

    if norm_ess >= 0.8:
        interpretation = "uniform"
    elif norm_ess >= 0.4:
        interpretation = "balanced"
    else:
        interpretation = "concentrated"

    return {"ESS": ess, "normalized_ESS": norm_ess, "interpretation": interpretation}


def criticality_index(P):
    """M39: Distance from critical point (edge of chaos)."""
    P = np.asarray(P, dtype=float)
    s = P.sum()
    if s != 0:
        P = P / s

    variance = round(float(np.var(P)), 6)

    n = len(P)
    if n > 1:
        mean = P.mean()
        c0 = np.sum((P - mean) ** 2)
        c1 = np.sum((P[:-1] - mean) * (P[1:] - mean))
        autocorr_lag1 = round(float(c1 / c0) if c0 != 0 else 0.0, 6)
    else:
        autocorr_lag1 = 0.0

    sv = np.sort(P)[::-1]
    sv = sv[sv > 0]
    if len(sv) > 2:
        slope, _ = np.polyfit(np.log(np.arange(1, len(sv) + 1, dtype=float)), np.log(sv), 1)
        power_law_exponent = round(float(-slope), 6)
    else:
        power_law_exponent = 0.0

    ideal = np.array([0.1, 0.7, 1.0])
    observed = np.array([variance, autocorr_lag1, power_law_exponent])
    criticality_distance = round(float(np.linalg.norm(observed - ideal)), 6)

    return {
        "variance": variance,
        "autocorr_lag1": autocorr_lag1,
        "power_law_exponent": power_law_exponent,
        "criticality_distance": criticality_distance,
        "at_criticality": criticality_distance < 0.3,
    }
