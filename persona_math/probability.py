"""Probability — M26-M28: Markov chain evolution, Bayesian update, Markov blanket."""

import numpy as np


def markov_persona(P, n_steps=10, noise=0.02):
    """M26: Markov chain evolution of persona over n_steps."""
    P = np.asarray(P, dtype=float)
    trajectory = np.empty((n_steps + 1, P.size))
    trajectory[0] = P.ravel()
    current = P.ravel().copy()
    for i in range(1, n_steps + 1):
        current = current + noise * np.random.randn(P.size)
        trajectory[i] = current
    drifts = np.linalg.norm(trajectory - trajectory[0], axis=1)
    mean_drift = float(np.mean(drifts))
    stays_bounded = bool(np.all(drifts < 1.5))
    return {
        "trajectory": trajectory,
        "mean_drift": round(mean_drift, 6),
        "stays_bounded": stays_bounded,
    }


def bayesian_update(P, evidence, prior_strength=0.8):
    """M27: Bayesian belief update with KL divergence and L1 belief shift."""
    P = np.asarray(P, dtype=float)
    evidence = np.asarray(evidence, dtype=float)
    posterior = prior_strength * P + (1.0 - prior_strength) * evidence
    lo, hi = posterior.min(), posterior.max()
    if hi > lo:
        posterior = (posterior - lo) / (hi - lo)
    else:
        posterior = np.zeros_like(posterior)
    eps = 1e-10
    p = np.clip(posterior.ravel(), eps, None)
    q = np.clip(P.ravel(), eps, None)
    p_norm = p / p.sum()
    q_norm = q / q.sum()
    kl = float(np.sum(p_norm * np.log(p_norm / (q_norm + eps))))
    belief_shift = float(np.sum(np.abs(posterior.ravel() - P.ravel())))
    return {
        "posterior": posterior,
        "kl_divergence_from_prior": round(kl, 6),
        "belief_shift": round(belief_shift, 6),
    }


def markov_blanket(P, threshold=0.5):
    """M28: Pearl's Markov blanket — classify layers by activation level."""
    P = np.asarray(P, dtype=float)
    layers = P.ravel()
    inside = layers > threshold
    boundary = (layers >= threshold - 0.15) & (layers <= threshold + 0.15)
    outside = layers < (threshold - 0.15)
    inside_count = int(inside.sum())
    boundary_count = int(boundary.sum())
    outside_count = int(outside.sum())
    total = layers.size
    blanket_fraction = round(boundary_count / total if total > 0 else 0.0, 6)
    inside_sum = float(layers[inside & ~boundary].sum())
    boundary_sum = float(layers[boundary].sum())
    denom = abs(inside_sum) + abs(boundary_sum)
    blanket_quality = round((inside_sum - boundary_sum) / denom if denom > 0 else 0.0, 6)
    return {
        "inside_count": inside_count,
        "boundary_count": boundary_count,
        "outside_count": outside_count,
        "blanket_fraction": blanket_fraction,
        "blanket_quality": blanket_quality,
    }
