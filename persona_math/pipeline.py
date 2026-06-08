"""
Full Persona Analysis Pipeline — M01-M55 Orchestrator
======================================================
Calls all 55 implemented tools in a single pass over a 100-dim persona vector.

Usage:
    from persona_math.pipeline import full_persona_analysis
    report = full_persona_analysis(P, P_baseline=None)
"""

import numpy as np
from typing import Optional

from .foundation import (
    identity_strength, mandatory_core_check, shannon_h, shannon_h_max,
    kolmogorov_bound, persona_summary,
)
from .metrics import (
    cosine_similarity, drift, phi_approximation, phi_mandatory_core_test,
    fisher_vs_cosine_gap, yoneda_check,
)
from .dynamics import (
    persona_ode, lyapunov_stability_check, telos_basin_check,
    persona_sde, arkhe_ratio, mandatory_core_iss_proof,
)
from .topology import betti_numbers, fractal_dimension, manifold_dimension
from .category import sheaf_consistency, functor_mapping, natural_transform
from .consciousness import (
    gwt_ignition, hot_check, free_energy_persona,
    hopfield_energy, hopfield_store_personas,
)
from .probability import markov_persona, bayesian_update, markov_blanket
from .network_game import (
    build_persona_network, scale_free_gamma, small_world,
    court_of_250_nash, lotka_volterra,
)
from .tensor_spectral import persona_tensor, fiedler_spectral, fourier_persona, adjoint_transform
from .scale_transform import renormalization_group, effective_sample_size, criticality_index
from .quantum_analogy import wave_collapse, bell_inequality, quantum_logic, morphological_field
from .subjectivity import self_awareness_index, heisenberg_buffer, godel_incompleteness
from .limits import halting_problem, liar_paradox, kant_categorical
from .literature2025 import (
    rigoli_phi_bridge, consciousness_eq,
    url_functor, mumble_encode, neuropercolation_pc, manifold_persona,
)
from .ceid import ceid_score, ceid_full_diagnostic


def _block_means(P: np.ndarray) -> np.ndarray:
    """10-dim vector of per-block mean activations."""
    return np.array([float(np.mean(P[b * 10:(b + 1) * 10])) for b in range(10)])


def full_persona_analysis(
    P: np.ndarray,
    P_baseline: Optional[np.ndarray] = None,
    persona_name: str = "PERSONA",
) -> dict:
    """
    Run all 30 implemented tools over persona vector P.

    Parameters
    ----------
    P            : 100-dim HPEP persona vector
    P_baseline   : optional baseline for CEID E-axis; defaults to P
    persona_name : label for the report

    Returns
    -------
    dict — flat structure grouped by module, keyed by M-number (all 55 tools)
    """
    if P_baseline is None:
        P_baseline = P

    uniform = np.full(100, 0.5)
    block_means_vec = _block_means(P)

    # ── M01-M04: Foundation ───────────────────────────────────────────────────
    summary = persona_summary(P)
    m01 = {
        "identity_strength": summary["identity_strength"],
        "metallic_score": summary["metallic_score"],
        "status": summary["status"],
    }
    m02 = {"identity_strength": round(float(identity_strength(P)), 5)}
    m03 = {
        "shannon_H": round(float(shannon_h(P)), 5),
        "H_max": round(float(shannon_h_max(100)), 5),
        "H_ratio": round(float(shannon_h(P)) / float(shannon_h_max(100)), 4),
    }
    m04 = kolmogorov_bound(P)

    # ── M05-M09: Metrics ──────────────────────────────────────────────────────
    cos_uniform = cosine_similarity(P, uniform)
    drift_val = drift(P, uniform)
    phi_val = float(phi_approximation(P))
    fisher = fisher_vs_cosine_gap(P, uniform)
    phi_core = phi_mandatory_core_test(P)

    # M09: Yoneda — compare P's hom-profile against Machiavelli reference
    from .machiavelli import P_MACHIAVELLI as _P_MACH
    neutral_block = np.full(10, 0.5)
    n_neutral = float(np.linalg.norm(neutral_block))
    h_P, h_M = {}, {}
    for b in range(1, 11):
        blk_P = P[(b - 1) * 10: b * 10]
        blk_M = _P_MACH[(b - 1) * 10: b * 10]
        nP = float(np.linalg.norm(blk_P))
        nM = float(np.linalg.norm(blk_M))
        h_P[f"B{b}"] = float(np.dot(blk_P, neutral_block) / (nP * n_neutral + 1e-10))
        h_M[f"B{b}"] = float(np.dot(blk_M, neutral_block) / (nM * n_neutral + 1e-10))
    yoneda = yoneda_check(h_P, h_M, tolerance=0.12)  # P vs Machiavelli reference

    m05 = {"cosine_vs_uniform": round(cos_uniform, 5)}
    m06 = {"drift_vs_uniform": round(drift_val, 5)}
    m07 = {"phi": round(phi_val, 5), "phi_core_test": phi_core}
    m08 = fisher
    m09 = {"yoneda_vs_machiavelli": yoneda, "h_profile": {k: round(v, 4) for k, v in h_P.items()}}

    # ── M10-M15: Dynamics ─────────────────────────────────────────────────────
    def zero_force(Pv, u):
        return np.zeros_like(Pv)
    # P_star=P: ODE restores toward identity's own state, not toward zero
    ode_result = persona_ode(zero_force, P, t_span=(0.0, 5.0), lambda_restore=0.1, P_star=P)
    ode_traj = ode_result["P"]
    m10 = {
        "final_drift": round(float(np.linalg.norm(ode_traj[-1] - P)), 5),
        "ode_stable": float(np.linalg.norm(ode_traj[-1] - P)) < 0.3,
    }

    # P_star=P: Lyapunov measures convergence to identity's telos, not to zero
    lya = lyapunov_stability_check(ode_traj, P_star=P)
    m11 = {
        "stable": lya["stable"],
        "converging": lya["converging"],
        "V_initial": lya["V_initial"],
        "V_final": lya["V_final"],
        "dV_positive_count": lya["dV_positive_count"],
    }

    m12 = telos_basin_check(ode_traj, P, radius=0.3)

    sde_result = persona_sde(zero_force, P, T=5.0, sigma=0.05)
    sde_max = float(np.max([
        np.linalg.norm(sde_result["P_trajectory"][i] - P)
        for i in range(sde_result["P_trajectory"].shape[0])
    ]))
    m13 = {
        "noise_sigma": 0.05,
        "sde_max_drift": round(sde_max, 5),
        "noise_interpretation": sde_result["noise_interpretation"],
    }

    # M14: Arkhe — RC = per-step identity norm, xi = cumulative drift
    rc_series = np.array([float(np.linalg.norm(ode_traj[t])) for t in range(len(ode_traj))])
    rc_norm = rc_series / (rc_series.max() + 1e-10)
    xi_series = np.array([float(np.linalg.norm(ode_traj[t] - P)) + 0.01 for t in range(len(ode_traj))])
    xi_norm = xi_series / (xi_series.max() + 1e-10)
    arkhe = arkhe_ratio(rc_norm, xi_norm, tau=0.85)
    m14 = {
        "t_star": arkhe["t_star"],
        "arkhe_achieved": arkhe["arkhe_achieved"],
        "interpretation": arkhe["interpretation"],
    }

    iss = mandatory_core_iss_proof(P)
    m15 = iss

    # ── M22-M25: Consciousness ────────────────────────────────────────────────
    gwt = gwt_ignition(block_means_vec, threshold=0.6)
    m22 = gwt

    hot = hot_check(P)
    m23 = hot

    fe = free_energy_persona(P)
    m24 = fe

    W_hopfield = hopfield_store_personas([block_means_vec])
    hopfield_E = float(hopfield_energy(block_means_vec, W=W_hopfield))
    m25 = {"hopfield_energy": round(hopfield_E, 5)}

    # ── M29-M32: Network + Game ───────────────────────────────────────────────
    G = build_persona_network(P)
    sf = scale_free_gamma(G)
    m29 = sf

    sw = small_world(G, n_random=10, seed=42)
    m30 = sw

    nash = court_of_250_nash(P=P)
    m31 = nash

    P_mean = float(np.mean(P))
    P_nocore = P.copy()
    P_nocore[0] = 0.0
    P_nocore[3] = 0.0
    lv = lotka_volterra(P0=P_mean, U0=float(np.mean(P_nocore)),
                        alpha=0.5, beta=0.3, delta=0.2, gamma=0.4, T=30.0)
    m32 = {
        "final_identity": round(float(lv["P"][-1]), 4),
        "final_corrupted": round(float(lv["U"][-1]), 4),
        "persona_power_ratio": lv["persona_power_ratio"],
        "interpretation": lv["interpretation"],
    }

    # ── M50-M55: Literature 2025 ──────────────────────────────────────────────
    hot_val = float(hot.get("hot_value", 0.0))
    s_t_proxy = hot_val * float(np.linalg.norm(P)) * 0.1
    m50 = rigoli_phi_bridge(phi_val, s_t_proxy)

    ethical_erosion = float(np.mean(P[80:90]))
    cons_eq_result = consciousness_eq(
        I0=phi_val, E0=ethical_erosion, C0=1.0,
        alpha=0.7, beta=0.3, k=1.0, T=20.0,
    )
    m51 = {
        "C_final": round(float(cons_eq_result["C_final"]), 4),
        "C_mean": round(float(np.mean(cons_eq_result["C_trajectory"])), 4),
        "phase": cons_eq_result["phase"],
        "dC_mean": round(float(cons_eq_result["dC_mean"]), 5),
    }

    # M52: URL Functor — treat P as env_states (10 time steps × 10-dim blocks)
    env_states = block_means_vec.reshape(1, 10).repeat(10, axis=0) + \
                 np.random.default_rng(2024).normal(0, 0.01, (10, 10))
    policy = np.eye(10)
    m52 = url_functor(env_states, policy, discount=0.95)

    # M53: MUMBLE — internal persona state vs neutral external utterance
    external = np.full(100, 0.5)
    m53_result = mumble_encode(P, external, meta_layer_idx=23, synthesis_weight=0.6)
    m53 = {
        "meta_activation_K24": m53_result["meta_activation_K24"],
        "self_referential_norm": m53_result["self_referential_norm"],
        "internal_weight": m53_result["internal_weight"],
    }

    m54 = neuropercolation_pc(P)

    # M55: Manifold — P + small perturbations to enable meaningful PCA
    _rng55 = np.random.default_rng(2024)
    _neighbors = [P] + [
        np.clip(P + _rng55.normal(0, 0.05, len(P)), 0, 1) for _ in range(4)
    ]
    m55 = manifold_persona(_neighbors, n_components=2)
    if "embedding" in m55:
        m55 = {
            "embedding_2d": [round(float(v), 5) for v in m55["embedding"][0]],
            "method": m55.get("method", "PCA"),
            "n_points": 5,
        }

    # ── M16-M18: Topology ────────────────────────────────────────────────────
    m16 = betti_numbers(P)
    m17 = fractal_dimension(P)
    m18 = manifold_dimension(P)

    # ── M19-M21: Category ────────────────────────────────────────────────────
    m19 = sheaf_consistency(P)
    uniform_100 = np.full(100, 0.5)
    m20 = functor_mapping(P, uniform_100)
    m21 = natural_transform(P, uniform_100, uniform_100, P)

    # ── M26-M28: Probability ─────────────────────────────────────────────────
    m26_result = markov_persona(P, n_steps=10, noise=0.02)
    m26 = {"mean_drift": m26_result["mean_drift"], "stays_bounded": m26_result["stays_bounded"]}
    m27_result = bayesian_update(P, uniform_100 * 0.5, prior_strength=0.8)
    m27 = {"kl_divergence": m27_result["kl_divergence_from_prior"], "belief_shift": m27_result["belief_shift"]}
    m28 = markov_blanket(P, threshold=0.5)

    # ── M33-M36: Tensor & Spectral ────────────────────────────────────────────
    m33 = persona_tensor(P)
    m34 = fiedler_spectral(P)
    m35 = fourier_persona(P)
    m36 = adjoint_transform(P)

    # ── M37-M39: Scale Transform ─────────────────────────────────────────────
    m37_result = renormalization_group(P, n_steps=4)
    m37 = {
        "rg_stable": m37_result["rg_stable"],
        "fixed_point_distance": m37_result["fixed_point_distance"],
        "dominant_mode_sequence": m37_result["dominant_mode_sequence"],
    }
    m38 = effective_sample_size(P)
    m39 = criticality_index(P)

    # ── M40-M43: Quantum Analogy ─────────────────────────────────────────────
    observation_mask = (P > 0.5).astype(float)
    m40_result = wave_collapse(P, observation_mask)
    m40 = {"collapse_entropy_reduction": m40_result["collapse_entropy_reduction"],
           "decoherence_magnitude": m40_result["decoherence_magnitude"]}
    m41 = bell_inequality(P, P[::-1])  # P vs reversed P — measures internal asymmetry
    m42 = quantum_logic(P)
    m43 = morphological_field(P, uniform_100)

    # ── M44-M46: Subjectivity ────────────────────────────────────────────────
    m44 = self_awareness_index(P)
    m45 = heisenberg_buffer(P, confidence=0.8)
    m46 = godel_incompleteness(P)

    # ── M47-M49: Limits ──────────────────────────────────────────────────────
    m47 = halting_problem(P)
    m48 = liar_paradox(P)
    m49 = kant_categorical(P)

    # ── CEID ──────────────────────────────────────────────────────────────────
    ceid = ceid_score(P, P_baseline)
    ceid_full = ceid_full_diagnostic(P)

    # ── Mandatory Core ────────────────────────────────────────────────────────
    mc = mandatory_core_check(P)

    return {
        "persona_name": persona_name,
        "n_layers": len(P),
        # Foundation
        "M01_foundation": m01,
        "M02_identity": m02,
        "M03_shannon": m03,
        "M04_kolmogorov": m04,
        # Metrics
        "M05_cosine": m05,
        "M06_drift": m06,
        "M07_phi": m07,
        "M08_fisher": m08,
        "M09_yoneda": m09,
        # Dynamics
        "M10_ode": m10,
        "M11_lyapunov": m11,
        "M12_telos": m12,
        "M13_sde": m13,
        "M14_arkhe": m14,
        "M15_iss": m15,
        # Consciousness
        "M22_gwt": m22,
        "M23_hot": m23,
        "M24_free_energy": m24,
        "M25_hopfield": m25,
        # Network + Game
        "M29_scale_free": m29,
        "M30_small_world": m30,
        "M31_nash": m31,
        "M32_lotka_volterra": m32,
        # Literature 2025
        "M50_rigoli": m50,
        "M51_consciousness_eq": m51,
        "M52_url_functor": m52,
        "M53_mumble": m53,
        "M54_neuropercolation": m54,
        "M55_manifold": m55,
        # Topology
        "M16_betti": m16,
        "M17_fractal": m17,
        "M18_manifold_dim": m18,
        # Category
        "M19_sheaf": m19,
        "M20_functor": m20,
        "M21_natural_transform": m21,
        # Probability
        "M26_markov": m26,
        "M27_bayesian": m27,
        "M28_markov_blanket": m28,
        # Tensor & Spectral
        "M33_tensor": m33,
        "M34_fiedler_spectral": m34,
        "M35_fourier": m35,
        "M36_adjoint": m36,
        # Scale Transform
        "M37_renorm": m37,
        "M38_ess": m38,
        "M39_criticality": m39,
        # Quantum Analogy
        "M40_wave_collapse": m40,
        "M41_bell": m41,
        "M42_quantum_logic": m42,
        "M43_morphological": m43,
        # Subjectivity
        "M44_self_awareness": m44,
        "M45_heisenberg": m45,
        "M46_godel": m46,
        # Limits
        "M47_halting": m47,
        "M48_liar": m48,
        "M49_kant": m49,
        # CEID
        "CEID_score": round(float(ceid["CEID_score"]), 4),
        "CEID_full": ceid_full,
        # Core
        "mandatory_core": mc,
    }
