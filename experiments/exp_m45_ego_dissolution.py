"""
M45 — Ego Dissolution as Temporary K1-K4 Suspension.

Models mystical ego-dissolution as suspending the boundary layers K1 (idx0) and K4
(idx3) to varying depth (meditation < prayer < psychedelic) and measures the loss of
individuating identity. Tier: Simülasyon; psychedelic neuroimaging data is Tahmini.
"""
from __future__ import annotations
from pathlib import Path
from typing import Optional
import numpy as np
from . import figtex
from ._common import individuation_recovery, outdir_for, panel_sample, vectors_for
from .io_utils import write_dat, write_json
from .provenance import Tier, exp_seed, run_metadata, stamp
from .providers import SeriesProvider, SimulatedProvider

M_ID, M_NUM = "M45", 45
SOURCE = "experiments/exp_m45_ego_dissolution.py"
TOOL_USAGE = ["_common.individuation_recovery (K1/K4 suspension)"]
N_PERSONAS = 40
PATHWAYS = {"meditation": 0.3, "prayer": 0.6, "psychedelic": 1.0}  # suspension depth

def run(provider=None, seed=None, outdir=None) -> dict:
    provider = provider or SimulatedProvider()
    seed = exp_seed(M_NUM) if seed is None else int(seed)
    outdir = Path(outdir) if outdir else outdir_for(M_ID)
    ids = panel_sample(N_PERSONAS); vecs = vectors_for(ids); pm = np.mean(vecs, axis=0)
    dat = []
    for i, (name, depth) in enumerate(PATHWAYS.items()):
        diss = []
        for P0 in vecs:
            P = P0.copy(); P[0] *= (1 - depth); P[3] *= (1 - depth)   # suspend K1, K4
            diss.append(1.0 - individuation_recovery(P, P0, pm))      # ego boundary loss
        dat.append([i, round(float(np.mean(diss)), 4)])
    write_dat(outdir / "figdata" / "m45_dissolution.dat", ["pathway_index", "ego_dissolution"], dat)
    (outdir / "tex").mkdir(parents=True, exist_ok=True)
    fig = figtex.line_figure(m_id=M_ID, dat_name="m45_dissolution.dat", columns=[(1, "ego dissolution")],
        xlabel="pathway (0 meditation, 1 prayer, 2 psychedelic)", ylabel="boundary dissolution",
        caption=("Ego dissolution as K1/K4 suspension: deeper suspension (psychedelic) dissolves the "
                 f"identity boundary more (Simülasyon; n={N_PERSONAS}; seed={seed}). Psychedelic "
                 "neuroimaging data is future work."),
        label="fig:m45", source=SOURCE, tier=Tier.SIMULASYON.value, seed=seed)
    (outdir / "tex" / "m45_fig.tex").write_text(fig, encoding="utf-8")
    write_json(outdir / "results.json", {
        "metadata": run_metadata(M_ID, seed, {"n_personas": N_PERSONAS, "pathways": PATHWAYS}),
        "tool_usage": TOOL_USAGE,
        "dissolution_by_pathway": {n: round(d[1], 4) for n, d in zip(PATHWAYS, dat)},
        "future_work": stamp("Mapping to real psilocybin/meditation fMRI (Johns Hopkins/Imperial) is "
                             "future work; here suspension is simulated.", tier=Tier.TAHMINI,
                             seed=seed, method="future-work")})
    return {"id": M_ID, "outdir": str(outdir), "tool_usage": TOOL_USAGE,
            "headline": {n: round(d[1], 3) for n, d in zip(PATHWAYS, dat)}}
