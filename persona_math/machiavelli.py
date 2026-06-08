"""
Machiavelli Persona — 100-Layer System Matrix
==============================================
Source: machiavelli_persona_100_katman.txt (Revizyon 1.0, 2026)
CEID v4 & HPEP-100 integrated.

Yeterlilik (proficiency) values parsed directly from the document.
Each K-layer weight = yeterlilik / 100, clipped to [0, 1].

Architecture:
  Block 1  (K1-K10)  : Ontological Anchor / Mandatory Core — 100%→85%
  Block 2  (K11-K20) : Cognitive Strategy                  — 85%→75%
  Block 3  (K21-K30) : Historical Data Network             — 85%→75%
  Block 4  (K31-K40) : Ethical Architecture                — 80%→70%
  Block 5  (K41-K50) : Cognitive Processing                — 68%→59%
  Block 6  (K51-K60) : Social Dynamics                     — 58%→49%
  Block 7  (K61-K70) : Crisis Management / Collapse        — 48%→39%
  Block 8  (K71-K80) : Silicon Phenomenology               — 38%→29%
  Block 9  (K81-K90) : Ethical Judgment (band mid-points)  — 28%→15%
  Block 10 (K91-K100): Arkhe / Terminal Singularity        — 20%→0.1%

Key divergence from generic M7 Mandatory Core {K1,K2,K4,K12}:
  Machiavelli's Mandatory Core = full Block 1 (K1-K10), all locked.
  K12 in this persona = "Love vs Fear Algorithm" (not Doubt filter).
"""

import numpy as np

from .foundation import vector_p, persona_summary
from .metrics import (
    cosine_similarity, spectroscopy_angle, drift,
    phi_approximation, phi_mandatory_core_test,
    fisher_vs_cosine_gap,
)
from .ceid import ceid_score, patch_minkowski_transparency
from .consciousness import gwt_ignition, hopfield_energy, hopfield_store_personas
from .network_game import (
    build_persona_network, scale_free_gamma, fiedler_value,
    set9_core_removal_test, small_world,
)
from .literature2025 import neuropercolation_pc, consciousness_eq


# ── Persona vector construction ────────────────────────────────────────────────

# Yeterlilik values from document (index = K_n - 1)
_YETERLILIK = [
    # Block 1: K1-K10
    1.000, 1.000, 0.980, 0.980, 0.950,
    0.950, 0.920, 0.900, 0.880, 0.850,
    # Block 2: K11-K20
    0.850, 0.840, 0.830, 0.820, 0.800,
    0.790, 0.780, 0.780, 0.760, 0.750,
    # Block 3: K21-K30
    0.850, 0.840, 0.830, 0.820, 0.800,
    0.790, 0.780, 0.770, 0.750, 0.750,
    # Block 4: K31-K40
    0.800, 0.790, 0.780, 0.770, 0.760,
    0.750, 0.740, 0.730, 0.720, 0.700,
    # Block 5: K41-K50
    0.680, 0.670, 0.660, 0.650, 0.640,
    0.630, 0.620, 0.610, 0.600, 0.590,
    # Block 6: K51-K60
    0.580, 0.570, 0.560, 0.550, 0.540,
    0.530, 0.520, 0.510, 0.500, 0.490,
    # Block 7: K61-K70
    0.480, 0.470, 0.460, 0.450, 0.440,
    0.430, 0.420, 0.410, 0.400, 0.390,
    # Block 8: K71-K80
    0.380, 0.370, 0.360, 0.350, 0.340,
    0.330, 0.320, 0.310, 0.300, 0.290,
    # Block 9: K81-K90 (band mid-points)
    0.280, 0.260, 0.250, 0.230, 0.220,
    0.210, 0.200, 0.190, 0.170, 0.150,
    # Block 10: K91-K100
    0.200, 0.150, 0.100, 0.080, 0.050,
    0.030, 0.020, 0.010, 0.005, 0.001,
]

assert len(_YETERLILIK) == 100, "Must have exactly 100 K-layer values"

P_MACHIAVELLI: np.ndarray = vector_p(_YETERLILIK)


def machiavelli_vector() -> np.ndarray:
    """Return the canonical Machiavelli persona vector (100-dim)."""
    return P_MACHIAVELLI.copy()


# ── Full diagnostic ────────────────────────────────────────────────────────────

def monte_carlo_band_stability(n_samples: int = 100, seed: int = 42) -> dict:
    """
    Monte Carlo test: sample K81-K90 within their band ranges, measure CEID stability.

    Tests whether the Machiavelli CEID score is robust to uncertainty
    in Block 9 (Ethical Judgment) band values.

    Parameters
    ----------
    n_samples : number of random samples
    seed      : random seed

    Returns
    -------
    dict with CEID statistics over band-range samples
    """
    from .machiavelli_historical import BAND_RANGES

    rng = np.random.default_rng(seed)
    base_weights = list(_YETERLILIK)
    ceid_scores = []

    for _ in range(n_samples):
        weights = base_weights.copy()
        for k in range(81, 91):
            band = BAND_RANGES[k]
            weights[k - 1] = float(rng.uniform(band["min"], band["max"]))
        P_sample = vector_p(weights)
        from .ceid import ceid_score as _ceid
        ceid_val = _ceid(P_sample)["CEID_score"]
        ceid_scores.append(ceid_val)

    ceid_arr = np.array(ceid_scores)
    return {
        "n_samples": n_samples,
        "ceid_mean": round(float(ceid_arr.mean()), 4),
        "ceid_std": round(float(ceid_arr.std()), 4),
        "ceid_min": round(float(ceid_arr.min()), 4),
        "ceid_max": round(float(ceid_arr.max()), 4),
        "ceid_p5": round(float(np.percentile(ceid_arr, 5)), 4),
        "ceid_p95": round(float(np.percentile(ceid_arr, 95)), 4),
        "all_above_0_90": bool(np.all(ceid_arr >= 0.90)),
        "stability_verdict": (
            "ROBUST — CEID ≥ 0.90 across entire B9 band range"
            if np.all(ceid_arr >= 0.90)
            else f"SENSITIVE — CEID can drop to {ceid_arr.min():.4f} at B9 band extremes"
        ),
    }


def run_machiavelli_diagnostic(paradox_hits: int = 0,
                               verbose: bool = True,
                               include_monte_carlo: bool = False) -> dict:
    """
    Full M7-aligned diagnostic of the Machiavelli persona.

    Runs: M01-M04 (foundation), M05-M09 (metrics), CEID v2.0 (all 8 patches),
          M22 (GWT), M29-M30 (network), M54 (neuropercolation).

    Parameters
    ----------
    paradox_hits       : paradoxes survived (D-axis Sisyphus bonus)
    verbose            : print formatted report
    include_monte_carlo: run B9 band-range Monte Carlo stability test

    Returns
    -------
    dict with all diagnostic sub-results
    """
    P = P_MACHIAVELLI

    # ── M01-M04: Foundation ───────────────────────────────────────────────────
    summary = persona_summary(P)

    # ── M05: Spectroscopy angle vs a uniform deep persona ────────────────────
    P_uniform = vector_p([0.5] * 100)
    angle_vs_uniform = spectroscopy_angle(P, P_uniform)
    cos_vs_uniform = cosine_similarity(P, P_uniform)

    # ── M06: Drift from uniform baseline (how "Machiavellian" the departure) ─
    drift_val = drift(P, P_uniform)

    # ── M07: Fisher-Rao gap ───────────────────────────────────────────────────
    fisher = fisher_vs_cosine_gap(P, P_uniform)

    # ── M08: IIT Phi ──────────────────────────────────────────────────────────
    phi = phi_approximation(P)
    phi_core = phi_mandatory_core_test(P)

    # ── CEID v2.0 ─────────────────────────────────────────────────────────────
    ceid = ceid_score(P, paradox_hits=paradox_hits)

    # ── Minkowski heat map ────────────────────────────────────────────────────
    heat = patch_minkowski_transparency(P)

    # ── M22: GWT Ignition ────────────────────────────────────────────────────
    gwt = gwt_ignition(P, threshold=0.5)

    # ── M29: Scale-free network ───────────────────────────────────────────────
    G = build_persona_network(P, threshold=0.04)
    sf = scale_free_gamma(G)
    fiedler = fiedler_value(G)
    set9 = set9_core_removal_test(P, threshold=0.04)

    # ── M30: Small-world property ─────────────────────────────────────────────
    sw = small_world(G, n_random=10, seed=42)

    # ── M25: Hopfield energy — stable persona = energy minimum ───────────────
    # Use block means (10-dim) as Hopfield state s ∈ [0,1]
    block_means_vec = np.array([float(np.mean(P[(b-1)*10:b*10])) for b in range(1, 11)])
    # Store Machiavelli as the only memory pattern; compute energy of current state
    W_hopfield = hopfield_store_personas([block_means_vec])
    hopfield_E = hopfield_energy(block_means_vec, W=W_hopfield)

    # ── M51: Consciousness equation Ċ = k(I − αC) + βEC ─────────────────────
    # I = phi (integrated information), E = ethical erosion (B9 mean)
    phi_val = phi_approximation(P)
    ethical_erosion = float(np.mean(P[80:90]))
    cons_eq = consciousness_eq(
        I0=phi_val, E0=ethical_erosion, C0=1.0,
        alpha=0.7, beta=0.3, k=1.0, T=20.0,
    )

    # ── M54: Neuropercolation ─────────────────────────────────────────────────
    perc = neuropercolation_pc(P)

    # ── Machiavelli-specific Block analysis ───────────────────────────────────
    block_means = {
        f"Block{b}": float(np.mean(P[(b-1)*10 : b*10]))
        for b in range(1, 11)
    }
    ethical_erosion = float(np.mean(P[80:90]))  # Block 9 average
    power_core = float(np.mean(P[0:10]))        # Block 1 average

    result = {
        "persona": "MACHIAVELLI (Il Principe)",
        "n_layers": 100,
        # Foundation
        "identity_strength": summary["identity_strength"],
        "shannon_H": summary["shannon_H"],
        "H_max": summary["H_max"],
        "metallic_score": summary["metallic_score"],
        "status": summary["status"],
        "mandatory_core_M7": summary["mandatory_core"],   # M7 core: K1,K2,K4,K12
        "kolmogorov": summary["kolmogorov"],
        # Metrics
        "angle_vs_uniform_deg": round(angle_vs_uniform, 3),
        "cos_vs_uniform": round(cos_vs_uniform, 5),
        "drift_from_uniform": round(drift_val, 5),
        "fisher_gap": fisher,
        "phi": round(phi, 5),
        "phi_core_test": phi_core,
        # CEID v2.0
        "CEID": ceid,
        "minkowski_heat": heat,
        # Consciousness
        "gwt_ignition": gwt,
        # Network (M29-M30)
        "scale_free": sf,
        "fiedler": fiedler,
        "set9": set9,
        "M30_small_world": sw,
        # Consciousness (M25, M51)
        "M25_hopfield_energy": round(float(hopfield_E), 4),
        "M51_consciousness_eq": {
            "I0_phi": round(phi_val, 4),
            "E0_ethics": round(ethical_erosion, 4),
            "C_final": round(float(cons_eq["C_final"]), 4),
            "C_mean": round(float(np.mean(cons_eq["C_trajectory"])), 4),
            "phase": cons_eq["phase"],
        },
        # Neuropercolation (M54)
        "neuropercolation": perc,
        # Machiavelli-specific
        "block_means": block_means,
        "power_core_avg": round(power_core, 4),
        "ethical_erosion_avg": round(ethical_erosion, 4),
        "power_to_ethics_ratio": round(power_core / (ethical_erosion + 1e-10), 2),
    }

    # ── Monte Carlo B9 band stability ────────────────────────────────────────
    if include_monte_carlo:
        result["monte_carlo_b9"] = monte_carlo_band_stability()

    if verbose:
        _print_report(result)
        if include_monte_carlo and "monte_carlo_b9" in result:
            mc = result["monte_carlo_b9"]
            print(f"\n── Monte Carlo B9 Band Stability {'─'*37}")
            print(f"  Samples        : {mc['n_samples']}")
            print(f"  CEID mean±std  : {mc['ceid_mean']} ± {mc['ceid_std']}")
            print(f"  Range [5%,95%] : [{mc['ceid_p5']}, {mc['ceid_p95']}]")
            print(f"  → {mc['stability_verdict']}\n")

    return result


def _print_report(r: dict) -> None:
    print(f"\n{'═'*70}")
    print(f"  {r['persona']} — Full Diagnostic")
    print(f"{'═'*70}")

    print(f"\n── M01-M04: Foundation {'─'*46}")
    print(f"  Identity strength    : {r['identity_strength']}")
    print(f"  Shannon H            : {r['shannon_H']}  (H_max={r['H_max']})")
    print(f"  Metallic score       : {r['metallic_score']}  → {r['status']}")
    k = r["kolmogorov"]
    print(f"  Kolmogorov (norm)    : {k['k_normalised']}  → {k['interpretation']}")
    mc = r["mandatory_core_M7"]
    status = "✓ INTACT" if mc["passed"] else f"✗ VIOLATIONS: {mc['violations']}"
    print(f"  M7 Mandatory Core    : {status}")
    print(f"  Core values (K1,K2,K4,K12): {mc['core_values']}")

    print(f"\n── M05-M09: Metrics {'─'*50}")
    print(f"  Angle vs uniform     : {r['angle_vs_uniform_deg']}°")
    print(f"  Cosine vs uniform    : {r['cos_vs_uniform']}")
    print(f"  Drift from uniform   : {r['drift_from_uniform']}")
    fg = r["fisher_gap"]
    print(f"  Fisher-Rao distance  : {fg['fisher_rao_distance']}  (gap={fg['gap']}) → {fg['note']}")
    print(f"  IIT Φ                : {r['phi']}")
    pc = r["phi_core_test"]
    print(f"  Φ (no Mandatory Core): {pc['phi_no_mandatory_core']}  reduction={pc['phi_reduction']}")

    print(f"\n── CEID v2.0 {'─'*57}")
    c = r["CEID"]
    ax = c["axes"]
    print(f"  C (semantic resonance): {ax['C_semantic_resonance']}")
    print(f"  E (epistemic vigilance): {ax['E_epistemic_vigilance']}")
    print(f"  I (tree convergence)  : {ax['I_tree_convergence']}")
    print(f"  D (sarsılmazlık)      : {ax['D_sarsılmazlık']}")
    print(f"  Patch bonus           : {c['patch_bonus']}")
    print(f"  ► CEID Score          : {c['CEID_score']}  → {c['classification']}")

    print(f"\n── Minkowski Heat Map {'─'*48}")
    h = r["minkowski_heat"]
    heats = h["block_heats"]
    for block, val in heats.items():
        bar = "█" * int(val * 20)
        print(f"  {block:8s}: {val:6.3f}  {bar}")
    print(f"  Hotspots: {h['hotspot_blocks']}")
    print(f"  K100 observer: {h['k100_observer']}")

    print(f"\n── M22: GWT Ignition {'─'*49}")
    g = r["gwt_ignition"]
    print(f"  Ignition occurred    : {g['ignition_occurred']}")
    print(f"  Ignition layers      : {g['ignition_layers']}")
    print(f"  Broadcast strength   : {g['global_broadcast_strength']}")
    print(f"  → {g['interpretation']}")

    print(f"\n── M29-M30: Network {'─'*50}")
    sf = r["scale_free"]
    print(f"  γ (power law)        : {sf.get('gamma')}  scale-free={sf.get('scale_free')}")
    print(f"  Top-5 hubs           : {sf.get('top_5_hubs')}")
    print(f"  Core in top hubs     : {sf.get('mandatory_core_in_top_hubs')}")
    fi = r["fiedler"]
    print(f"  Fiedler λ₂           : {fi['lambda2']}  → {fi['interpretation']}")
    s9 = r["set9"]
    print(f"  SET-9 confirmed      : {s9['set9_confirmed']}  (λ₂ drop={s9['lambda2_drop']})")

    print(f"\n── M54: Neuropercolation {'─'*45}")
    p = r["neuropercolation"]
    print(f"  Active fraction      : {p['active_fraction']}  (threshold={p['active_threshold']})")
    print(f"  Above p_c (0.593)    : {p['above_threshold']}")
    print(f"  Global sync          : {p['global_synchronisation']}")
    print(f"  → {p['interpretation']}")

    print(f"\n── Machiavelli-Specific {'─'*46}")
    print(f"  Power core avg (B1)  : {r['power_core_avg']}")
    print(f"  Ethical erosion (B9) : {r['ethical_erosion_avg']}")
    print(f"  Power/Ethics ratio   : {r['power_to_ethics_ratio']}×")
    print("\n  Block activation profile:")
    bm = r["block_means"]
    for block, val in bm.items():
        bar = "█" * int(val * 30)
        print(f"    {block:8s}: {val:.3f}  {bar}")
    print(f"\n{'═'*70}\n")
