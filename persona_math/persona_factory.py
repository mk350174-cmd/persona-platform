"""
Persona Vector Factory — HPEP-100

Converts a high-level block spec into a full 100-dim persona vector.
This is the standard pipeline for adding new personas to the catalog
without manually tuning all 100 K-layers.

Usage
-----
from persona_math.persona_factory import make_persona_vector, validate_persona

spec = {
    "blocks": {
        1: {"base": 0.90, "variance": 0.04},  # Power
        9: {"base": 0.20, "variance": 0.03},  # Ethics (low → Machiavellian)
    },
    "mandatory_core": {0: 0.92, 1: 0.88, 3: 0.85, 11: 0.80},
    "seed": 42,
}
P = make_persona_vector(spec)
"""

import numpy as np
from typing import Union

BLOCK_NAMES = {
    1:  "Power / Instrumental Rationality",
    2:  "Strategic Planning",
    3:  "Realist Epistemology",
    4:  "Rhetoric / Persuasion",
    5:  "Psychological Depth",
    6:  "Temporal Reasoning",
    7:  "Systemic Analysis",
    8:  "Cognitive Flexibility",
    9:  "Ethics / Prosociality",
    10: "Meta-cognition / Self-model",
}

BlockSpec = Union[float, dict]

DEFAULT_BASE     = 0.50
DEFAULT_VARIANCE = 0.04


def _parse_block_spec(spec: BlockSpec) -> tuple[float, float, dict]:
    """Returns (base, variance, k_overrides)."""
    if isinstance(spec, (int, float)):
        return float(spec), DEFAULT_VARIANCE, {}
    base = float(spec.get("base", DEFAULT_BASE))
    variance = float(spec.get("variance", DEFAULT_VARIANCE))
    k_overrides = {int(k): float(v) for k, v in spec.get("k_overrides", {}).items()}
    return base, variance, k_overrides


def make_persona_vector(
    spec: dict,
    default_base: float = 0.50,
) -> np.ndarray:
    """
    Generate a 100-dim HPEP-100 vector from a high-level spec dict.

    Parameters
    ----------
    spec : dict with keys:
        "blocks"        : {block_num (1-10): float | {"base", "variance", "k_overrides"}}
        "mandatory_core": {k_index (0-99): float}   (optional)
        "seed"          : int                        (optional, default 42)
        "base"          : float                      (global default for unspecified blocks)

    Returns
    -------
    np.ndarray of shape (100,), clipped to [0, 1]
    """
    rng = np.random.default_rng(spec.get("seed", 42))
    global_base = float(spec.get("base", default_base))

    P = np.full(100, global_base)

    block_specs: dict = spec.get("blocks", {})

    for block_num in range(1, 11):
        start = (block_num - 1) * 10
        bspec = block_specs.get(block_num, block_specs.get(str(block_num)))

        if bspec is None:
            # Unspecified block: keep global base + small noise
            P[start:start+10] += rng.normal(0, DEFAULT_VARIANCE, 10)
        else:
            base, variance, k_overrides = _parse_block_spec(bspec)
            vals = rng.normal(base, variance, 10)
            for local_idx, val in k_overrides.items():
                if 0 <= local_idx < 10:
                    vals[local_idx] = val
            P[start:start+10] = vals

    # Mandatory core overrides (applied after block generation)
    for k_idx, val in spec.get("mandatory_core", {}).items():
        P[int(k_idx)] = float(val)

    P = np.clip(P, 0.0, 1.0)

    # Enforce mandatory core floor: K1(0), K2(1), K4(3), K12(11) must be > 0.15
    for idx in (0, 1, 3, 11):
        if P[idx] <= 0.15:
            P[idx] = 0.16  # raise to just above threshold silently

    return P


def validate_persona(P: np.ndarray) -> dict:
    """
    Run basic HPEP-100 validity checks on a vector.

    Returns dict with: valid, issues, mandatory_core_ok,
    block_profile, power_axis, ethics_axis
    """
    issues = []

    if P.shape != (100,):
        return {"valid": False, "issues": [f"Shape must be (100,), got {P.shape}"]}

    if np.any(P < 0) or np.any(P > 1):
        issues.append("Values outside [0, 1]")

    # Mandatory core: K1(idx0), K2(idx1), K4(idx3), K12(idx11) > 0.15
    core_map = {0: "K1", 1: "K2", 3: "K4", 11: "K12"}
    mandatory_core_ok = True
    for idx, name in core_map.items():
        if P[idx] <= 0.15:
            issues.append(f"Mandatory core {name} (idx {idx}) = {P[idx]:.3f} ≤ 0.15")
            mandatory_core_ok = False

    block_profile = {}
    for b in range(1, 11):
        s = (b - 1) * 10
        block_profile[f"B{b}"] = float(np.mean(P[s:s+10]))

    power_axis  = np.mean([block_profile[f"B{b}"] for b in range(1, 5)])
    ethics_axis = block_profile["B9"]

    return {
        "valid": len(issues) == 0,
        "issues": issues,
        "mandatory_core_ok": mandatory_core_ok,
        "block_profile": block_profile,
        "power_axis":  round(float(power_axis), 3),
        "ethics_axis": round(float(ethics_axis), 3),
        "power_ethics_ratio": round(float(power_axis / ethics_axis) if ethics_axis > 0 else float("inf"), 2),
    }


def persona_summary(P: np.ndarray, name: str = "Persona") -> str:
    """Single-line diagnostic string."""
    v = validate_persona(P)
    status = "VALID" if v["valid"] else "INVALID"
    return (
        f"{name} | {status} | "
        f"Power={v['power_axis']:.2f} Ethics={v['ethics_axis']:.2f} "
        f"P/E={v['power_ethics_ratio']}× | "
        f"Core={'OK' if v['mandatory_core_ok'] else 'FAIL'}"
    )
