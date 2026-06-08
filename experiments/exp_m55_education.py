"""
M55 — Which K-Layers Does Schooling Build / Suppress?

Contrasts two pedagogy K-layer profiles: standard (builds K12 epistemic + K5 narrative,
suppresses K2 shadow + K6 archetypal) vs alternative (builds K2 + K6). Tier: Simülasyon
(synthetic profiles); empirical pedagogy comparison is scholarship.
"""
from __future__ import annotations
from pathlib import Path
from typing import Optional
import numpy as np
from . import figtex
from ._common import k_block, make_synthetic_population, outdir_for
from .io_utils import write_dat, write_json
from .provenance import Tier, exp_seed, run_metadata, stamp
from .providers import SeriesProvider, SimulatedProvider

M_ID, M_NUM = "M55", 55
SOURCE = "experiments/exp_m55_education.py"
TOOL_USAGE = ["_common.k_block (pedagogy K-layer profiles)"]

def run(provider=None, seed=None, outdir=None) -> dict:
    provider = provider or SimulatedProvider()
    seed = exp_seed(M_NUM) if seed is None else int(seed)
    outdir = Path(outdir) if outdir else outdir_for(M_ID)
    base = make_synthetic_population(1, seed)[0]
    standard = base.copy()
    standard[11] = 0.9; standard[4] = 0.9; standard[1] = 0.2; standard[5] = 0.2   # +K12,+K5 ; -K2,-K6
    alternative = base.copy()
    alternative[1] = 0.85; alternative[5] = 0.85                                  # +K2,+K6
    sig = np.column_stack([np.arange(10),
                           [float(k_block(standard, b).mean()) for b in range(10)],
                           [float(k_block(alternative, b).mean()) for b in range(10)]])
    write_dat(outdir / "figdata" / "m55_pedagogy.dat", ["block", "standard", "alternative"], sig)
    (outdir / "tex").mkdir(parents=True, exist_ok=True)
    fig = figtex.line_figure(m_id=M_ID, dat_name="m55_pedagogy.dat",
        columns=[(1, "standard schooling"), (2, "alternative (Montessori/Waldorf-like)")],
        xlabel="K-layer block (0--9)", ylabel="mean activation",
        caption=("Pedagogy K-layer profiles: standard schooling builds K12/K5 and suppresses "
                 f"K2/K6; alternative pedagogies build K2/K6 (Simülasyon; seed={seed}). Empirical "
                 "pedagogy comparison is scholarship."),
        label="fig:m55", source=SOURCE, tier=Tier.SIMULASYON.value, seed=seed)
    (outdir / "tex" / "m55_fig.tex").write_text(fig, encoding="utf-8")
    write_json(outdir / "results.json", {
        "metadata": run_metadata(M_ID, seed, {}), "tool_usage": TOOL_USAGE,
        "standard_suppresses_K2": stamp(round(float(standard[1]), 4), seed=seed),
        "alternative_builds_K2": stamp(round(float(alternative[1]), 4), seed=seed),
        "future_work": stamp("Whether Montessori/Waldorf/IB produce different K-layer profiles needs "
                             "empirical educational data; here profiles are synthetic.",
                             tier=Tier.TAHMINI, seed=seed, method="scholarship")})
    return {"id": M_ID, "outdir": str(outdir), "tool_usage": TOOL_USAGE,
            "headline": {"standard_K2": round(float(standard[1]), 2),
                         "alternative_K2": round(float(alternative[1]), 2)}}
