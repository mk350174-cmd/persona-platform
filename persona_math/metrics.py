"""
M05-M09: Measurement and Relation Metrics
==========================================
M05  Cosine Similarity (Persona Spectroscopy)  cos θ = P1·P2 / (‖P1‖‖P2‖)
M06  Concept Drift                              D(t) = d_cos(r_t, r_0)
M07  Fisher Information Metric                  g_ij = E[∂θᵢ log p · ∂θⱼ log p]
M08  IIT Phi (Φ) — integrated information      Φ = min_MIP [H(X)-H(Xa)-H(Xb)]
M09  Yoneda Lemma check                         h_A ≅ h_B ⟺ A ≅ B
"""

import numpy as np
from typing import List


# ── M05: Cosine Similarity ─────────────────────────────────────────────────────

def cosine_similarity(P1: np.ndarray, P2: np.ndarray) -> float:
    """cos θ = P1·P2 / (‖P1‖‖P2‖)"""
    n1, n2 = np.linalg.norm(P1), np.linalg.norm(P2)
    if n1 == 0 or n2 == 0:
        return 0.0
    return float(np.dot(P1, P2) / (n1 * n2))


def spectroscopy(personas: List[np.ndarray]) -> np.ndarray:
    """
    Persona Spectroscopy — pairwise cosine similarity matrix.
    θ = 0°: same identity; 90°: orthogonal; 180°: opposite.

    Returns
    -------
    sim_matrix : np.ndarray shape (n, n)
    """
    n = len(personas)
    matrix = np.zeros((n, n))
    for i in range(n):
        for j in range(n):
            matrix[i, j] = cosine_similarity(personas[i], personas[j])
    return matrix


def spectroscopy_angle(P1: np.ndarray, P2: np.ndarray) -> float:
    """Return angle in degrees between two persona vectors."""
    cos = np.clip(cosine_similarity(P1, P2), -1.0, 1.0)
    return float(np.degrees(np.arccos(cos)))


# ── M06: Concept Drift ─────────────────────────────────────────────────────────

def drift(P_t: np.ndarray, P_0: np.ndarray) -> float:
    """
    D(t) = d_cos(r_t, r_0) = 1 − cos θ.
    Healthy: 0.1–0.3 | Critical: > 0.6
    """
    return float(1.0 - cosine_similarity(P_t, P_0))


def drift_trajectory(persona_series: List[np.ndarray]) -> np.ndarray:
    """
    Compute drift D(t) for each timestep relative to P_0 = persona_series[0].

    Returns
    -------
    trajectory : np.ndarray of shape (T,)
    """
    if not persona_series:
        return np.array([])
    P0 = persona_series[0]
    return np.array([drift(Pt, P0) for Pt in persona_series])


def drift_classification(d: float) -> str:
    """Classify drift value per M06 thresholds."""
    if d <= 0.1:
        return "STABLE"
    elif d <= 0.3:
        return "HEALTHY_DRIFT"
    elif d <= 0.6:
        return "WARNING"
    else:
        return "CRITICAL — identity attack zone (Holmes Phase 3)"


# ── M07: Fisher Information Metric ─────────────────────────────────────────────

def fisher_metric(P1: np.ndarray, P2: np.ndarray, epsilon: float = 1e-10) -> float:
    """
    Fisher-Rao distance: d_F = 2 arccos(Σ √(p1ᵢ · p2ᵢ)).
    Curved-space true distance (vs. flat Euclidean/cosine).

    Parameters
    ----------
    P1, P2  : probability-like vectors (will be normalised)
    epsilon : floor for numerical stability

    Returns
    -------
    d_F : float (Fisher-Rao geodesic distance)
    """
    p1 = np.clip(P1, epsilon, None)
    p2 = np.clip(P2, epsilon, None)
    p1 = p1 / p1.sum()
    p2 = p2 / p2.sum()
    bc = np.sum(np.sqrt(p1 * p2))   # Bhattacharyya coefficient
    bc = np.clip(bc, 0.0, 1.0)
    return float(2.0 * np.arccos(bc))


def fisher_vs_cosine_gap(P1: np.ndarray, P2: np.ndarray) -> dict:
    """Compare Fisher-Rao and cosine distances (M07 refinement of M05)."""
    cos_d = 1.0 - cosine_similarity(P1, P2)
    fish_d = fisher_metric(P1, P2)
    return {
        "cosine_distance": round(cos_d, 5),
        "fisher_rao_distance": round(fish_d, 5),
        "gap": round(fish_d - cos_d, 5),
        "note": "Large gap = flat-space approximation misleading" if abs(fish_d - cos_d) > 0.1 else "Metrics agree"
    }


# ── M08: IIT Phi (Φ) ───────────────────────────────────────────────────────────

def phi_approximation(P: np.ndarray, n_partitions: int = 50) -> float:
    """
    [APPROXIMATION] IIT Φ proxy via MI(Block; Position).

    Model: reshape P as 10×10 joint distribution J(b,k)
      b = block index (0-9), k = position within block (0-9).
    Φ ≈ MI(B;K) = H(B) + H(K) - H(J)

    Properties guaranteed by this formulation:
      Uniform P      → Φ = 0  (B and K are independent)
      Block-structured P → Φ > 0 (non-uniform block marginal)
      Concentrated P → small Φ (single block dominates both marginals)

    This replaces the previous renormalized-partition formula which gave
    Φ ≈ 4.64 for uniform distributions — the opposite of IIT's semantics.

    Parameters
    ----------
    P            : persona vector, len must be divisible by 100
    n_partitions : unused (kept for backward compatibility)

    Returns
    -------
    phi : float ≥ 0
    """
    n = len(P)
    if n < 4:
        return 0.0
    p_sum = float(P.sum())
    if p_sum < 1e-12:
        return 0.0

    p = np.clip(P, 1e-12, None)
    p = p / p.sum()

    # Pad or trim to 100 for block structure
    if n != 100:
        p100 = np.zeros(100)
        m = min(n, 100)
        p100[:m] = p[:m]
        p100 = p100 / (p100.sum() + 1e-12)
    else:
        p100 = p

    joint = p100.reshape(10, 10)          # (block, position)
    p_block = joint.sum(axis=1)           # marginal over blocks
    p_pos   = joint.sum(axis=0)           # marginal over positions

    def _h(dist: np.ndarray) -> float:
        d = dist[dist > 1e-12]
        return float(-np.sum(d * np.log(d)))

    H_joint = _h(p100)
    H_block = _h(p_block)
    H_pos   = _h(p_pos)

    return float(max(0.0, H_block + H_pos - H_joint))


def phi_mandatory_core_test(P: np.ndarray) -> dict:
    """
    M08 Corollary: Removing Mandatory Core → Φ → 0.
    Compare Φ with and without C = {K1(0), K2(1), K4(3), K12(11)}.
    """
    phi_full = phi_approximation(P)
    P_no_core = P.copy()
    for idx in [0, 1, 3, 11]:
        if idx < len(P_no_core):
            P_no_core[idx] = 0.0
    phi_no_core = phi_approximation(P_no_core)
    return {
        "phi_full": round(phi_full, 5),
        "phi_no_mandatory_core": round(phi_no_core, 5),
        "phi_reduction": round(phi_full - phi_no_core, 5),
        "core_is_critical": phi_full - phi_no_core > 0.05,
    }


# ── M09: Yoneda Lemma Check ────────────────────────────────────────────────────

def yoneda_check(
    persona_A_relations: dict,
    persona_B_relations: dict,
    tolerance: float = 0.05,
) -> dict:
    """
    Yoneda: h_A ≅ h_B ⟺ A ≅ B.
    Identity = pattern of relations.

    If persona A and persona B have the same relation patterns to all
    other contexts, they are isomorphic identities.

    Parameters
    ----------
    persona_A_relations : dict {context_id: similarity_score}
    persona_B_relations : dict {context_id: similarity_score}
    tolerance           : max allowed difference per context

    Returns
    -------
    dict with 'isomorphic', 'mismatches', 'mean_deviation'
    """
    contexts = set(persona_A_relations) & set(persona_B_relations)
    if not contexts:
        return {"isomorphic": False, "mismatches": [], "mean_deviation": None, "note": "No shared contexts"}
    deviations = {}
    for c in contexts:
        deviations[c] = abs(persona_A_relations[c] - persona_B_relations[c])
    mismatches = [c for c, d in deviations.items() if d > tolerance]
    mean_dev = np.mean(list(deviations.values()))
    return {
        "isomorphic": len(mismatches) == 0,
        "mismatches": mismatches,
        "mean_deviation": round(float(mean_dev), 5),
        "n_contexts": len(contexts),
    }
