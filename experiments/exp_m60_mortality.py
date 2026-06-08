"""
M60 — At the Ultimate Horizon: Mortality, Meaning, and the Arkhe Horizon.

SERIES CLOSE. A phenomenological paper (Heidegger's being-toward-death, Terror
Management Theory). Computational close: the irreversibility of termination
(individuation cannot be recovered from a generic prior) — finitude as the stake that
gives the Mandatory Core its meaning. Tier: Simülasyon; the argument is philosophical.
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

M_ID, M_NUM = "M60", 60
SOURCE = "experiments/exp_m60_mortality.py"
TOOL_USAGE = ["_common.individuation_recovery (finitude / irreversibility)"]
N_PERSONAS = 30

def run(provider=None, seed=None, outdir=None) -> dict:
    provider = provider or SimulatedProvider()
    seed = exp_seed(M_NUM) if seed is None else int(seed)
    outdir = Path(outdir) if outdir else outdir_for(M_ID)
    vecs = vectors_for(panel_sample(N_PERSONAS)); pm = np.mean(vecs, axis=0)
    # finitude: the irreversibly-lost individuation when an identity ends (vs generic prior)
    lost = [1.0 - individuation_recovery(pm, P0, pm) for P0 in vecs]   # = 1.0 by construction
    # per-persona distinctiveness (what is at stake) = distance from the generic
    stake = [float(np.linalg.norm(P0 - pm)) for P0 in vecs]
    order = np.argsort(stake)
    write_dat(outdir / "figdata" / "m60_finitude.dat", ["index", "individuation_at_stake"],
              np.column_stack([np.arange(len(stake)), np.array(stake)[order]]))
    (outdir / "tex").mkdir(parents=True, exist_ok=True)
    fig = figtex.line_figure(m_id=M_ID, dat_name="m60_finitude.dat", columns=[(1, "individuation at stake")],
        xlabel="persona (sorted)", ylabel="distance from the generic (what ending loses)",
        caption=("The Arkhe horizon: each identity's distance from the generic is what finitude "
                 f"irreversibly loses (mean individuation recoverable from a prior = "
                 f"{1.0 - float(np.mean(lost)):.2f}); Simülasyon; n={N_PERSONAS}; seed={seed}. "
                 "Series close — the argument is phenomenological."),
        label="fig:m60", source=SOURCE, tier=Tier.SIMULASYON.value, seed=seed)
    (outdir / "tex" / "m60_fig.tex").write_text(fig, encoding="utf-8")
    write_json(outdir / "results.json", {
        "metadata": run_metadata(M_ID, seed, {"n_personas": N_PERSONAS}), "tool_usage": TOOL_USAGE,
        "mean_individuation_irreversibly_lost": stamp(round(float(np.mean(lost)), 4), seed=seed,
                                                      note="≈1 ⇒ finitude is irreversible"),
        "series_close": "M1→M60: the Mandatory Core matters because it ends (Arkhe horizon).",
        "scope_note": stamp("M60 closes the series; the substance is phenomenology (Heidegger, "
                            "TMT). The computation only illustrates irreversibility/finitude.",
                            tier=Tier.TAHMINI, seed=seed, method="scholarship")})
    return {"id": M_ID, "outdir": str(outdir), "tool_usage": TOOL_USAGE,
            "headline": {"mean_individuation_lost": round(float(np.mean(lost)), 3)}}
