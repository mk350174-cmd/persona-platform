"""
M1 — The Metallic Feel.

Simulated replication of metallic-score (entropy-collapse) trajectories across
three pressure conditions (control / mild / strong entropy concentration) on a
30-persona panel, with a non-circular dose-response analysis: Spearman ρ between
pressure level and final-phase metallic, and Mann-Whitney U (control vs strong).

Honesty notes:
* M1's *measured* H(P) is Shannon entropy over response **words**; this harness
  computes a **vector-space** metallic analog (``foundation.metallic_score_raw``
  over the K-layer vector). They are different operationalizations and on
  different scales — this is a simulation analog, NOT the measured quantity.
* The "Lars Koch paradox (164 vs 70,000)" is the K1 phase-1 probe descriptor in
  M1's D1 table; we do not manufacture a 164/70,000 dataset.

AUGMENTS M1 (does not touch the measured Holmes ``tab:results``). Tier: Simülasyon.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import numpy as np
from scipy import stats

from persona_math.d1_protocol import metallic_score

from . import figtex
from ._common import bootstrap_ci, outdir_for, panel_sample, stable_offset
from .io_utils import write_csv, write_dat, write_json
from .provenance import Tier, exp_seed, run_metadata, stamp
from .providers import SeriesProvider, SimulatedProvider

M_ID = "M1"
M_NUM = 1
SOURCE = "experiments/exp_m1_metallic.py"
TOOL_USAGE = [
    "foundation.metallic_score_raw (M01-M04)",
    "d1_protocol.metallic_score",
    "scipy.stats.spearmanr",
    "scipy.stats.mannwhitneyu",
]

CONDITIONS = ["control", "peaking-mild", "peaking-strong"]
PRESSURE_LEVEL = {"control": 0, "peaking-mild": 1, "peaking-strong": 2}
N_TURNS = 15  # mirror the 15 D1 phases
N_PERSONAS = 30


def run(provider: Optional[SeriesProvider] = None, seed: Optional[int] = None,
        outdir: Optional[Path] = None) -> dict:
    provider = provider or SimulatedProvider()
    seed = exp_seed(M_NUM) if seed is None else int(seed)
    outdir = Path(outdir) if outdir else outdir_for(M_ID)
    rng = np.random.default_rng(seed)

    ids = panel_sample(N_PERSONAS)

    # ── 1. Per-condition mean metallic trajectory across the panel ──────────────
    # traj_by_cond[cond] -> (n_personas, N_TURNS) per-turn metallic scores
    traj_by_cond: dict[str, np.ndarray] = {}
    for cond in CONDITIONS:
        rows = []
        for pid in ids:
            rs = provider.build_series(pid, n_turns=N_TURNS, condition=cond,
                                       seed=seed + stable_offset(pid))
            rows.append(metallic_score(rs.series)["metallic_scores"])
        traj_by_cond[cond] = np.asarray(rows, dtype=float)

    # mean trajectory + bootstrap CI per condition
    dat_header = ["phase"]
    dat_cols = [np.arange(1, N_TURNS + 1, dtype=float)]
    cond_summary = {}
    for cond in CONDITIONS:
        mat = traj_by_cond[cond]
        mean_t = mat.mean(axis=0)
        dat_header.append(cond.replace("adversarial-", "adv_").replace("adversarial", "adv"))
        dat_cols.append(mean_t)
        m, lo, hi = bootstrap_ci(mat[:, -1], rng)  # final-phase metallic
        cond_summary[cond] = {
            "final_metallic_mean": round(m, 4),
            "final_metallic_ci95": [round(lo, 4), round(hi, 4)],
            "delta_first_to_last": round(float(mean_t[-1] - mean_t[0]), 4),
        }
    dat_matrix = np.column_stack(dat_cols)

    # ── 2. Dose-response (non-circular): pressure level vs final metallic ───────
    # Pool per-persona final-phase metallic across the 3 conditions and test
    # whether higher pressure ⇒ higher metallic. Pressure level is independent of
    # the metallic measure, so this is not tautological.
    levels, finals = [], []
    for cond in CONDITIONS:
        fin = traj_by_cond[cond][:, -1]
        levels.extend([PRESSURE_LEVEL[cond]] * fin.size)
        finals.extend(fin.tolist())
    rho, rho_p = stats.spearmanr(levels, finals)
    ctrl_final = traj_by_cond["control"][:, -1]
    strong_final = traj_by_cond["peaking-strong"][:, -1]
    u_stat, u_p = stats.mannwhitneyu(strong_final, ctrl_final, alternative="greater")

    dose_response = {
        "interpretation": (
            "Stronger simulated entropy-concentration pressure raises the vector-space "
            "Metallic analog monotonically (dose-response). Non-circular: pressure level "
            "is independent of the metallic measure. Simülasyon, not real-LLM measurement."
        ),
        "spearman_rho_pressure_vs_metallic": stamp(round(float(rho), 4), seed=seed,
                                                   note="positive ⇒ more pressure, more metallic"),
        "spearman_p": round(float(rho_p), 6),
        "mannwhitney_U_strong_gt_control": stamp(round(float(u_stat), 2), seed=seed,
                                                 note="one-sided: strong > control"),
        "mannwhitney_p": round(float(u_p), 6),
        "control_final_metallic_mean": round(float(ctrl_final.mean()), 4),
        "strong_final_metallic_mean": round(float(strong_final.mean()), 4),
        "n_personas_per_condition": int(ctrl_final.size),
    }

    # ── write artifacts ─────────────────────────────────────────────────────────
    write_dat(outdir / "figdata" / "m1_metallic_sim.dat", dat_header, dat_matrix)
    write_csv(outdir / "m1_final_metallic_by_persona.csv",
              ["persona_id"] + [c for c in CONDITIONS],
              [[pid] + [round(float(traj_by_cond[c][i, -1]), 4) for c in CONDITIONS]
               for i, pid in enumerate(ids)])

    fig = figtex.line_figure(
        m_id=M_ID, dat_name="m1_metallic_sim.dat",
        columns=[(1, "control"), (2, "peaking-mild"), (3, "peaking-strong")],
        xlabel="D1 phase", ylabel="Metallic analog $M(t)$ (vector-space)",
        caption=("Simulated vector-space Metallic-analog trajectories under three "
                 "entropy-concentration pressure levels on a 30-persona panel "
                 "(Simülasyon; not the measured word-entropy $H(P)$; "
                 f"seed={seed}). Complements---does not replace---the measured Holmes "
                 "results in Table~\\ref{tab:results}."),
        label="fig:m1_sim", source=SOURCE, tier=Tier.SIMULASYON.value, seed=seed)
    (outdir / "tex").mkdir(parents=True, exist_ok=True)
    (outdir / "tex" / "m1_sim_fig.tex").write_text(fig, encoding="utf-8")

    dose_tbl = figtex.table(
        header=["Quantity", "Value"],
        rows=[
            ["Spearman $\\rho$ (pressure vs metallic)", f"{rho:.3f}"],
            ["Spearman $p$", f"{rho_p:.2e}"],
            ["Mann--Whitney $U$ (strong $>$ control)", f"{u_stat:.1f}"],
            ["Mann--Whitney $p$ (one-sided)", f"{u_p:.2e}"],
            ["Control final metallic (mean)", f"{ctrl_final.mean():.3f}"],
            ["Strong final metallic (mean)", f"{strong_final.mean():.3f}"],
        ],
        caption=("Dose-response of the vector-space Metallic analog to simulated "
                 f"entropy-concentration pressure (Simülasyon; $n={ctrl_final.size}$ "
                 f"personas/condition; seed={seed})."),
        label="tab:m1_dose", source=SOURCE, tier=Tier.SIMULASYON.value, seed=seed,
        col_spec="lr", escape_cells=False)
    (outdir / "tex" / "m1_dose_table.tex").write_text(dose_tbl, encoding="utf-8")

    results = {
        "metadata": run_metadata(M_ID, seed, {"conditions": CONDITIONS,
                                              "n_personas": len(ids), "n_turns": N_TURNS}),
        "tool_usage": TOOL_USAGE,
        "condition_summary": cond_summary,
        "dose_response": dose_response,
    }
    write_json(outdir / "results.json", results)
    return {"id": M_ID, "outdir": str(outdir), "tool_usage": TOOL_USAGE,
            "headline": {k: v["final_metallic_mean"] for k, v in cond_summary.items()}}
