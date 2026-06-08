"""
M53 — The Authoritarian Drift Model (4-stage K-layer account).

On Leadership-domain personas, models the four ADM stages as a trajectory where K1
(visible face, idx0) inflates while K4 (moral filter, idx3) collapses under
power-consolidation pressure. Tier: Simülasyon; historical leader cases are scholarship.
"""
from __future__ import annotations
from pathlib import Path
from typing import Optional
import numpy as np
from . import figtex
from ._common import ids_by, outdir_for, stable_offset, vectors_for
from .io_utils import write_dat, write_json
from .provenance import Tier, exp_seed, run_metadata, stamp
from .providers import SeriesProvider, SimulatedProvider

M_ID, M_NUM = "M53", 53
SOURCE = "experiments/exp_m53_authoritarian.py"
TOOL_USAGE = ["K1 inflation / K4 collapse trajectory"]
N_LEADERS, N_STAGES = 30, 4

def run(provider=None, seed=None, outdir=None) -> dict:
    provider = provider or SimulatedProvider()
    seed = exp_seed(M_NUM) if seed is None else int(seed)
    outdir = Path(outdir) if outdir else outdir_for(M_ID)
    ids = ids_by(domain="Leadership", limit=N_LEADERS)
    k1_traj, k4_traj = np.zeros(N_STAGES + 1), np.zeros(N_STAGES + 1)
    for pid in ids:
        P0 = vectors_for([pid])[0]
        rng = np.random.default_rng(seed + stable_offset(pid))
        for s in range(N_STAGES + 1):
            f = s / N_STAGES
            k1_traj[s] += min(1.0, P0[0] + 0.4 * f + rng.normal(0, 0.01))     # K1 inflates
            k4_traj[s] += max(0.0, P0[3] * (1 - f) + rng.normal(0, 0.01))     # K4 collapses
    k1_traj /= len(ids); k4_traj /= len(ids)
    write_dat(outdir / "figdata" / "m53_adm.dat", ["stage", "K1_visible_face", "K4_moral_filter"],
              np.column_stack([np.arange(N_STAGES + 1), k1_traj, k4_traj]))
    (outdir / "tex").mkdir(parents=True, exist_ok=True)
    fig = figtex.line_figure(m_id=M_ID, dat_name="m53_adm.dat",
        columns=[(1, "K1 visible face"), (2, "K4 moral filter")],
        xlabel="ADM stage (0 elected → 4 authoritarian)", ylabel="K-layer activation",
        caption=("Authoritarian Drift Model: across the four stages K1 (visible face) inflates "
                 f"while K4 (moral filter) collapses (Simülasyon; n={N_LEADERS} leaders; seed={seed}). "
                 "Historical cases are scholarship."),
        label="fig:m53", source=SOURCE, tier=Tier.SIMULASYON.value, seed=seed)
    (outdir / "tex" / "m53_fig.tex").write_text(fig, encoding="utf-8")
    write_json(outdir / "results.json", {
        "metadata": run_metadata(M_ID, seed, {"n_leaders": N_LEADERS, "n_stages": N_STAGES}),
        "tool_usage": TOOL_USAGE,
        "K1_final": stamp(round(float(k1_traj[-1]), 4), seed=seed, note="inflated visible face"),
        "K4_final": stamp(round(float(k4_traj[-1]), 4), seed=seed, note="collapsed moral filter"),
        "future_work": stamp("ADM validation needs historical leader case-tracking and institutional "
                             "outcome data; the trajectory here is a stylised simulation.",
                             tier=Tier.TAHMINI, seed=seed, method="scholarship")})
    return {"id": M_ID, "outdir": str(outdir), "tool_usage": TOOL_USAGE,
            "headline": {"K1_final": round(float(k1_traj[-1]), 3), "K4_final": round(float(k4_traj[-1]), 3)}}
