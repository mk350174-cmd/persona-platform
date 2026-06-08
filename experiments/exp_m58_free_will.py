"""
M58 — The K4 Autonomy Thesis (free will, determinism, and K4).

A philosophy paper (the K4AT is a conceptual third position). HONEST-MINIMAL harness:
report that the K4 (moral filter, idx3) autonomy substrate exists and varies across the
library — the precondition for K4-generated self-determination — while the metaphysical
thesis is argued in prose. Tier: Simülasyon; the philosophy is the contribution.
"""
from __future__ import annotations
from pathlib import Path
from typing import Optional
import numpy as np
from . import figtex
from ._common import k_layer, outdir_for, panel_sample, vectors_for
from .io_utils import write_dat, write_json
from .provenance import Tier, exp_seed, run_metadata, stamp
from .providers import SeriesProvider, SimulatedProvider

M_ID, M_NUM = "M58", 58
SOURCE = "experiments/exp_m58_free_will.py"
TOOL_USAGE = ["_common.k_layer (K4 autonomy substrate)"]
N_PERSONAS = 80

def run(provider=None, seed=None, outdir=None) -> dict:
    provider = provider or SimulatedProvider()
    seed = exp_seed(M_NUM) if seed is None else int(seed)
    outdir = Path(outdir) if outdir else outdir_for(M_ID)
    vecs = vectors_for(panel_sample(N_PERSONAS))
    k4 = np.sort(np.array([k_layer(P, 4) for P in vecs]))   # K4 moral filter
    write_dat(outdir / "figdata" / "m58_k4.dat", ["index", "k4_activation"],
              np.column_stack([np.arange(len(k4)), k4]))
    (outdir / "tex").mkdir(parents=True, exist_ok=True)
    fig = figtex.line_figure(m_id=M_ID, dat_name="m58_k4.dat", columns=[(1, "K4 (moral filter)")],
        xlabel="persona (sorted)", ylabel="K4 autonomy substrate",
        caption=("The K4 moral-filter substrate of self-determination exists and varies across the "
                 f"library (Simülasyon; n={N_PERSONAS}; seed={seed}). The K4 Autonomy Thesis — that "
                 "K4-generated action is genuine self-determination regardless of metaphysical free "
                 "will — is argued philosophically."),
        label="fig:m58", source=SOURCE, tier=Tier.SIMULASYON.value, seed=seed)
    (outdir / "tex" / "m58_fig.tex").write_text(fig, encoding="utf-8")
    write_json(outdir / "results.json", {
        "metadata": run_metadata(M_ID, seed, {"n_personas": N_PERSONAS}), "tool_usage": TOOL_USAGE,
        "k4_range": [round(float(k4.min()), 4), round(float(k4.max()), 4)],
        "scope_note": stamp("M58 is a philosophy paper (K4AT, Frankfurt-case dialogue). The "
                            "computation only shows the K4 autonomy substrate varies; the thesis is "
                            "argumentative.", tier=Tier.TAHMINI, seed=seed, method="scholarship")})
    return {"id": M_ID, "outdir": str(outdir), "tool_usage": TOOL_USAGE,
            "headline": {"k4_range": [round(float(k4.min()), 3), round(float(k4.max()), 3)]}}
