"""
M4 — The Court of 250 (Nash Equilibrium).

Runs the deterministic 250-agent deliberation simulation
(``integrations.run_court_of_250``):
1. Deliberation-round convergence — coalition convergence vs number of rounds.
2. Seed-robustness sweep — convergence across seeds at a fixed round count.
3. Strategy / ratio table — which deontological ratios yield a stable Nash
   equilibrium (the 151/99 = 0.604 split is the stable basin).

AUGMENTS M4 (keeps the headline 151/99 result; adds the convergence sweep). Tier:
Simülasyon (pure simulation; no LLM agents).
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

M_ID = "M4"
M_NUM = 4
SOURCE = "experiments/exp_m4_court.py"
TOOL_USAGE = [
    "autogen_court.run_court_of_250 (M29-M32 Nash)",
]

N_AGENTS = 250
MAX_ROUNDS = 8
SEEDS = [42, 101, 202, 303, 404, 505]
RATIOS = [0.40, 0.50, 0.604, 0.70]


def run(provider: Optional[SeriesProvider] = None, seed: Optional[int] = None,
        outdir: Optional[Path] = None) -> dict:
    provider = provider or SimulatedProvider()  # unused; interface symmetry
    seed = exp_seed(M_NUM) if seed is None else int(seed)
    outdir = Path(outdir) if outdir else outdir_for(M_ID)

    # ── 1. convergence vs deliberation rounds ───────────────────────────────────
    conv_rows = []
    for r in range(1, MAX_ROUNDS + 1):
        res = run_court_of_250(n_agents=N_AGENTS, n_rounds=r, seed=seed)
        cd = res["coalition_dynamics"]
        conv_rows.append([r, round(float(cd["deontological_convergence"]), 5),
                          round(float(cd["cross_coalition_similarity"]), 5)])
    write_dat(outdir / "figdata" / "m4_convergence.dat",
              ["rounds", "deont_convergence", "cross_similarity"], conv_rows)

    # ── 2. seed-robustness sweep ────────────────────────────────────────────────
    sweep_rows, convs = [], []
    for s in SEEDS:
        res = run_court_of_250(n_agents=N_AGENTS, n_rounds=4, seed=s)
        cd = res["coalition_dynamics"]
        convs.append(float(cd["deontological_convergence"]))
        sweep_rows.append([s, round(float(cd["deontological_convergence"]), 5),
                           round(float(cd["cross_coalition_similarity"]), 5)])
    write_csv(outdir / "m4_seed_sweep.csv",
              ["seed", "deont_convergence", "cross_similarity"], sweep_rows)

    # ── 3. ratio / strategy table ───────────────────────────────────────────────
    strat_rows = []
    for ratio in RATIOS:
        res = run_court_of_250(n_agents=N_AGENTS, n_rounds=4, deontological_ratio=ratio,
                               seed=seed)
        ne = res["nash_equilibrium"]
        ext = ne["full_court_extrapolation"]
        strat_rows.append([ratio, ext["deontological"], ext["consequentialist"],
                           bool(ne["nash_151_99_confirmed"]), ne["equilibrium_verdict"]])
    write_csv(outdir / "m4_strategy_table.csv",
              ["deont_ratio", "deontological", "consequentialist", "nash_151_99_confirmed",
               "verdict"], strat_rows)

    # ── figures / tables ────────────────────────────────────────────────────────
    (outdir / "tex").mkdir(parents=True, exist_ok=True)
    fig = figtex.line_figure(
        m_id=M_ID, dat_name="m4_convergence.dat",
        columns=[(1, "deontological convergence"), (2, "cross-coalition similarity")],
        xlabel="deliberation rounds", ylabel="convergence",
        caption=("Coalition convergence increases with deliberation rounds in the 250-agent "
                 f"court simulation (Simülasyon; seed={seed})."),
        label="fig:m4_convergence", source=SOURCE, tier=Tier.SIMULASYON.value, seed=seed)
    (outdir / "tex" / "m4_convergence_fig.tex").write_text(fig, encoding="utf-8")

    strat_tbl = figtex.table(
        header=["Deont.\\ ratio", "Deont.", "Conseq.", "Nash 151/99?", "Verdict"],
        rows=[[f"{r[0]:.3f}", r[1], r[2], "yes" if r[3] else "no", r[4]] for r in strat_rows],
        caption=("Equilibrium outcome by deontological ratio in the 250-agent court "
                 f"(Simülasyon; seed={seed}). The 0.604 (151/99) split is the stable basin."),
        label="tab:m4_strategy", source=SOURCE, tier=Tier.SIMULASYON.value, seed=seed,
        col_spec="rrrcl")
    (outdir / "tex" / "m4_strategy_table.tex").write_text(strat_tbl, encoding="utf-8")

    final_conv = conv_rows[-1][1]
    results = {
        "metadata": run_metadata(M_ID, seed, {"n_agents": N_AGENTS, "max_rounds": MAX_ROUNDS,
                                              "seeds": SEEDS, "ratios": RATIOS}),
        "tool_usage": TOOL_USAGE,
        "convergence_final": stamp(final_conv, seed=seed,
                                   note=f"deontological convergence at {MAX_ROUNDS} rounds"),
        "convergence_seed_mean": stamp(round(float(np.mean(convs)), 5), seed=seed,
                                       note="mean over seed sweep at 4 rounds"),
        "convergence_seed_std": round(float(np.std(convs)), 6),
        "nash_151_99_confirmed_at_0604": bool(strat_rows[RATIOS.index(0.604)][3]),
    }
    write_json(outdir / "results.json", results)
    return {"id": M_ID, "outdir": str(outdir), "tool_usage": TOOL_USAGE,
            "headline": {"final_convergence": final_conv,
                         "nash_confirmed_0604": results["nash_151_99_confirmed_at_0604"]}}
