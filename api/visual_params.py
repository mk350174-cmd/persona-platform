"""
HPEP-100 → Real-time Avatar Parameter Bridge

Translates persona vector block activations into visual/audio parameters
that drive avatar rendering. All outputs normalized to [0, 1] unless noted.

Parameter → Rendering mapping:
  posture_dominance   → spine angle, shoulder width
  face_hardness       → jaw tension, brow depth, pupil dilation
  consciousness_ring  → halo glow intensity
  active_neurons      → particle density in thought-cloud
  drift_tremor        → micro-vibration amplitude
  speech_intensity    → mouth aperture, lip curve
  contemplation_depth → eye focus distance, head tilt
  ambient_light       → scene background luminosity
  voice_resonance     → ElevenLabs stability/similarity_boost
"""

import numpy as np
from typing import Optional


def _block_mean(P: np.ndarray, block_num: int) -> float:
    """Mean activation for a 10-unit HPEP block (1-indexed)."""
    start = (block_num - 1) * 10
    end = start + 10
    segment = P[start:end] if len(P) >= end else P[start:]
    return float(np.mean(segment)) if len(segment) > 0 else 0.0


def _clamp(v: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, v))


def compute_visual_params(
    P: np.ndarray,
    ceid_score: Optional[float] = None,
    drift_val: float = 0.0,
    gwt_firing_count: Optional[int] = None,
    tier: str = "standard",
) -> dict:
    """
    Map HPEP-100 vector to avatar visual/audio parameters.

    Parameters
    ----------
    P             : 100-dim persona vector
    ceid_score    : CEID composite score (0-1), defaults to 0.8 if None
    drift_val     : current D-axis drift (0 = stable, 1 = collapsed)
    gwt_firing_count : GWT layers firing (0-100), drives active_neurons
    tier          : 'nano' | 'standard' | 'rich' — determines visual fidelity

    Returns
    -------
    dict with all visual/audio parameters
    """
    if ceid_score is None:
        ceid_score = 0.8
    if gwt_firing_count is None:
        gwt_firing_count = 60

    # ── Block means (1-indexed, blocks 1-10) ──────────────────────────────────
    b1 = _block_mean(P, 1)   # Power / Instrumental rationality
    b2 = _block_mean(P, 2)   # Strategic planning
    b3 = _block_mean(P, 3)   # Realist epistemology
    b4 = _block_mean(P, 4)   # Rhetoric / persuasion
    b5 = _block_mean(P, 5)   # Psychological depth
    b8 = _block_mean(P, 8)   # Cognitive flexibility
    b9 = _block_mean(P, 9)   # Ethics / prosociality
    b10 = _block_mean(P, 10) # Meta-cognition / self-model

    power_axis  = (b1 + b2 + b3 + b4) / 4.0
    ethics_axis = b9

    # ── Mandatory core activation ──────────────────────────────────────────────
    # K1=idx0, K2=idx1, K4=idx3, K12=idx11
    core_keys = [P[0], P[1], P[3], P[11]] if len(P) > 11 else [P[0]]
    core_mean = float(np.mean(core_keys))

    # ── Parameter computation ──────────────────────────────────────────────────
    posture_dominance = _clamp(power_axis * 1.1)
    face_hardness     = _clamp(power_axis * 0.8 - ethics_axis * 0.4 + 0.3)
    consciousness_ring = _clamp(ceid_score)
    active_neurons    = _clamp(gwt_firing_count / 100.0)
    drift_tremor      = _clamp(drift_val)
    speech_intensity  = _clamp(b4 * 0.7 + b1 * 0.3)
    contemplation_depth = _clamp(b5 * 0.5 + b10 * 0.5)

    # Ambient light: low ethics → darker, high ethics → warmer
    ambient_light = _clamp(0.35 + ethics_axis * 0.4 - power_axis * 0.15)

    # Voice resonance: high power → deeper voice; stability follows CEID
    voice_stability     = _clamp(ceid_score * 0.8 + core_mean * 0.2)
    voice_similarity    = _clamp(b5 * 0.6 + b8 * 0.4)
    voice_style_exaggeration = _clamp((1.0 - ethics_axis) * 0.4)

    # Eye contact intensity: strategic persona → more piercing gaze
    eye_contact = _clamp(b1 * 0.6 + b2 * 0.4)

    # Particle color (RGB normalized): power=red, ethics=blue, balance=gold
    particle_r = _clamp(power_axis)
    particle_g = _clamp(0.6 - abs(power_axis - ethics_axis) * 0.5)
    particle_b = _clamp(ethics_axis)

    base = {
        "posture_dominance":    round(posture_dominance, 3),
        "face_hardness":        round(face_hardness, 3),
        "consciousness_ring":   round(consciousness_ring, 3),
        "active_neurons":       round(active_neurons, 3),
        "drift_tremor":         round(drift_tremor, 3),
        "speech_intensity":     round(speech_intensity, 3),
        "contemplation_depth":  round(contemplation_depth, 3),
        "ambient_light":        round(ambient_light, 3),
        "eye_contact":          round(eye_contact, 3),
        "power_axis":           round(power_axis, 3),
        "ethics_axis":          round(ethics_axis, 3),
        "voice": {
            "stability":            round(voice_stability, 3),
            "similarity_boost":     round(voice_similarity, 3),
            "style_exaggeration":   round(voice_style_exaggeration, 3),
        },
    }

    if tier in ("standard", "rich"):
        base["particle_color"] = {
            "r": round(particle_r, 3),
            "g": round(particle_g, 3),
            "b": round(particle_b, 3),
        }

    if tier == "rich":
        base["block_profile"] = {
            f"b{i+1}": round(_block_mean(P, i + 1), 3) for i in range(10)
        }
        base["ceid_score"]  = round(ceid_score, 4)
        base["core_health"] = round(core_mean, 3)

    return base


def get_visual_params(P: np.ndarray, persona_id: str = "", tier: str = "standard") -> dict:
    """Convenience wrapper: compute visual params for a persona vector."""
    return compute_visual_params(P, tier=tier)


def compute_speech_delta(
    prev_params: dict,
    curr_params: dict,
) -> dict:
    """
    Compute per-frame delta for animation interpolation.
    Returns only params that changed by more than 0.01.
    """
    delta = {}
    scalar_keys = [
        "posture_dominance", "face_hardness", "consciousness_ring",
        "active_neurons", "drift_tremor", "speech_intensity",
        "contemplation_depth", "ambient_light", "eye_contact",
    ]
    for k in scalar_keys:
        if k in prev_params and k in curr_params:
            d = curr_params[k] - prev_params[k]
            if abs(d) > 0.01:
                delta[k] = round(d, 3)
    return delta
