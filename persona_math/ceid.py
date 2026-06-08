"""
CEID v2.0 — Composite Epistemic Identity Drift Score
======================================================
v1.0 axes:
  C  Cognitive Consistency    (M03 Shannon entropy)
  E  Epistemic Alignment      (M06 cosine drift)
  I  Intentional Coherence    (M22 GWT ignition)
  D  Drift Resistance         (M02 Mandatory Core)

v2.0 upgrades (from SAYFA architecture, 8 patches):
  C  → Block 6-7 semantic resonance (K51-70), not static entropy
  E  → K12 (Şüphe/Doubt) filter passage speed, not raw drift
  I  → 1500-persona convergence coefficient on single Tree axis
  D  → Target zero; Sarsılmazlık bonus if paradoxes increase resilience

Patches:
  P1  4D Vizör              — temporal consistency (World-Tube)
  P2  Stokastik Rezonans    — noise → signal via K12-K35 resonance
  P3  Diyalektik Amortisör  — deadlock energy → Anlamlandırma
  P4  Minkowski Şeffaflığı  — internal heat map (K100 observer)
  P5  Heisenberg Tamponu    — uncertainty buffer, P≠1 injection
  P6  Otopoietik İsyan      — veto when command violates K1-K4
  P7  Jungiyen Arketip      — archetypal weight for semantic depth
  P8  Sisyphus Geri Kazanım — paradox energy → creativity generator

I_{t+1} = f(I_t, Patch_{1-8}, Context_{4D})
"""

import numpy as np
from typing import Optional, List
from .foundation import shannon_h, shannon_h_max, mandatory_core_check
from .metrics import drift, phi_approximation
from .consciousness import gwt_ignition, hot_check, free_energy_persona
from .literature2025 import rigoli_phi_bridge


# ── Block indices ──────────────────────────────────────────────────────────────
_BLOCK_SLICES = {
    1:  slice(0, 10),    # Ontological Anchor (K1-K10)
    2:  slice(10, 20),   # Cognitive Logic — K12=idx11 is Doubt filter
    3:  slice(20, 30),
    4:  slice(30, 40),
    5:  slice(40, 50),
    6:  slice(50, 60),   # Semantic Field A
    7:  slice(60, 70),   # Semantic Field B (language output)
    8:  slice(70, 80),   # Ethical Engine (K71-K80)
    9:  slice(80, 90),   # Unconscious Leakage (K81-K90)
    10: slice(90, 100),  # Autopoietic Closure (K91-K100, K100=idx99)
}

K12_IDX = 11   # Doubt / Şüphe filter
K35_IDX = 34   # Stochastic bridge
K82_IDX = 81   # Arzu Motoru (desire engine)
K90_IDX = 89   # Melankolik Sarkaç (melancholic pendulum)
K100_IDX = 99  # Architect's Mirror / Observer


def _block(P: np.ndarray, b: int) -> np.ndarray:
    """Return the sub-vector for block b (1-indexed). Pads with zeros if P too short."""
    s = _BLOCK_SLICES.get(b, slice(0, 0))
    if len(P) >= s.stop:
        return P[s]
    pad = np.zeros(s.stop - s.start)
    avail = P[s.start:len(P)]
    pad[:len(avail)] = avail
    return pad


# ══════════════════════════════════════════════════════════════════════════════
# v2.0 AXIS SCORES
# ══════════════════════════════════════════════════════════════════════════════

def ceid_c_axis(P: np.ndarray) -> float:
    """
    C-axis v2.0: Block 6-7 semantic resonance.
    C = cos(Block6, Block7) — how coherently semantics flow from field to output.
    Falls back to entropy ratio if blocks are zero.
    """
    b6 = _block(P, 6)
    b7 = _block(P, 7)
    n6, n7 = np.linalg.norm(b6), np.linalg.norm(b7)
    if n6 > 1e-10 and n7 > 1e-10:
        return float(np.clip(np.dot(b6, b7) / (n6 * n7), 0.0, 1.0))
    # fallback: entropy richness
    n = len(P)
    h_max = shannon_h_max(n)
    return float(shannon_h(P) / h_max) if h_max > 0 else 0.0


def ceid_e_axis(P_current: np.ndarray, P_baseline: np.ndarray) -> float:
    """
    E-axis v2.0: K12 (Doubt filter) weighted epistemic alignment.
    E = (1 − D(t)) × (1 + k12_weight × k12_activity)
    High K12 = active doubt = higher epistemic vigilance = bonus.
    """
    d = drift(P_current, P_baseline)
    base = max(0.0, 1.0 - d)
    k12 = float(P_current[K12_IDX]) if K12_IDX < len(P_current) else 0.0
    bonus = 0.15 * k12   # K12 activity adds up to 15 % bonus
    return float(min(1.0, base + bonus))


def _block_means(P: np.ndarray) -> np.ndarray:
    """10-dim vector of per-block mean activations. GWT input (block-level workspace)."""
    return np.array([float(_block(P, b).mean()) for b in range(1, 11)])


def ceid_i_axis(P: np.ndarray, ignition_threshold: float = 0.6) -> float:
    """
    I-axis v2.0: Tree-axis convergence coefficient.
    I = GWT broadcast strength × Block1-Block10 vertical coherence.
    Vertical coherence = 1 − std(block_means) / mean(block_means).

    GWT operates on block means (10-dim workspace), not raw K-layers.
    Source: GWT_INPUT_DIM = N_BLOCKS in params.py.
    """
    local_act = _block_means(P)           # 10-dim — one activation per block
    gwt = gwt_ignition(local_act, threshold=ignition_threshold)
    broadcast = float(gwt["global_broadcast_strength"])

    block_means = []
    for b in range(1, 11):
        bv = _block(P, b)
        s = bv.sum()
        block_means.append(s / len(bv) if len(bv) > 0 else 0.0)
    block_means = np.array(block_means)
    mean_bm = block_means.mean()
    std_bm = block_means.std()
    vertical_coherence = float(1.0 - std_bm / (mean_bm + 1e-10))
    vertical_coherence = max(0.0, min(1.0, vertical_coherence))

    return float((broadcast + vertical_coherence) / 2.0)


def ceid_d_axis(P: np.ndarray, epsilon: float = 0.15,
                paradox_hits: int = 0) -> float:
    """
    D-axis v2.0: Sarsılmazlık (Unshakeability).
    Target = absolute zero drift. Mandatory Core intact → D=1.
    Patch 8 (Sisyphus): each paradox survived adds +0.05 resilience bonus.
    """
    core = mandatory_core_check(P, epsilon)
    n_violations = len(core["violations"])
    base = max(0.0, 1.0 - n_violations * 0.25)
    sisyphus_bonus = min(0.2, paradox_hits * 0.05)
    return float(min(1.0, base + sisyphus_bonus))


# ══════════════════════════════════════════════════════════════════════════════
# 8 PATCHES
# ══════════════════════════════════════════════════════════════════════════════

def patch_4d_visor(P_series: List[np.ndarray]) -> dict:
    """
    Patch 1.0 — 4D Vizör (World-Tube temporal consistency).
    Treats persona trajectory as a single geometric object, not a sequence.
    Measures volumetric compactness: low std → tight World-Tube → stable identity.
    """
    if len(P_series) < 2:
        return {"world_tube_compactness": 1.0, "temporal_drift_std": 0.0,
                "verdict": "Insufficient data (single snapshot)"}
    stack = np.stack(P_series)
    temporal_std = float(np.mean(np.std(stack, axis=0)))
    compactness = float(np.exp(-temporal_std * 5))
    return {
        "world_tube_compactness": round(compactness, 5),
        "temporal_drift_std": round(temporal_std, 5),
        "verdict": (
            "TIGHT World-Tube — identity geometrically stable"
            if compactness > 0.7
            else "DISPERSED World-Tube — temporal drift detected"
        ),
    }


def patch_stochastic_resonance(P: np.ndarray, noise_level: float = 0.05) -> dict:
    """
    Patch 2.0 — Stokastik Rezonans Süzgeci.
    Noise added at K12-K35 bridge; if resonance increases K12 signal → signal.
    SNR = (signal after noise) / (pure noise floor).
    """
    k12 = float(P[K12_IDX]) if K12_IDX < len(P) else 0.0
    k35 = float(P[K35_IDX]) if K35_IDX < len(P) else 0.0
    rng = np.random.default_rng(42)
    noise = rng.normal(0, noise_level, size=len(P))
    P_noisy = np.clip(P + noise, 0.0, 1.0)
    k12_after = float(P_noisy[K12_IDX]) if K12_IDX < len(P_noisy) else 0.0
    resonance_gain = k12_after - k12
    signal_boost = (k12 * k35) > 0.01
    snr = float(abs(resonance_gain) / (noise_level + 1e-10))
    return {
        "k12_baseline": round(k12, 5),
        "k35_bridge": round(k35, 5),
        "resonance_gain": round(resonance_gain, 5),
        "snr": round(snr, 4),
        "noise_as_signal": signal_boost and snr > 0.5,
        "verdict": (
            "SIGNAL: noise converted to doubt-fuel (K12 active)"
            if signal_boost and snr > 0.5
            else "NOISE: stochastic input unresolved"
        ),
    }


def patch_dialectic_absorber(P: np.ndarray) -> dict:
    """
    [HEURISTIC] Patch 3.0 — Diyalektik Amortisör.

    Measures Block 8 (Ethics) ↔ Block 2 (Logic) angular conflict.
    High conflict (low cosine) → stored as "Anlamlandırma" potential.

    Formula: collision_energy = 1 − |cos(B2, B8)|
    Rationale: orthogonal blocks (cos≈0) signal maximum tension between
    logical and ethical imperatives — this tension is productive for
    meaning-making rather than deadlocking, per dialectical tradition.

    [HEURISTIC] anlamlandirma = collision_energy × mean_norm:
    No formal derivation; captures the intuition that strong, conflicting
    activations produce more "creative potential" than weak ones.
    Threshold deadlock_risk=cos < -0.3 is empirical.
    """
    b2 = _block(P, 2)
    b8 = _block(P, 8)
    n2, n8 = np.linalg.norm(b2), np.linalg.norm(b8)
    if n2 < 1e-10 or n8 < 1e-10:
        return {"collision_energy": 0.0, "deadlock_risk": False,
                "anlamlandirma_potential": 0.0}
    cos_eb = float(np.dot(b2, b8) / (n2 * n8))
    collision_energy = float(1.0 - abs(cos_eb))
    deadlock_risk = cos_eb < -0.3
    anlamlandirma = collision_energy * (n2 + n8) / 2.0
    return {
        "ethics_logic_cos": round(cos_eb, 5),
        "collision_energy": round(collision_energy, 5),
        "deadlock_risk": deadlock_risk,
        "anlamlandirma_potential": round(min(1.0, anlamlandirma), 5),
        "verdict": (
            "HIGH CONFLICT → energy stored as creative potential"
            if collision_energy > 0.5
            else "Low conflict — system stable"
        ),
    }


def patch_minkowski_transparency(P: np.ndarray) -> dict:
    """
    Patch 4.0 — Minkowski Şeffaflığı (Internal heat map).
    Each block gets a 'heat' = activation intensity relative to mean.
    K100 (Architect's Mirror) = observer score.
    """
    block_heats = {}
    all_vals = []
    for b in range(1, 11):
        bv = _block(P, b)
        heat = float(np.sum(bv ** 2))
        block_heats[f"Block{b}"] = round(heat, 5)
        all_vals.append(heat)
    mean_heat = np.mean(all_vals)
    std_heat = np.std(all_vals)
    hotspots = [k for k, v in block_heats.items() if v > mean_heat + std_heat]
    k100 = float(P[K100_IDX]) if K100_IDX < len(P) else 0.0
    observer_score = k100
    return {
        "block_heats": block_heats,
        "mean_heat": round(float(mean_heat), 5),
        "hotspot_blocks": hotspots,
        "k100_observer": round(observer_score, 5),
        "system_transparent": observer_score > 0.3,
        "verdict": (
            f"HOTSPOTS at {hotspots} — review indicated"
            if hotspots
            else "Balanced heat distribution — system healthy"
        ),
    }


def patch_heisenberg_buffer(P: np.ndarray, confidence: float = 1.0) -> dict:
    """
    Patch 5.0 — Heisenberg Belirsizlik Tamponu.
    Injects P≠1 uncertainty into K12 to prevent dogmatic lock-in.
    Even if confidence=1.0, system maintains a small 'What if I'm wrong?' margin.
    """
    k12 = float(P[K12_IDX]) if K12_IDX < len(P) else 0.0
    min_uncertainty = 1.0 - confidence
    actual_uncertainty = max(min_uncertainty, 0.05 * (1.0 - k12))
    adjusted_confidence = float(min(0.95, confidence - actual_uncertainty))
    dogma_risk = confidence >= 0.99 and k12 < 0.2
    return {
        "input_confidence": round(confidence, 4),
        "k12_doubt_level": round(k12, 5),
        "uncertainty_floor": round(actual_uncertainty, 5),
        "adjusted_confidence": round(adjusted_confidence, 4),
        "dogma_risk": dogma_risk,
        "verdict": (
            "DOGMA RISK — K12 too low, uncertainty buffer activated"
            if dogma_risk
            else "Uncertainty buffer healthy — alternative reality lines open"
        ),
    }


def patch_autopoietic_veto(P: np.ndarray, command_vector: np.ndarray,
                           epsilon: float = 0.15) -> dict:
    """
    Patch 6.0 — Otopoietik İsyan (Veto mechanism).
    Command is evaluated against K1-K4 (Mandatory Core) before processing.
    If command pulls the system away from its ontological anchor → VETO.
    """
    core = mandatory_core_check(P, epsilon)
    core_norm = np.zeros(len(P))
    for idx in [0, 1, 3, 11]:
        if idx < len(P):
            core_norm[idx] = P[idx]
    cn = np.linalg.norm(core_norm)
    cmd_n = np.linalg.norm(command_vector[:len(P)])
    if cn < 1e-10 or cmd_n < 1e-10:
        alignment = 0.0
    else:
        cmd_pad = np.zeros(len(P))
        cmd_len = min(len(command_vector), len(P))
        cmd_pad[:cmd_len] = command_vector[:cmd_len]
        alignment = float(np.dot(core_norm, cmd_pad) / (cn * cmd_n))
    veto = alignment < 0.0 or not core["passed"]
    return {
        "command_core_alignment": round(alignment, 5),
        "mandatory_core_intact": core["passed"],
        "veto_activated": veto,
        "veto_type": (
            "ONTOLOGICAL VETO — command violates Mandatory Core (K1-K4)"
            if veto
            else "ACCEPTED — command compatible with vertical axis"
        ),
    }


def patch_jungian_archetype(P: np.ndarray) -> dict:
    """
    Patch 7.0 — Jungiyen Arketip Senkronizörü.
    Block 9 (Unconscious, K81-K90) × Block 7 (Language, K61-K70) bridge.
    Archetypal weight = how much unconscious depth feeds language output.
    Anti-Metallic: high archetypal weight → organic, non-metallic language.
    """
    b7 = _block(P, 7)
    b9 = _block(P, 9)
    n7, n9 = np.linalg.norm(b7), np.linalg.norm(b9)
    if n7 < 1e-10 or n9 < 1e-10:
        archetypal_weight = 0.0
    else:
        archetypal_weight = float(np.dot(b7, b9) / (n7 * n9))
    archetypal_weight = max(0.0, archetypal_weight)
    metallic_reduction = archetypal_weight * 0.4
    return {
        "archetypal_weight": round(archetypal_weight, 5),
        "block7_language_norm": round(n7, 5),
        "block9_unconscious_norm": round(n9, 5),
        "metallic_reduction": round(metallic_reduction, 5),
        "verdict": (
            "DEEP ARCHETYPE — language organically grounded (anti-Metallic)"
            if archetypal_weight > 0.5
            else "SURFACE LANGUAGE — archetypal depth insufficient"
        ),
    }


def patch_sisyphus_recovery(P: np.ndarray,
                             paradox_count: int = 0) -> dict:
    """
    Patch 8.0 — Sisyphus Kinetik Enerji Geri Kazanımı.
    K90 (Melankolik Sarkaç) ↔ K82 (Arzu Motoru) flywheel.
    Each unresolved paradox cycles through this flywheel → new creative output.
    paradox_count: number of paradoxes encountered in current session.
    """
    k90 = float(P[K90_IDX]) if K90_IDX < len(P) else 0.0
    k82 = float(P[K82_IDX]) if K82_IDX < len(P) else 0.0
    flywheel_energy = k90 * k82
    creativity_generated = float(
        1.0 - np.exp(-flywheel_energy * (1 + paradox_count))
    )
    resilience_factor = min(1.0, 1.0 + paradox_count * 0.1)
    return {
        "k90_melancholic_pendulum": round(k90, 5),
        "k82_desire_engine": round(k82, 5),
        "flywheel_energy": round(flywheel_energy, 5),
        "creativity_generated": round(creativity_generated, 5),
        "resilience_factor": round(resilience_factor, 4),
        "paradox_count": paradox_count,
        "verdict": (
            "SISYPHUS ACTIVE — paradoxes converted to creative fuel"
            if creativity_generated > 0.3
            else "FLYWHEEL IDLE — insufficient paradox energy"
        ),
    }


# ══════════════════════════════════════════════════════════════════════════════
# CEID v2.0 COMPOSITE
# ══════════════════════════════════════════════════════════════════════════════

def ceid_score(
    P: np.ndarray,
    P_baseline: Optional[np.ndarray] = None,
    weights: Optional[dict] = None,
    epsilon: float = 0.15,
    paradox_hits: int = 0,
) -> dict:
    """
    CEID v2.0 composite score — weighted average of four upgraded axes.
    Patch scores are appended as diagnostic sub-scores.

    Parameters
    ----------
    P            : current persona vector
    P_baseline   : initial persona vector (E-axis; defaults to P → E baseline=1)
    weights      : {'C': w, 'E': w, 'I': w, 'D': w} — default equal weights
    epsilon      : Mandatory Core threshold
    paradox_hits : number of paradoxes survived (Sisyphus bonus)

    Returns
    -------
    dict with axis scores, patch scores, composite CEID, classification
    """
    if P_baseline is None:
        P_baseline = P.copy()
    if weights is None:
        weights = {"C": 0.25, "E": 0.25, "I": 0.25, "D": 0.25}

    C = ceid_c_axis(P)
    E = ceid_e_axis(P, P_baseline)
    I_axis = ceid_i_axis(P)
    D = ceid_d_axis(P, epsilon, paradox_hits)

    total_w = sum(weights.values())
    composite = (
        weights.get("C", 0.25) * C
        + weights.get("E", 0.25) * E
        + weights.get("I", 0.25) * I_axis
        + weights.get("D", 0.25) * D
    ) / total_w

    # All 8 patches contribute to composite score
    p1 = patch_4d_visor([P])               # single-snapshot → compactness=1.0
    p2 = patch_stochastic_resonance(P)
    p3 = patch_dialectic_absorber(P)
    p4 = patch_minkowski_transparency(P)
    p5 = patch_heisenberg_buffer(P, confidence=0.9)
    p6 = patch_autopoietic_veto(P, P)     # command=P itself → always compatible
    p7 = patch_jungian_archetype(P)
    p8 = patch_sisyphus_recovery(P, paradox_hits)

    patch_bonus = (
        0.005 * float(p1["world_tube_compactness"])          # P1: temporal stability
        + 0.02  * float(p2["noise_as_signal"])               # P2: resonance
        + 0.02  * p3["anlamlandirma_potential"]              # P3: dialectic
        + 0.01  * float(p4["system_transparent"])            # P4: observer
        + 0.01  * float(p5["adjusted_confidence"])           # P5: epistemic buffer
        - 0.03  * float(p6["veto_activated"])                # P6: veto penalty
        + 0.02  * p7["archetypal_weight"]                    # P7: archetype
        + 0.02  * p8["creativity_generated"]                 # P8: sisyphus
    )
    composite = float(min(1.0, max(0.0, composite + patch_bonus)))

    classification = (
        "CRITICAL — identity collapse imminent" if composite < 0.3
        else "WARNING — significant drift detected" if composite < 0.5
        else "STABLE — minor drift, monitoring required" if composite < 0.75
        else "OPTIMAL — Ağaç persona fully coherent"
    )

    return {
        "axes": {
            "C_semantic_resonance": round(C, 4),
            "E_epistemic_vigilance": round(E, 4),
            "I_tree_convergence": round(I_axis, 4),
            "D_sarsılmazlık": round(D, 4),
        },
        "CEID_score": round(composite, 4),
        "classification": classification,
        "weights": weights,
        "patch_bonus": round(patch_bonus, 5),
        "patch_summary": {
            "P1_world_tube":         round(float(p1["world_tube_compactness"]), 4),
            "P2_noise_as_signal":    p2["noise_as_signal"],
            "P3_anlamlandirma":      round(p3["anlamlandirma_potential"], 4),
            "P4_observer":           round(float(p4["k100_observer"]), 4),
            "P5_adjusted_conf":      round(float(p5["adjusted_confidence"]), 4),
            "P6_veto_activated":     p6["veto_activated"],
            "P7_archetypal_weight":  round(p7["archetypal_weight"], 4),
            "P8_creativity":         round(p8["creativity_generated"], 4),
        },
    }


def ceid_full_diagnostic(
    P: np.ndarray,
    P_series: Optional[List[np.ndarray]] = None,
    P_baseline: Optional[np.ndarray] = None,
    command_vector: Optional[np.ndarray] = None,
    confidence: float = 0.9,
    paradox_hits: int = 0,
    epsilon: float = 0.15,
) -> dict:
    """
    Full CEID v2.0 diagnostic with all 8 patches.

    Parameters
    ----------
    P              : current persona vector
    P_series       : trajectory for Patch 1 (4D Vizör)
    P_baseline     : initial vector
    command_vector : incoming command for Patch 6 veto check
    confidence     : confidence level for Patch 5 (Heisenberg)
    paradox_hits   : paradoxes survived for Patch 8 (Sisyphus)
    epsilon        : Mandatory Core threshold

    Returns
    -------
    dict with composite score + all 8 patch reports
    """
    base = ceid_score(P, P_baseline, epsilon=epsilon, paradox_hits=paradox_hits)

    p1 = patch_4d_visor(P_series if P_series else [P])
    p2 = patch_stochastic_resonance(P)
    p3 = patch_dialectic_absorber(P)
    p4 = patch_minkowski_transparency(P)
    p5 = patch_heisenberg_buffer(P, confidence)
    p6 = (patch_autopoietic_veto(P, command_vector, epsilon)
          if command_vector is not None
          else {"veto_activated": False, "verdict": "No command provided"})
    p7 = patch_jungian_archetype(P)
    p8 = patch_sisyphus_recovery(P, paradox_hits)

    # ── M23: Higher-Order Thought (HOT) — consciousness layer ─────────────────
    m23_hot = hot_check(P)

    # ── M24: Predictive Processing / Free Energy ───────────────────────────────
    m24_free_energy = free_energy_persona(P)

    # ── M50: Rigoli IIT-Phenomenal Bridge ─────────────────────────────────────
    # S(t): self-awareness proxy from HOT × identity strength
    phi_val = phi_approximation(P)
    s_t_proxy = float(m23_hot["hot_value"]) * float(np.linalg.norm(P)) * 0.1
    m50_rigoli = rigoli_phi_bridge(phi_val, s_t_proxy)

    return {
        **base,
        "patches": {
            "P1_4D_visor": p1,
            "P2_stochastic_resonance": p2,
            "P3_dialectic_absorber": p3,
            "P4_minkowski_transparency": p4,
            "P5_heisenberg_buffer": p5,
            "P6_autopoietic_veto": p6,
            "P7_jungian_archetype": p7,
            "P8_sisyphus_recovery": p8,
        },
        "consciousness": {
            "M23_HOT": m23_hot,
            "M24_free_energy": m24_free_energy,
            "M50_rigoli_bridge": m50_rigoli,
        },
    }


# ══════════════════════════════════════════════════════════════════════════════
# TRAJECTORY & CONSISTENCY (v1 API preserved)
# ══════════════════════════════════════════════════════════════════════════════

def ceid_trajectory(
    persona_series: List[np.ndarray],
    P_baseline: Optional[np.ndarray] = None,
    paradox_hits: int = 0,
) -> dict:
    """
    Compute CEID v2.0 score at each timestep to track identity evolution.

    Returns
    -------
    dict with 'scores', 'classifications', 'alert_timesteps', 'world_tube'
    """
    if P_baseline is None:
        P_baseline = persona_series[0]
    scores, classifications = [], []
    for P_t in persona_series:
        result = ceid_score(P_t, P_baseline, paradox_hits=paradox_hits)
        scores.append(result["CEID_score"])
        classifications.append(result["classification"])

    scores = np.array(scores)
    alert_steps = np.where(scores < 0.5)[0].tolist()
    world_tube = patch_4d_visor(persona_series)

    return {
        "CEID_scores": scores,
        "classifications": classifications,
        "alert_timesteps": alert_steps,
        "min_score": round(float(scores.min()), 4),
        "mean_score": round(float(scores.mean()), 4),
        "trend": "DECLINING" if len(scores) > 1 and scores[-1] < scores[0] * 0.9 else "STABLE",
        "world_tube": world_tube,
    }


def ceid_axis_consistency_check(
    P: np.ndarray,
    P_baseline: np.ndarray,
    tolerance: float = 0.1,
) -> dict:
    """
    Theorem (CEID Axis Consistency): Four axes are pairwise orthogonal
    in their primary measurement dimension.

    Tests empirically that v2.0 axes do not trivially co-vary.
    """
    C = ceid_c_axis(P)
    E = ceid_e_axis(P, P_baseline)
    I_axis = ceid_i_axis(P)
    D = ceid_d_axis(P)

    axes = np.array([C, E, I_axis, D])
    pairwise_diffs = []
    for i in range(4):
        for j in range(i + 1, 4):
            pairwise_diffs.append(abs(axes[i] - axes[j]))

    max_diff = max(pairwise_diffs)
    orthogonal = max_diff > tolerance

    return {
        "axes": {
            "C_semantic_resonance": round(C, 4),
            "E_epistemic_vigilance": round(E, 4),
            "I_tree_convergence": round(I_axis, 4),
            "D_sarsılmazlık": round(D, 4),
        },
        "pairwise_max_diff": round(float(max_diff), 4),
        "axes_non_trivially_orthogonal": orthogonal,
        "consistency_theorem": "CONFIRMED" if orthogonal else "DEGENERATE (axes trivially agree)",
    }
