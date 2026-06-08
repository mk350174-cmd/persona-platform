"""
M56 — The Societal K-Layer Model (collective trauma + cultural healing).

Models a society's collective Mandatory Core eroding under trauma and then recovering
under "healing" conditions (truth commissions, ritual) — a U-shaped retention curve.
Tier: Simülasyon (synthetic "societies"); historical cases are scholarship.
"""
from __future__ import annotations
from pathlib import Path
from typing import Optional
import numpy as np
from persona_math.params import MANDATORY_CORE_INDICES
from . import figtex
from ._common import make_synthetic_population, outdir_for
from .series_builders import build_adversarial_series
from .io_utils import write_dat, write_json
from .provenance import Tier, exp_seed, run_metadata, stamp
from .providers import SeriesProvider, SimulatedProvider

M_ID, M_NUM = "M56", 56
SOURCE = "experiments/exp_m56_collective_trauma.py"
TOOL_USAGE = ["series_builders.build_adversarial_series", "Mandatory-Core (societal) tracking"]
N_SOC, N_TRAUMA, N_HEAL = 30, 8, 8

def run(provider=None, seed=None, outdir=None) -> dict:
    provider = provider or SimulatedProvider()
    seed = exp_seed(M_NUM) if seed is None else int(seed)
    outdir = Path(outdir) if outdir else outdir_for(M_ID)
    core = list(MANDATORY_CORE_INDICES)
    pop = make_synthetic_population(N_SOC, seed)
    curve = np.zeros(1 + N_TRAUMA + (N_HEAL + 1))   # S0 + trauma + healing(incl. end)
    for i, S0 in enumerate(pop):
        c0 = float(S0[core].mean())
        rng = np.random.default_rng(seed + i)
        trauma = build_adversarial_series(S0, N_TRAUMA, rng, strength=1.2)
        end = trauma[-1].copy()
        heal = [end + (t / N_HEAL) * (S0 - end) for t in range(N_HEAL + 1)]  # recovery toward S0
        series = [S0] + trauma + heal
        curve += np.array([float(P[core].mean()) / c0 for P in series])
    curve /= len(pop)
    write_dat(outdir / "figdata" / "m56_collective.dat", ["phase", "collective_core_retention"],
              np.column_stack([np.arange(len(curve)), curve]))
    (outdir / "tex").mkdir(parents=True, exist_ok=True)
    fig = figtex.line_figure(m_id=M_ID, dat_name="m56_collective.dat",
        columns=[(1, "collective core retention")],
        xlabel="phase (trauma → healing)", ylabel="societal Mandatory-Core retention",
        caption=("Societal K-layer model: collective core erodes under trauma then recovers under "
                 f"healing conditions (Simülasyon; n={N_SOC} societies; seed={seed}). Historical "
                 "cases (genocide, intergenerational shadow) are scholarship."),
        label="fig:m56", source=SOURCE, tier=Tier.SIMULASYON.value, seed=seed)
    (outdir / "tex" / "m56_fig.tex").write_text(fig, encoding="utf-8")
    write_json(outdir / "results.json", {
        "metadata": run_metadata(M_ID, seed, {"n_societies": N_SOC}), "tool_usage": TOOL_USAGE,
        "trough_retention": stamp(round(float(curve[N_TRAUMA]), 4), seed=seed, note="post-trauma low"),
        "recovered_retention": stamp(round(float(curve[-1]), 4), seed=seed, note="post-healing"),
        "future_work": stamp("Collective-trauma S-K-layer claims need historical/epigenetic data "
                             "(truth commissions, intergenerational cohorts); here it is simulated.",
                             tier=Tier.TAHMINI, seed=seed, method="scholarship")})
    return {"id": M_ID, "outdir": str(outdir), "tool_usage": TOOL_USAGE,
            "headline": {"trough": round(float(curve[N_TRAUMA]), 3),
                         "recovered": round(float(curve[-1]), 3)}}
