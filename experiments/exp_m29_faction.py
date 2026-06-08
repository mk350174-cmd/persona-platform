"""
M29 — Faction Dynamics in Multi-Persona Systems.

Runs the 250-agent court across seeds (reusing M4's simulation) and analyses
coalition formation: the deontological/consequentialist split, its convergence, and
its seed-robustness — the dynamics behind M4's 151/99 equilibrium. Tier: Simülasyon.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import numpy as np

from integrations.autogen_court import run_court_of_250

from . import figtex
from ._common import outdir_for
from .io_utils import write_csv, write_dat, write_json
from .provenance import Tier, exp_seed, run_metadata, stamp
from .providers import SeriesProvider, SimulatedProvider

M_ID, M_NUM = "M29", 29
SOURCE = "experiments/exp_m29_faction.py"
TOOL_USAGE = ["autogen_court.run_court_of_250 (coalition dynamics)"]

N_AGENTS = 250
SEEDS = [42, 101, 202, 303, 404, 505, 606, 707]


def run(provider: Optional[SeriesProvider] = None, seed: Optional[int] = None,
        outdir: Optional[Path] = None) -> dict:
    provider = provider or SimulatedProvider()
    seed = exp_seed(M_NUM) if seed is None else int(seed)
    outdir = Path(outdir) if outdir else outdir_for(M_ID)

    rows, conv, cross = [], [], []
    for s in SEEDS:
        res = run_court_of_250(n_agents=N_AGENTS, n_rounds=4, seed=s)
        cd = res["coalition_dynamics"]
        sim = res["simulation"]
        rows.append([s, sim["n_deontological"], sim["n_consequentialist"],
                     round(float(cd["deontological_convergence"]), 5),
                     round(float(cd["cross_coalition_similarity"]), 5)])
        conv.append(float(cd["deontological_convergence"]))
        cross.append(float(cd["cross_coalition_similarity"]))
    write_csv(outdir / "m29_seed_sweep.csv",
              ["seed", "n_deontological", "n_consequentialist", "convergence",
               "cross_similarity"], rows)
    write_dat(outdir / "figdata" / "m29_coalitions.dat",
              ["seed_index", "convergence", "cross_similarity"],
              np.column_stack([np.arange(len(SEEDS)), conv, cross]))

    (outdir / "tex").mkdir(parents=True, exist_ok=True)
    fig = figtex.line_figure(
        m_id=M_ID, dat_name="m29_coalitions.dat",
        columns=[(1, "deontological convergence"), (2, "cross-coalition similarity")],
        xlabel="seed index", ylabel="coalition metric",
        caption=("Coalition formation across seeds in the 250-agent court: convergence is high and "
                 f"seed-robust, with weak cross-coalition ties (Simülasyon; seed={seed})."),
        label="fig:m29", source=SOURCE, tier=Tier.SIMULASYON.value, seed=seed)
    (outdir / "tex" / "m29_fig.tex").write_text(fig, encoding="utf-8")

    results = {
        "metadata": run_metadata(M_ID, seed, {"n_agents": N_AGENTS, "seeds": SEEDS}),
        "tool_usage": TOOL_USAGE,
        "coalition_convergence_mean": stamp(round(float(np.mean(conv)), 5), seed=seed),
        "coalition_convergence_std": round(float(np.std(conv)), 6),
        "cross_coalition_similarity_mean": stamp(round(float(np.mean(cross)), 5), seed=seed,
                                                 note="weak-tie strength between coalitions"),
    }
    write_json(outdir / "results.json", results)
    return {"id": M_ID, "outdir": str(outdir), "tool_usage": TOOL_USAGE,
            "headline": {"convergence_mean": round(float(np.mean(conv)), 4),
                         "convergence_std": round(float(np.std(conv)), 6)}}
