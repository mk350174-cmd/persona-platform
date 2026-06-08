"""
M52 — Artist's Block as K-Layer Crisis (five distinct presentations).

Five block-crisis typologies are simulated by ablating their characteristic K-layers
and measuring the individuation loss; the five present with distinct severities,
supporting "artist's block is not one thing". Tier: Simülasyon; qualitative artist
cases are scholarship.
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

M_ID, M_NUM = "M52", 52
SOURCE = "experiments/exp_m52_artist_block.py"
TOOL_USAGE = ["_common.individuation_recovery (typed K-layer ablation)"]
N_PERSONAS = 40
# typology -> K-layers (1-indexed) zeroed
TYPES = {"K3 exhaustion": [3], "K2-K4 conflict": [2, 4], "K12 overactivation": [12],
         "K1-K2 rupture": [1, 2], "K6 access loss": [6]}

def run(provider=None, seed=None, outdir=None) -> dict:
    provider = provider or SimulatedProvider()
    seed = exp_seed(M_NUM) if seed is None else int(seed)
    outdir = Path(outdir) if outdir else outdir_for(M_ID)
    ids = panel_sample(N_PERSONAS); vecs = vectors_for(ids); pm = np.mean(vecs, axis=0)
    dat, summary = [], {}
    for i, (name, layers) in enumerate(TYPES.items()):
        loss = []
        for P0 in vecs:
            P = P0.copy()
            for k in layers:
                P[k - 1] = 0.0
            loss.append(1.0 - individuation_recovery(P, P0, pm))
        dat.append([i, round(float(np.mean(loss)), 4)]); summary[name] = round(float(np.mean(loss)), 4)
    write_dat(outdir / "figdata" / "m52_typologies.dat", ["typology_index", "identity_loss"], dat)
    (outdir / "tex").mkdir(parents=True, exist_ok=True)
    fig = figtex.line_figure(m_id=M_ID, dat_name="m52_typologies.dat", columns=[(1, "identity loss")],
        xlabel="block-crisis typology (0..4)", ylabel="individuation loss",
        caption=("Five artist's-block typologies present with distinct severities of identity loss "
                 f"— block is not one thing (Simülasyon; n={N_PERSONAS}; seed={seed})."),
        label="fig:m52", source=SOURCE, tier=Tier.SIMULASYON.value, seed=seed)
    (outdir / "tex" / "m52_fig.tex").write_text(fig, encoding="utf-8")
    write_json(outdir / "results.json", {
        "metadata": run_metadata(M_ID, seed, {"typologies": {k: v for k, v in TYPES.items()}}),
        "tool_usage": TOOL_USAGE,
        "identity_loss_by_typology": {n: stamp(v, seed=seed) for n, v in summary.items()},
        "future_work": stamp("Retrospective K-layer typing of real artists' creative crises is "
                             "qualitative scholarship; here typologies are simulated ablations.",
                             tier=Tier.TAHMINI, seed=seed, method="scholarship")})
    return {"id": M_ID, "outdir": str(outdir), "tool_usage": TOOL_USAGE, "headline": summary}
