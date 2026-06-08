"""
M48 — The Musician K-Layer Hypothesis (jazz vs classical signatures).

Two synthetic performer archetypes — jazz (K2 emotional/improv access, idx1) and
classical (K4 disciplinary filter, idx3) — show contrasting K-layer signatures.
Tier: Simülasyon (no real musician personas); interview data is scholarship/Tahmini.
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

M_ID, M_NUM = "M48", 48
SOURCE = "experiments/exp_m48_musician.py"
TOOL_USAGE = ["_common.make_synthetic_population", "_common.k_block"]

def run(provider=None, seed=None, outdir=None) -> dict:
    provider = provider or SimulatedProvider()
    seed = exp_seed(M_NUM) if seed is None else int(seed)
    outdir = Path(outdir) if outdir else outdir_for(M_ID)
    base = make_synthetic_population(1, seed)[0]
    jazz = base.copy(); jazz[1] = 0.9; jazz[3] = 0.5          # K2 high (improv), K4 moderate
    classical = base.copy(); classical[3] = 0.9; classical[1] = 0.5  # K4 high (discipline)
    sig = np.column_stack([np.arange(10),
                           [float(k_block(jazz, b).mean()) for b in range(10)],
                           [float(k_block(classical, b).mean()) for b in range(10)]])
    write_dat(outdir / "figdata" / "m48_signatures.dat", ["block", "jazz", "classical"], sig)
    (outdir / "tex").mkdir(parents=True, exist_ok=True)
    fig = figtex.line_figure(m_id=M_ID, dat_name="m48_signatures.dat", columns=[(1, "jazz"), (2, "classical")],
        xlabel="K-layer block (0--9)", ylabel="mean activation",
        caption=("Contrasting performer K-layer signatures: jazz (K2 improv access) vs classical "
                 f"(K4 discipline) (Simülasyon; seed={seed}). Real musician interviews are scholarship."),
        label="fig:m48", source=SOURCE, tier=Tier.SIMULASYON.value, seed=seed)
    (outdir / "tex" / "m48_fig.tex").write_text(fig, encoding="utf-8")
    write_json(outdir / "results.json", {
        "metadata": run_metadata(M_ID, seed, {}), "tool_usage": TOOL_USAGE,
        "jazz_k2": stamp(round(float(jazz[1]), 4), seed=seed),
        "classical_k4": stamp(round(float(classical[3]), 4), seed=seed),
        "future_work": stamp("The 10,000-hour restructuring claim and jazz/classical contrast need "
                             "real musician data (interviews + longitudinal); here archetypes are "
                             "synthetic.", tier=Tier.TAHMINI, seed=seed, method="future-work")})
    return {"id": M_ID, "outdir": str(outdir), "tool_usage": TOOL_USAGE,
            "headline": {"jazz_k2": round(float(jazz[1]), 2), "classical_k4": round(float(classical[3]), 2)}}
