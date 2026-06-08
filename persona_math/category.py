"""Category Theory — M19-M21 Sheaf consistency, functor mapping, natural transformation."""

import numpy as np


def _blocks(P: np.ndarray, n: int = 10) -> list:
    return np.array_split(P, n)


def _cosine(a: np.ndarray, b: np.ndarray) -> float:
    na, nb = np.linalg.norm(a), np.linalg.norm(b)
    if na == 0 or nb == 0:
        return 0.0
    return float(np.dot(a, b) / (na * nb))


# ── M19: Sheaf Consistency ────────────────────────────────────────────────────

def sheaf_consistency(P: np.ndarray, sections=None, threshold: float = 0.05):
    blocks = _blocks(P) if sections is None else sections
    global_mean = float(np.mean(P))
    consistent, inconsistent = [], []
    for i, blk in enumerate(blocks):
        local_mean = float(np.mean(blk))
        if abs(local_mean - global_mean) < threshold:
            consistent.append(i)
        else:
            inconsistent.append(i)
    global_coherence = round(len(consistent) / len(blocks), 4)
    return {
        "consistent_sections": consistent,
        "inconsistent_sections": inconsistent,
        "global_coherence": global_coherence,
        "sheaf_valid": len(inconsistent) == 0,
    }


# ── M20: Functor Mapping ──────────────────────────────────────────────────────

def functor_mapping(P: np.ndarray, Q: np.ndarray):
    p_blocks = _blocks(P)
    q_blocks = _blocks(Q)
    n = len(p_blocks)
    M = np.zeros((n, n))
    for i, pb in enumerate(p_blocks):
        for j, qb in enumerate(q_blocks):
            M[i, j] = _cosine(pb, qb)
    diag_sum = float(np.trace(M))
    total_sum = float(np.sum(np.abs(M)))
    structure_preservation = round(diag_sum / total_sum, 4) if total_sum != 0 else 0.0
    faithful = structure_preservation > 0.5
    return {
        "mapping_matrix": np.round(M, 4).tolist(),
        "faithful": faithful,
        "structure_preservation": structure_preservation,
    }


# ── M21: Natural Transformation ───────────────────────────────────────────────

def natural_transform(P: np.ndarray, Q: np.ndarray, P_prime: np.ndarray, Q_prime: np.ndarray):
    p_blocks  = _blocks(P)
    q_blocks  = _blocks(Q)
    pp_blocks = _blocks(P_prime)
    qp_blocks = _blocks(Q_prime)
    n = len(p_blocks)

    # F: P→Q, G: P'→Q'  morphism vectors per block (mean vectors)
    F_morphisms = [np.mean(q_blocks[i]) - np.mean(p_blocks[i]) for i in range(n)]
    G_morphisms = [np.mean(qp_blocks[i]) - np.mean(pp_blocks[i]) for i in range(n)]

    # η_P: P→P', η_Q: Q→Q' (component cosine similarities)
    eta_P = [_cosine(p_blocks[i], pp_blocks[i]) for i in range(n)]
    eta_Q = [_cosine(q_blocks[i], qp_blocks[i]) for i in range(n)]

    # commutativity gap: |η_Q ∘ F - G ∘ η_P| per block (scalar proxy)
    gaps = [abs(eta_Q[i] * F_morphisms[i] - G_morphisms[i] * eta_P[i]) for i in range(n)]
    commutativity_gap = round(float(np.mean(gaps)), 6)
    naturality_score = round(1.0 / (1.0 + commutativity_gap), 4)
    commutative = commutativity_gap < 0.05

    return {
        "commutative": commutative,
        "commutativity_gap": commutativity_gap,
        "naturality_score": naturality_score,
    }
