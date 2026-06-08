"""
M22 — Physiological Synchrony as Identity Boundary Dissolution.

Models interpersonal "synchrony" as coupling between two persona vectors and
measures how the identity boundary (distinctiveness) softens as coupling rises.
Tier: Simülasyon; real physiological-synchrony data is Tahmini future work.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import numpy as np
from scipy import stats

from persona_math.metrics import cosine_similarity

from . import figtex
from ._common import outdir_for, panel_sample, stable_offset, vectors_for
from .io_utils import write_dat, write_json
from .provenance import Tier, exp_seed, run_metadata, stamp
from .providers import SeriesProvider, SimulatedProvider

M_ID, M_NUM = "M22", 22
SOURCE = "experiments/exp_m22_synchrony.py"
TOOL_USAGE = ["metrics.cosine_similarity", "scipy.stats.spearmanr"]

N_PAIRS = 40
COUPLING = [0.0, 0.2, 0.4, 0.6, 0.8]


def run(provider: Optional[SeriesProvider] = None, seed: Optional[int] = None,
        outdir: Optional[Path] = None) -> dict:
    provider = provider or SimulatedProvider()
    seed = exp_seed(M_NUM) if seed is None else int(seed)
    outdir = Path(outdir) if outdir else outdir_for(M_ID)

    ids = panel_sample(2 * N_PAIRS)
    vecs = vectors_for(ids)
    pairs = [(vecs[2 * i], vecs[2 * i + 1]) for i in range(N_PAIRS)]

    levels, boundaries = [], []
    dat = []
    for c in COUPLING:
        bvals = []
        for A, B in pairs:
            mid = 0.5 * (A + B)
            A_c = (1 - c) * A + c * mid          # A pulled toward the dyad mean
            # identity boundary = how distinct A_c remains from B (1 - cosine)
            bvals.append(1.0 - cosine_similarity(A_c, B))
            levels.append(c); boundaries.append(bvals[-1])
        dat.append([c, round(float(np.mean(bvals)), 4)])
    write_dat(outdir / "figdata" / "m22_synchrony.dat",
              ["coupling", "identity_boundary"], dat)
    rho, p = stats.spearmanr(levels, boundaries)

    (outdir / "tex").mkdir(parents=True, exist_ok=True)
    fig = figtex.line_figure(
        m_id=M_ID, dat_name="m22_synchrony.dat",
        columns=[(1, "identity boundary (1 - cosine)")],
        xlabel="physiological coupling (simulated)", ylabel="identity boundary",
        caption=("As simulated interpersonal coupling rises, the identity boundary between two "
                 f"personas dissolves (Spearman $\\rho={rho:.2f}$; Simülasyon; seed={seed}). Real "
                 "cardiac/respiratory synchrony data is future work."),
        label="fig:m22", source=SOURCE, tier=Tier.SIMULASYON.value, seed=seed)
    (outdir / "tex" / "m22_fig.tex").write_text(fig, encoding="utf-8")

    results = {
        "metadata": run_metadata(M_ID, seed, {"n_pairs": N_PAIRS, "coupling": COUPLING}),
        "tool_usage": TOOL_USAGE,
        "boundary_dissolution": {
            "spearman_rho_coupling_vs_boundary": stamp(round(float(rho), 4), seed=seed,
                                                       note="negative ⇒ more coupling, less boundary"),
            "spearman_p": float(f"{p:.3e}"),
        },
        "future_work": stamp("Physiological synchrony (heart/breath) ↔ identity-boundary data "
                             "from dyadic experiments is required; not available here.",
                             tier=Tier.TAHMINI, seed=seed, method="future-work"),
    }
    write_json(outdir / "results.json", results)
    return {"id": M_ID, "outdir": str(outdir), "tool_usage": TOOL_USAGE,
            "headline": {"rho_coupling_vs_boundary": round(float(rho), 3)}}
