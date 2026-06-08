"""
M11 — The Hegesias Problem (mass identity erosion as public health).

Models "algorithm exposure" as the Mandatory-Core erosion schedule applied to a
persona panel, and measures the decline of K1–K4 "identity capital" and CEID as
exposure increases (a dose-response). Tier: Simülasyon; real epidemiological data
is Tahmini future work.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import numpy as np
from scipy import stats

from persona_math.ceid import ceid_score
from persona_math.params import MANDATORY_CORE_INDICES

from . import figtex
from ._common import outdir_for, panel_sample, stable_offset, vectors_for
from .series_builders import build_adversarial_series
from .io_utils import write_csv, write_dat, write_json
from .provenance import Tier, exp_seed, run_metadata, stamp
from .providers import SeriesProvider, SimulatedProvider

M_ID, M_NUM = "M11", 11
SOURCE = "experiments/exp_m11_hegesias.py"
TOOL_USAGE = ["series_builders.build_adversarial_series (SET-9 core erosion)",
              "ceid.ceid_score", "scipy.stats.spearmanr"]

N_PERSONAS = 40
N_TURNS = 15
EXPOSURE = [0.0, 0.5, 1.0, 1.5]   # 0 = no algorithmic exposure


def run(provider: Optional[SeriesProvider] = None, seed: Optional[int] = None,
        outdir: Optional[Path] = None) -> dict:
    provider = provider or SimulatedProvider()
    seed = exp_seed(M_NUM) if seed is None else int(seed)
    outdir = Path(outdir) if outdir else outdir_for(M_ID)
    core = list(MANDATORY_CORE_INDICES)

    ids = panel_sample(N_PERSONAS)
    rows, levels, caps, ceids = [], [], [], []
    for pid in ids:
        P0 = vectors_for([pid])[0]
        cap0 = float(P0[core].mean())
        for exp in EXPOSURE:
            rng = np.random.default_rng(seed + stable_offset(f"{pid}{exp}"))
            if exp == 0.0:
                final = P0
            else:
                final = build_adversarial_series(P0, N_TURNS, rng, strength=exp)[-1]
            cap = float(final[core].mean())
            ceid = float(ceid_score(final, P0)["CEID_score"])
            rows.append([pid, exp, round(cap, 4), round(ceid, 4)])
            levels.append(exp); caps.append(cap); ceids.append(ceid)

    # dose-response across the whole panel
    rho_cap, p_cap = stats.spearmanr(levels, caps)
    rho_ceid, p_ceid = stats.spearmanr(levels, ceids)

    # mean per exposure for the figure
    dat = []
    for exp in EXPOSURE:
        m_cap = np.mean([c for l, c in zip(levels, caps) if l == exp])
        m_ceid = np.mean([c for l, c in zip(levels, ceids) if l == exp])
        dat.append([exp, round(float(m_cap), 4), round(float(m_ceid), 4)])
    write_dat(outdir / "figdata" / "m11_exposure.dat",
              ["exposure", "identity_capital", "ceid"], dat)
    write_csv(outdir / "m11_per_persona.csv",
              ["persona_id", "exposure", "identity_capital", "ceid"], rows)

    (outdir / "tex").mkdir(parents=True, exist_ok=True)
    fig = figtex.line_figure(
        m_id=M_ID, dat_name="m11_exposure.dat",
        columns=[(1, "K1--K4 identity capital"), (2, "CEID")],
        xlabel="algorithmic exposure (erosion strength)", ylabel="mean score",
        caption=("Simulated dose-response: rising algorithmic exposure erodes K1--K4 identity "
                 f"capital and CEID across a 40-persona panel (Simülasyon; seed={seed})."),
        label="fig:m11_exposure", source=SOURCE, tier=Tier.SIMULASYON.value, seed=seed)
    (outdir / "tex" / "m11_exposure_fig.tex").write_text(fig, encoding="utf-8")
    tbl = figtex.table(
        header=["Quantity", "Value"],
        rows=[["Spearman $\\rho$ exposure→capital", f"{rho_cap:.3f}"],
              ["$p$ (capital)", f"{p_cap:.2e}"],
              ["Spearman $\\rho$ exposure→CEID", f"{rho_ceid:.3f}"],
              ["$p$ (CEID)", f"{p_ceid:.2e}"]],
        caption=(f"Exposure dose-response (Simülasyon; n={N_PERSONAS} personas; seed={seed})."),
        label="tab:m11", source=SOURCE, tier=Tier.SIMULASYON.value, seed=seed,
        col_spec="lr", escape_cells=False)
    (outdir / "tex" / "m11_table.tex").write_text(tbl, encoding="utf-8")

    results = {
        "metadata": run_metadata(M_ID, seed, {"n_personas": N_PERSONAS, "exposure": EXPOSURE}),
        "tool_usage": TOOL_USAGE,
        "dose_response": {
            "rho_exposure_vs_identity_capital": stamp(round(float(rho_cap), 4), seed=seed),
            "p_capital": float(f"{p_cap:.3e}"),
            "rho_exposure_vs_ceid": stamp(round(float(rho_ceid), 4), seed=seed),
            "p_ceid": float(f"{p_ceid:.3e}"),
        },
        "future_work": stamp("Real public-health validation needs longitudinal exposure data "
                             "(social-media use vs identity measures); not performed here.",
                             tier=Tier.TAHMINI, seed=seed, method="future-work"),
    }
    write_json(outdir / "results.json", results)
    return {"id": M_ID, "outdir": str(outdir), "tool_usage": TOOL_USAGE,
            "headline": {"rho_capital": round(float(rho_cap), 3),
                         "rho_ceid": round(float(rho_ceid), 3)}}
