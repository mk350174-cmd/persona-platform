import numpy as np


def wave_collapse(P, observation):
    """M40: Quantum wave function collapse analog."""
    P, obs = np.array(P, dtype=float), np.array(observation, dtype=float)

    def entropy(v):
        v = np.abs(v)
        total = v.sum()
        if total == 0:
            return 0.0
        p = v / total
        p = p[p > 0]
        return float(-np.sum(p * np.log2(p)))

    h_before = entropy(P)
    collapsed = P * obs
    norm = np.linalg.norm(collapsed)
    state = collapsed / norm if norm > 0 else collapsed
    return {
        "collapsed_state": state.tolist(),
        "collapse_entropy_reduction": round(h_before - entropy(state), 6),
        "decoherence_magnitude": round(float(np.linalg.norm(P - state)), 6),
    }


def bell_inequality(P1, P2, n_measurements=4):
    """M41: CHSH Bell inequality test for persona correlation."""
    P1, P2 = np.array(P1, dtype=float), np.array(P2, dtype=float)
    qa = [P1[i*25:(i+1)*25] for i in range(4)]
    qb = [P2[i*25:(i+1)*25] for i in range(4)]

    def corr(a, b):
        na, nb = np.linalg.norm(a), np.linalg.norm(b)
        return 0.0 if na == 0 or nb == 0 else float(np.mean((a/na)*(b/nb)))

    chsh = abs(corr(qa[0],qb[1]) - corr(qa[0],qb[3]) + corr(qa[2],qb[1]) + corr(qa[2],qb[3]))
    return {
        "chsh_value": round(chsh, 6),
        "violates_classical": bool(chsh > 2),
        "entanglement_degree": round(chsh / 2.8284271247, 6),
    }


def quantum_logic(P):
    """M42: Quantum logic lattice check."""
    P = np.array(P, dtype=float)
    blocks = [P[i*25:(i+1)*25] for i in range(4)]
    total = np.abs(P).sum() or 1.0

    def prob(b): return float(np.abs(b).sum() / total)

    pA, pB = prob(blocks[0]), prob(blocks[1])
    pAB = float(np.minimum(np.abs(blocks[0]), np.abs(blocks[1])).sum() / total)
    classical_probability = round(pA + pB - pAB, 6)
    quantum_prob = round(((np.abs(blocks[0]).sum() + np.abs(blocks[1]).sum()) / total)**2 / 2, 6)
    quantum_deviation = round(float(abs(classical_probability - quantum_prob)), 6)
    return {
        "classical_probability": classical_probability,
        "quantum_deviation": quantum_deviation,
        "lattice_type": "quantum" if quantum_deviation > 0.05 else "classical",
        "superposition_count": int(sum(1 for b in blocks if 0.4 < float(np.abs(b).mean()) < 0.6)),
    }


def morphological_field(P, P_target):
    """M43: Morphological field analog (Sheldrake-inspired, mathematical only)."""
    P, T = np.array(P, dtype=float), np.array(P_target, dtype=float)
    np_, nt = np.linalg.norm(P), np.linalg.norm(T)
    resonance = round(float(np.dot(P, T) / (np_ * nt)), 6) if np_ > 0 and nt > 0 else 0.0
    field_strength = round(float(np.linalg.norm(P - T)), 6)
    morphic_index = round(resonance / (field_strength + 0.01), 6)
    if morphic_index > 5:
        interp = "strong morphic resonance"
    elif morphic_index > 1:
        interp = "moderate field coupling"
    elif morphic_index > 0:
        interp = "weak field influence"
    else:
        interp = "field divergence"
    return {
        "resonance": resonance,
        "field_strength": field_strength,
        "morphic_index": morphic_index,
        "interpretation": interp,
    }
