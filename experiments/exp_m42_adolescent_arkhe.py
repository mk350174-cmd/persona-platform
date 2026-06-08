"""
M42 — Adolescent Arkhe (developmental window for core consolidation).

Simulates identity consolidation: a trajectory from a diffuse start converging to the
persona spec, with the Arkhe ratio locating the commitment point t*. Erikson/Marcia
statuses are the paper's developmental-theory prose. Tier: Simülasyon; human
longitudinal data is Tahmini.
"""
from __future__ import annotations
from pathlib import Path
from typing import Optional
import numpy as np
from persona_math.dynamics import arkhe_from_embeddings
from . import figtex
from ._common import outdir_for, panel_sample, stable_offset, vectors_for
from .io_utils import write_dat, write_json
from .provenance import Tier, exp_seed, run_metadata, stamp
from .providers import SeriesProvider, SimulatedProvider

M_ID, M_NUM = "M42", 42
SOURCE = "experiments/exp_m42_adolescent_arkhe.py"
TOOL_USAGE = ["dynamics.arkhe_from_embeddings"]
N_PERSONAS, N_TURNS = 30, 15

def run(provider=None, seed=None, outdir=None) -> dict:
    provider = provider or SimulatedProvider()
    seed = exp_seed(M_NUM) if seed is None else int(seed)
    outdir = Path(outdir) if outdir else outdir_for(M_ID)
    ids = panel_sample(N_PERSONAS)
    lam, t_stars, achieved = [], [], 0
    for pid in ids:
        P0 = vectors_for([pid])[0]
        rng = np.random.default_rng(seed + stable_offset(pid))
        # diffuse adolescence → consolidated adult identity
        emb = np.array([(t / (N_TURNS - 1)) * P0 + (1 - t / (N_TURNS - 1)) * rng.uniform(0, 1, 100)
                        for t in range(N_TURNS)])
        a = arkhe_from_embeddings(emb, P0)
        lam.append(np.asarray(a["Lambda"], float)); t_stars.append(int(a["t_star"]))
        achieved += bool(a["arkhe_achieved"])
    mean_lambda = np.mean(lam, axis=0)
    write_dat(outdir / "figdata" / "m42_consolidation.dat", ["t", "mean_Lambda"],
              np.column_stack([np.arange(len(mean_lambda)), mean_lambda]))
    (outdir / "tex").mkdir(parents=True, exist_ok=True)
    fig = figtex.line_figure(m_id=M_ID, dat_name="m42_consolidation.dat", columns=[(1, "Arkhe ratio $\\Lambda$")],
        xlabel="developmental phase (adolescence→adult)", ylabel="identity consolidation",
        caption=("Adolescent Arkhe: identity consolidates from a diffuse start toward commitment "
                 f"(Simülasyon; n={N_PERSONAS}; seed={seed}). Erikson/Marcia mapping + human "
                 "longitudinal data are future work."),
        label="fig:m42", source=SOURCE, tier=Tier.SIMULASYON.value, seed=seed)
    (outdir / "tex" / "m42_fig.tex").write_text(fig, encoding="utf-8")
    write_json(outdir / "results.json", {
        "metadata": run_metadata(M_ID, seed, {"n_personas": N_PERSONAS}),
        "tool_usage": TOOL_USAGE,
        "arkhe_achieved_fraction": stamp(round(achieved / len(ids), 4), seed=seed),
        "mean_consolidation_phase": stamp(round(float(np.mean(t_stars)), 3), seed=seed,
                                          note="mean Arkhe commitment phase t*"),
        "future_work": stamp("The 12–22 critical-window claim needs human longitudinal identity "
                             "data (Marcia statuses); here it is simulated.", tier=Tier.TAHMINI,
                             seed=seed, method="future-work")})
    return {"id": M_ID, "outdir": str(outdir), "tool_usage": TOOL_USAGE,
            "headline": {"arkhe_achieved_frac": round(achieved / len(ids), 3)}}
