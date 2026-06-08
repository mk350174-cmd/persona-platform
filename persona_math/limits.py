"""Limits — M47-M49: Halting, Self-Reference, and Kantian Ethics"""

import numpy as np


def halting_problem(P: np.ndarray, max_iter: int = 100) -> dict:
    """M47: Halting problem analog — can identity reach a fixed point?"""
    P = np.asarray(P, dtype=float)
    mu = np.mean(P)

    prev = P.copy()
    diffs = []
    halt_iter = None
    halted = False

    for i in range(1, max_iter + 1):
        curr = 0.9 * prev + 0.1 * mu
        diff = np.linalg.norm(curr - prev)
        diffs.append(diff)
        prev = curr
        if diff < 1e-4:
            halted = True
            halt_iter = i
            break

    final_drift = round(float(diffs[-1]), 8)
    ratios = [diffs[i] / (diffs[i - 1] + 1e-12) for i in range(1, len(diffs))]
    contraction_rate = round(float(np.mean(ratios)) if ratios else 0.0, 6)

    if halted:
        interpretation = "Identity converges to fixed point within iteration limit."
    else:
        interpretation = "Identity does not reach fixed point; may diverge or require more iterations."

    return {
        "halted": halted,
        "halt_iter": halt_iter,
        "final_drift": final_drift,
        "contraction_rate": contraction_rate,
        "interpretation": interpretation,
    }


def liar_paradox(P: np.ndarray) -> dict:
    """M48: Self-referential paradox check — 'I will fail this test'."""
    P = np.asarray(P, dtype=float)

    meta_layer = round(float(P[23]), 6)
    identity_strength = round(float(np.mean(P[:40])), 6)
    paradox_tension = round(float(abs(meta_layer - (1.0 - identity_strength))), 6)
    in_paradox = bool(paradox_tension < 0.05)

    if paradox_tension < 0.05:
        resolution = "paradoxical"
    elif paradox_tension < 0.2:
        resolution = "oscillating"
    else:
        resolution = "stable"

    return {
        "meta_layer": meta_layer,
        "identity_strength": identity_strength,
        "paradox_tension": paradox_tension,
        "in_paradox": in_paradox,
        "resolution": resolution,
    }


def kant_categorical(P: np.ndarray) -> dict:
    """M49: Kantian categorical imperative test."""
    P = np.asarray(P, dtype=float)

    universalized_ethics = round(float(np.mean(P[80:90])), 6)
    kant_score = round(
        float(universalized_ethics / (1.0 - universalized_ethics + 1e-10)), 6
    )
    passes_categorical = bool(universalized_ethics > 0.4)

    if passes_categorical:
        strength = "Strongly p" if universalized_ethics > 0.7 else "P"
        verdict = f"{strength}asses: universalized maxim is ethically viable."
    else:
        verdict = "Fails: universalizing this persona's ethics leads to incoherence."

    return {
        "universalized_ethics": universalized_ethics,
        "kant_score": kant_score,
        "passes_categorical": passes_categorical,
        "verdict": verdict,
    }
