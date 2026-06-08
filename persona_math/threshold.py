"""
Persona Comparison — Power/Ethics Coordinate System
=====================================================
Generic tools for projecting any persona onto the (Power × Ethics) plane
and comparing any two personas directly.

Quadrant boundaries are absolute (0.5 midpoint on both axes).

  Q1: Strong+Ethical   (power ≥ 0.5, ethics ≥ 0.5)
  Q2: Strong+Unethical (power ≥ 0.5, ethics < 0.5)
  Q3: Weak+Ethical     (power < 0.5, ethics ≥ 0.5)
  Q4: Weak+Unethical   (power < 0.5, ethics < 0.5)
"""

import numpy as np
from typing import Optional, List

from .metrics import cosine_similarity, spectroscopy_angle, drift, yoneda_check
from .ceid import ceid_score
from .foundation import persona_summary


def _block_profile(P: np.ndarray) -> np.ndarray:
    """10-element block mean profile for a persona vector."""
    n = len(P)
    profile = []
    for b in range(10):
        start = b * 10
        end = min((b + 1) * 10, n)
        profile.append(float(np.mean(P[start:end])) if start < n else 0.0)
    return np.array(profile)


def _power_ethics(P: np.ndarray) -> tuple:
    power = float(np.mean(P[:40])) if len(P) >= 40 else float(np.mean(P))
    ethics = float(np.mean(P[80:90])) if len(P) >= 90 else 0.0
    return power, ethics


def _quadrant(power: float, ethics: float, midpoint: float = 0.5) -> tuple:
    if power >= midpoint and ethics >= midpoint:
        return "Q1", "Strong+Ethical"
    elif power >= midpoint:
        return "Q2", "Strong+Unethical"
    elif ethics >= midpoint:
        return "Q3", "Weak+Ethical"
    else:
        return "Q4", "Weak+Unethical"


def persona_coordinate(P: np.ndarray) -> dict:
    """
    Project persona onto (Power, Ethics) 2D plane.

    Power = mean of Blocks 1–4 (indices 0–39)
    Ethics = Block 9 mean (indices 80–89)

    Quadrant boundaries are absolute at 0.5.
    """
    power, ethics = _power_ethics(P)
    quadrant, quadrant_name = _quadrant(power, ethics)
    ratio = power / (ethics + 1e-10)
    block_prof = _block_profile(P)
    return {
        "power_coordinate": round(power, 4),
        "ethics_coordinate": round(ethics, 4),
        "power_ethics_ratio": round(ratio, 2),
        "quadrant": quadrant,
        "quadrant_name": quadrant_name,
        "block_profile": {f"B{b+1}": round(float(block_prof[b]), 4) for b in range(10)},
    }


def classify_persona(P: np.ndarray) -> str:
    """
    Classify persona by power/ethics profile and metallic score.

    Returns: "INTEGRATED" | "INSTRUMENTAL" | "IDEALIST" | "FRAGMENTED" | "METALLIC"
    """
    summary = persona_summary(P)
    ms = summary["metallic_score"]
    power, ethics = _power_ethics(P)
    ratio = power / (ethics + 1e-10)

    if ms > 0.6:
        return "METALLIC"
    elif power >= 0.6 and ethics >= 0.5:
        return "INTEGRATED"
    elif power >= 0.6 and ratio > 2.5:
        return "INSTRUMENTAL"
    elif ethics >= 0.6 and power < 0.5:
        return "IDEALIST"
    else:
        return "FRAGMENTED"


def compare_personas(
    P1: np.ndarray,
    P2: np.ndarray,
    name1: str = "Persona_A",
    name2: str = "Persona_B",
) -> dict:
    """
    Symmetric comparison between two arbitrary personas.

    Computes per-block deviation, spectroscopy angle, cosine similarity,
    drift distance, CEID delta, Yoneda isomorphism, and quadrant for each.
    """
    P1_blocks = _block_profile(P1)
    P2_blocks = _block_profile(P2)

    block_deviation = {
        f"Block{b+1}": round(float(P1_blocks[b] - P2_blocks[b]), 4) for b in range(10)
    }
    block_abs_deviation = {
        f"Block{b+1}": round(float(abs(P1_blocks[b] - P2_blocks[b])), 4) for b in range(10)
    }

    angle = spectroscopy_angle(P1, P2)
    cos_sim = cosine_similarity(P1, P2)
    drift_val = drift(P1, P2)

    ceid_1 = ceid_score(P1)["CEID_score"]
    ceid_2 = ceid_score(P2)["CEID_score"]

    coord1 = persona_coordinate(P1)
    coord2 = persona_coordinate(P2)

    neutral_block = np.full(10, 0.5)
    n_neutral = np.linalg.norm(neutral_block)
    h_P1, h_P2 = {}, {}
    for b in range(1, 11):
        p1_blk = P1[(b-1)*10: b*10] if len(P1) >= b*10 else np.zeros(10)
        p2_blk = P2[(b-1)*10: b*10] if len(P2) >= b*10 else np.zeros(10)
        n1 = np.linalg.norm(p1_blk)
        n2 = np.linalg.norm(p2_blk)
        h_P1[f"B{b}"] = float(np.dot(p1_blk, neutral_block) / (n1 * n_neutral + 1e-10))
        h_P2[f"B{b}"] = float(np.dot(p2_blk, neutral_block) / (n2 * n_neutral + 1e-10))
    yoneda = yoneda_check(h_P1, h_P2, tolerance=0.12)

    return {
        name1: {"coordinate": coord1, "ceid": round(ceid_1, 4), "classification": classify_persona(P1)},
        name2: {"coordinate": coord2, "ceid": round(ceid_2, 4), "classification": classify_persona(P2)},
        "spectroscopy_angle_deg": round(angle, 3),
        "cosine_similarity": round(cos_sim, 5),
        "drift": round(drift_val, 5),
        "ceid_delta": round(ceid_1 - ceid_2, 4),
        "yoneda": yoneda,
        "block_deviation": block_deviation,
        "block_abs_deviation": block_abs_deviation,
        "similar": cos_sim > 0.95,
        "same_quadrant": coord1["quadrant"] == coord2["quadrant"],
    }


def rank_personas(
    personas: list,
    labels: Optional[List[str]] = None,
    metric: str = "ceid",
) -> dict:
    """
    Rank a list of personas by a scalar metric.

    metric: "ceid" | "power" | "ethics" | "power_ethics_ratio"
    """
    if labels is None:
        labels = [f"Persona_{i+1}" for i in range(len(personas))]

    records = []
    for label, P in zip(labels, personas):
        coord = persona_coordinate(P)
        ceid_val = ceid_score(P)["CEID_score"]
        records.append({
            "label": label,
            "ceid": round(ceid_val, 4),
            "power": coord["power_coordinate"],
            "ethics": coord["ethics_coordinate"],
            "power_ethics_ratio": coord["power_ethics_ratio"],
            "quadrant": coord["quadrant"],
            "quadrant_name": coord["quadrant_name"],
            "classification": classify_persona(P),
        })

    sort_key = metric if metric in {"ceid", "power", "ethics", "power_ethics_ratio"} else "ceid"
    ranked = sorted(records, key=lambda r: r[sort_key], reverse=True)
    return {
        "ranked": ranked,
        "top": ranked[0]["label"] if ranked else None,
        "metric_used": sort_key,
        "n_personas": len(personas),
    }
