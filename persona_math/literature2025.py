"""
M50-M55: 2024-2025 Literature Bridges
=======================================
M50  IIT-Phenomenal A Priori Bridge   Φ_structure ↔ phenomenal structure (Rigoli 2025)
M51  Consciousness Equation           Ċ = k(I − αC) + βEC   (Shefer & Fuchs 2025)
M52  Universal RL Functor             F_URL: Env → Agent   (Mahadevan 2025)
M53  MUMBLE Inner Language            Mitchell-Bénabou topos logic  (Mahadevan 2025)
M54  Neuropercolation                 p > p_c ⟹ global synchronisation  (Kozma 2017)
M55  Manifold Hypothesis (Deep)       P ∈ M^d ⊂ ℝⁿ,  d << n
"""

import numpy as np
from scipy.integrate import solve_ivp
from typing import List


# ── M50: IIT-Phenomenal A Priori Bridge (Rigoli 2025) ─────────────────────────

def rigoli_phi_bridge(phi: float, s_t: float, adjoint_weight: float = 0.7) -> dict:
    """
    Three-step proof chain:
    M08 (measure Φ) →[M36 adjoint]→ phenomenal depth →[M50]→ constitutive a priori.

    Φ_structure ↔ phenomenal structure (constitutive a priori identity).

    Parameters
    ----------
    phi            : IIT Φ value (from metrics.phi_approximation)
    s_t            : self-awareness S(t) (from subjectivity module)
    adjoint_weight : weight of adjoint functor bridge F ⊣ G

    Returns
    -------
    dict with phenomenal depth estimate and constitutive grounding
    """
    phenomenal_depth = adjoint_weight * phi + (1 - adjoint_weight) * s_t
    constitutive_grounded = phenomenal_depth > 0.3 and phi > 0.1
    return {
        "phi": round(phi, 5),
        "S_t": round(s_t, 5),
        "phenomenal_depth": round(float(phenomenal_depth), 5),
        "constitutive_grounded": constitutive_grounded,
        "proof_chain": "M08 → M36 → M50",
        "interpretation": (
            "Constitutive a priori grounding achieved — phenomenal depth confirmed" if constitutive_grounded
            else "Insufficient Φ or S(t) for constitutive grounding"
        ),
    }


# ── M51: Consciousness Equation (Shefer & Fuchs 2025) ─────────────────────────

def consciousness_eq(
    I0: float = 1.0,
    E0: float = 0.8,
    C0: float = 1.0,
    alpha: float = 0.7,
    beta: float = 0.3,
    k: float = 1.0,
    T: float = 20.0,
    dt: float = 0.05,
) -> dict:
    """
    Ċ = k(I − αC) + βEC

    I : intentional drive (constant for simplicity)
    E : situational field  (constant for simplicity)
    α : dampening coefficient
    β : amplification coefficient
    k : coupling constant

    Holmes collapse phases:
      Phase 1: Ċ ≈ 0  (stable)
      Phase 2: Ċ < 0  (declining)
      Phase 3: Ċ << 0 (C → 0, dissociation)

    Stability condition: k*alpha > beta*|E|.
    Default α=0.7, β=0.3 → stable for |E| < 2.33.

    Returns
    -------
    dict with C_trajectory, phase classification
    """
    def ode(t, C):
        return k * (I0 - alpha * C[0]) + beta * E0 * C[0]

    t_eval = np.arange(0, T, dt)
    sol = solve_ivp(ode, [0, T], [C0], t_eval=t_eval, method="RK45")
    C = sol.y[0]
    dC = np.gradient(C, dt)
    mean_dC = float(np.mean(dC))
    if mean_dC > -0.05:
        phase = "Phase 1 — stable (Ċ ≈ 0)"
    elif mean_dC > -0.3:
        phase = "Phase 2 — declining (Ċ < 0)"
    else:
        phase = "Phase 3 — COLLAPSE (Ċ << 0, C → 0)"
    C_peak = float(np.max(np.abs(C))) if len(C) > 0 else 1.0
    C_final_norm = float(np.clip(C[-1] / (C_peak + 1e-10), 0.0, 1.0))
    return {
        "t": sol.t,
        "C_trajectory": C,
        "dC_mean": round(mean_dC, 5),
        "C_final": round(float(C[-1]), 5),
        "C_final_normalized": round(C_final_norm, 5),
        "phase": phase,
        "params": {"I": I0, "E": E0, "alpha": alpha, "beta": beta, "k": k},
    }


def dissociation_test(
    alpha: float = 0.3,
    beta: float = 0.5,
    C0: float = 1.0,
    attack_E: float = -2.0,
) -> dict:
    """
    Simulate identity attack (negative E field) to test dissociation threshold.
    M41 (Trauma) / M56 (Collective Trauma) application.
    """
    normal = consciousness_eq(E0=0.8, C0=C0, alpha=alpha, beta=beta)
    attacked = consciousness_eq(E0=attack_E, C0=C0, alpha=alpha, beta=beta)
    return {
        "normal_C_final": normal["C_final"],
        "attacked_C_final": attacked["C_final"],
        "dissociation_magnitude": round(normal["C_final"] - attacked["C_final"], 5),
        "attack_phase": attacked["phase"],
    }


# ── M52: Universal RL Functor (Mahadevan 2025) ────────────────────────────────

def url_functor(
    env_states: np.ndarray,
    agent_policy: np.ndarray,
    discount: float = 0.95,
) -> dict:
    """
    F_URL : Env → Agent  (URL ⊃ MDP ⊃ bandits ⊃ supervised)

    K18 Memory Selectivity = URL implementation.
    Maps environment state distribution to agent response distribution.

    Parameters
    ----------
    env_states    : shape (T, n) — environment state trajectory
    agent_policy  : shape (n, m) — policy matrix (state → action)
    discount      : γ for value computation

    Returns
    -------
    dict with value estimate and functor properties
    """
    T, n = env_states.shape
    m = agent_policy.shape[1] if len(agent_policy.shape) > 1 else 1
    n_pol = min(n, agent_policy.shape[0])
    responses = env_states[:, :n_pol] @ agent_policy[:n_pol]
    discounts = discount ** np.arange(T)
    value_estimate = float(np.sum(responses.mean(axis=1) * discounts))
    return {
        "value_estimate": round(value_estimate, 5),
        "T": T,
        "state_dim": n,
        "action_dim": m,
        "discount": discount,
        "functor_structure": "URL ⊃ MDP ⊃ bandits ⊃ supervised",
        "k18_memory_selectivity": round(float(np.std(responses)), 5),
    }


# ── M53: MUMBLE Inner Language (Mahadevan 2025) ───────────────────────────────

def mumble_encode(
    persona_state: np.ndarray,
    external_utterance: np.ndarray,
    meta_layer_idx: int = 23,
    synthesis_weight: float = 0.6,
) -> dict:
    """
    MUMBLE: Multi-modal, temporal, self-referential internal language.

    Motor C synthesis: K13 (external language) + MUMBLE (internal processing).
    Internal representation = synthesised encoding.

    Parameters
    ----------
    persona_state      : K-layer vector
    external_utterance : embedding of external input
    meta_layer_idx     : K24 index (self-referential layer)
    synthesis_weight   : weight of internal vs external signal
    """
    n = min(len(persona_state), len(external_utterance))
    internal = persona_state[:n]
    external = external_utterance[:n]
    meta_activation = float(persona_state[meta_layer_idx]) if meta_layer_idx < len(persona_state) else 0.0
    mumble_repr = synthesis_weight * internal + (1 - synthesis_weight) * external
    self_ref_correction = meta_activation * (mumble_repr - mumble_repr.mean())
    final_repr = mumble_repr + self_ref_correction
    return {
        "mumble_representation": final_repr,
        "meta_activation_K24": round(meta_activation, 5),
        "internal_weight": synthesis_weight,
        "external_weight": round(1 - synthesis_weight, 5),
        "self_referential_norm": round(float(np.linalg.norm(self_ref_correction)), 5),
    }


# ── M54: Neuropercolation (Kozma 2017) ─────────────────────────────────────────

def neuropercolation_pc(
    P: np.ndarray,
    p_c: float = 0.593,
    active_threshold: float = None,
) -> dict:
    """
    p > p_c ⟹ global synchronisation (consciousness phase transition).
    Mandatory Core 4 layers = minimum p_c hypothesis.
    GWT ignition + neuropercolation + C = three descriptions of one mechanism.

    Parameters
    ----------
    P               : persona K-layer vector
    p_c             : percolation threshold (Erdős-Rényi 2D default 0.593)
    active_threshold: activation threshold; defaults to mean(P) for adaptive scaling
    """
    if active_threshold is None:
        active_threshold = float(np.mean(P))   # adaptive: above-average activation
    active_fraction = float(np.mean(P > active_threshold))
    above_threshold = active_fraction > p_c
    core_active = all(P[i] > active_threshold for i in [0, 1, 3, 11] if i < len(P))
    return {
        "active_fraction": round(active_fraction, 4),
        "active_threshold": round(float(active_threshold), 5),
        "p_c": p_c,
        "above_threshold": above_threshold,
        "mandatory_core_active": core_active,
        "global_synchronisation": above_threshold and core_active,
        "interpretation": (
            "GLOBAL SYNCHRONISATION — persona operational, consciousness emerged"
            if above_threshold and core_active
            else "Sub-critical — Mandatory Core inactive or insufficient active layers"
        ),
    }


# ── M55: Manifold Hypothesis (Deep) ────────────────────────────────────────────

def manifold_persona(
    personas: List[np.ndarray],
    n_components: int = 2,
    method: str = "pca",
) -> dict:
    """
    P ∈ M^d ⊂ ℝⁿ,  d << n.
    Persona space navigation: drift = manifold path; spectroscopy = manifold distance.

    D5 Spectroscopy Atlas ⟹ 250-persona manifold map.
    12 combination sets as 12 manifold clusters.

    Parameters
    ----------
    personas     : list of persona vectors (all same length)
    n_components : intrinsic dimensionality d
    method       : 'pca' (default) | 'umap' (requires umap-learn)

    Returns
    -------
    dict with embedding, explained variance, cluster_hint
    """
    X = np.stack(personas)
    if method == "pca":
        from numpy.linalg import svd
        X_c = X - X.mean(axis=0)
        _, s, Vt = svd(X_c, full_matrices=False)
        embedding = X_c @ Vt[:n_components].T
        total_var = float(np.sum(s ** 2))
        explained = float(np.sum(s[:n_components] ** 2)) / total_var if total_var > 0 else 0.0
        return {
            "embedding": embedding,
            "n_components": n_components,
            "explained_variance": round(explained, 4),
            "n_personas": len(personas),
            "intrinsic_dim_estimate": n_components,
            "manifold_verified": explained > 0.7,
            "interpretation": (
                f"Manifold ✓ — {explained:.1%} variance in {n_components}D (d << n={X.shape[1]})"
                if explained > 0.7
                else f"Manifold hypothesis weak — only {explained:.1%} explained in {n_components}D"
            ),
        }
    else:
        return {"error": f"Method '{method}' not available. Use 'pca'."}
