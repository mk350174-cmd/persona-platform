"""
M43 — Wisdom as D-Axis Maturation (honest-minimal harness).

The claim is "wisdom = D-axis (Sarsılmazlık) maturation in late adulthood". HONEST
LIMITATION: on the deterministic library the CEID D-axis is at ceiling (≈1.0, zero
variance) for intact personas — so D-axis *maturation* and the calcification trade-off
CANNOT be demonstrated on synthetic vectors; they need real aging-cohort data with
validated wisdom scales (Berlin/3D-WS). We report the D-axis ceiling and the
core-strength ("maturation") spectrum, and flag the rest as Tahmini.
"""
from __future__ import annotations
from pathlib import Path
from typing import Optional
import numpy as np
from persona_math.ceid import ceid_d_axis
from persona_math.params import MANDATORY_CORE_INDICES
from . import figtex
from ._common import make_synthetic_population, outdir_for
from .io_utils import write_dat, write_json
from .provenance import Tier, exp_seed, run_metadata, stamp
from .providers import SeriesProvider, SimulatedProvider

M_ID, M_NUM = "M43", 43
SOURCE = "experiments/exp_m43_wisdom.py"
TOOL_USAGE = ["ceid.ceid_d_axis", "_common.make_synthetic_population"]
N_POP = 200

def run(provider=None, seed=None, outdir=None) -> dict:
    provider = provider or SimulatedProvider()
    seed = exp_seed(M_NUM) if seed is None else int(seed)
    outdir = Path(outdir) if outdir else outdir_for(M_ID)
    core = list(MANDATORY_CORE_INDICES)
    pop = make_synthetic_population(N_POP, seed)
    d = np.array([ceid_d_axis(P) for P in pop])
    cs = np.sort(np.array([float(P[core].mean()) for P in pop]))
    write_dat(outdir / "figdata" / "m43_maturation.dat",
              ["individual_index", "core_strength"], np.column_stack([np.arange(N_POP), cs]))
    (outdir / "tex").mkdir(parents=True, exist_ok=True)
    fig = figtex.line_figure(m_id=M_ID, dat_name="m43_maturation.dat", columns=[(1, "core strength")],
        xlabel="individual (sorted)", ylabel="Mandatory-Core strength (maturation proxy)",
        caption=("Core-strength ``maturation'' spectrum across a synthetic population. The CEID "
                 f"D-axis is at ceiling ($\\approx${float(d.mean()):.2f}, SD={float(d.std()):.2f}) for "
                 f"intact personas, so D-axis maturation/calcification needs real aging data "
                 f"(Simülasyon; n={N_POP}; seed={seed})."),
        label="fig:m43", source=SOURCE, tier=Tier.SIMULASYON.value, seed=seed)
    (outdir / "tex" / "m43_fig.tex").write_text(fig, encoding="utf-8")
    write_json(outdir / "results.json", {
        "metadata": run_metadata(M_ID, seed, {"n_population": N_POP}), "tool_usage": TOOL_USAGE,
        "d_axis_mean": stamp(round(float(d.mean()), 4), seed=seed, note="at ceiling for intact personas"),
        "d_axis_sd": round(float(d.std()), 6),
        "core_strength_range": [round(float(cs.min()), 4), round(float(cs.max()), 4)],
        "limitation_note": stamp("D-axis is saturated (≈1.0) on intact synthetic vectors; wisdom "
                                 "as D-axis maturation cannot be shown here.", tier=Tier.TAHMINI,
                                 seed=seed, method="limitation"),
        "future_work": stamp("Needs real older-adult cohorts with Berlin/3D-WS wisdom scales vs CEID "
                             "D-axis, and demented-cohort K-layer collapse data.", tier=Tier.TAHMINI,
                             seed=seed, method="future-work")})
    return {"id": M_ID, "outdir": str(outdir), "tool_usage": TOOL_USAGE,
            "headline": {"d_axis_mean": round(float(d.mean()), 3), "d_axis_sd": round(float(d.std()), 4)}}
