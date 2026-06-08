"""
M2 — Mandatory Core (Topological Stability).

Three simulated/calculated checks on the persona library:
1. Attractor-basin stability — perturb each persona, integrate the restoring ODE,
   and check Lyapunov convergence + telos-basin containment (Simülasyon).
2. SET-9 core removal — zero K1/K4 and measure the Fiedler (λ₂) collapse on each
   persona's interaction graph (Hesaplanan, deterministic).
3. K1–K4 consistency across persona types — mean/std of the Mandatory-Core layers
   per domain (Hesaplanan).

Cross-references M1: a collapsed Mandatory Core is the substrate of the metallic
feel quantified there.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import numpy as np

from persona_math.dynamics import lyapunov_stability_check, persona_ode, telos_basin_check
from persona_math.network_game import set9_core_removal_test
from persona_math.params import MANDATORY_CORE_INDICES

from . import figtex
from ._common import ids_by, outdir_for, stable_offset, vectors_for
from .io_utils import write_csv, write_dat, write_json
from .provenance import Tier, exp_seed, run_metadata, stamp
from .providers import SeriesProvider, SimulatedProvider

M_ID = "M2"
M_NUM = 2
SOURCE = "experiments/exp_m2_mandatory_core.py"
TOOL_USAGE = [
    "dynamics.persona_ode (M10-M15)",
    "dynamics.lyapunov_stability_check (M10-M15)",
    "dynamics.telos_basin_check (M10-M15)",
    "network_game.set9_core_removal_test (M29-M32)",
]

TYPES = ["Philosophy", "Leadership", "Science", "Fiction", "Literature"]
PER_TYPE = 20
CORE_LABELS = {0: "K1", 1: "K2", 3: "K4", 11: "K12"}


def _zero_force(P, u):
    return np.zeros_like(P)


def run(provider: Optional[SeriesProvider] = None, seed: Optional[int] = None,
        outdir: Optional[Path] = None) -> dict:
    provider = provider or SimulatedProvider()  # unused here; kept for interface symmetry
    seed = exp_seed(M_NUM) if seed is None else int(seed)
    outdir = Path(outdir) if outdir else outdir_for(M_ID)

    type_ids = {t: ids_by(domain=t, limit=PER_TYPE) for t in TYPES}
    panel = [(t, pid) for t in TYPES for pid in type_ids[t]]

    # ── 1+2. basin stability + SET-9 per persona ────────────────────────────────
    basin_rows, fiedler_rows = [], []
    n_stable = n_basin = n_set9 = 0
    lambda_drops = []
    for t, pid in panel:
        P0 = vectors_for([pid])[0]
        rng = np.random.default_rng(seed + stable_offset(pid))
        # small within-basin perturbation (σ=0.02/dim ⇒ Euclidean ≈0.2 < basin 0.3)
        P_pert = np.clip(P0 + rng.normal(0.0, 0.02, P0.shape), 0.0, 1.0)
        ode = persona_ode(_zero_force, P_pert, (0.0, 10.0), lambda_restore=0.1, P_star=P0)
        traj = np.asarray(ode["P"])
        lyap = lyapunov_stability_check(traj, P0)
        basin = telos_basin_check(traj, P0)
        s9 = set9_core_removal_test(P0)

        stable = bool(lyap["stable"])
        in_basin = bool(basin["in_telos_basin"])
        confirmed = bool(s9["set9_confirmed"])
        n_stable += stable
        n_basin += in_basin
        n_set9 += confirmed
        lambda_drops.append(float(s9["lambda2_drop"]))

        basin_rows.append([pid, t, stable, in_basin, round(float(s9["lambda2_drop"]), 4),
                           confirmed])
        fiedler_rows.append((round(float(s9["fiedler_full"]), 4),
                             round(float(s9["fiedler_no_core"]), 4)))

    n = len(panel)
    # sort fiedler rows by full value for a readable monotone figure
    fiedler_sorted = sorted(fiedler_rows, key=lambda r: r[0], reverse=True)
    fdat = np.column_stack([np.arange(1, n + 1),
                            [r[0] for r in fiedler_sorted],
                            [r[1] for r in fiedler_sorted]])

    aggregate = {
        "n_personas": n,
        "stable_fraction": stamp(round(n_stable / n, 4), seed=seed,
                                 note="Lyapunov-stable after σ=0.02 within-basin perturbation"),
        "in_basin_fraction": stamp(round(n_basin / n, 4), seed=seed,
                                   note="trajectory stays in telos basin"),
        "set9_confirmed_rate": stamp(round(n_set9 / n, 4), tier=Tier.HESAPLANAN, seed=seed,
                                     note="K1/K4 removal collapses Fiedler λ₂"),
        "mean_lambda2_drop": stamp(round(float(np.mean(lambda_drops)), 4),
                                   tier=Tier.HESAPLANAN, seed=seed),
    }

    # ── 3. K1–K4 consistency by type ────────────────────────────────────────────
    core_idx = list(MANDATORY_CORE_INDICES)
    core_rows = []
    for t in TYPES:
        vecs = np.asarray(vectors_for(type_ids[t]))
        row = [t]
        for idx in core_idx:
            row += [round(float(vecs[:, idx].mean()), 4), round(float(vecs[:, idx].std()), 4)]
        core_rows.append(row)

    # ── write artifacts ─────────────────────────────────────────────────────────
    write_csv(outdir / "m2_basin_stability.csv",
              ["persona_id", "domain", "lyapunov_stable", "in_telos_basin",
               "lambda2_drop", "set9_confirmed"], basin_rows)
    write_dat(outdir / "figdata" / "m2_fiedler_drop.dat",
              ["idx", "fiedler_full", "fiedler_no_core"], fdat)
    core_header = ["domain"] + [f"{CORE_LABELS[i]}_{stat}"
                                for i in core_idx for stat in ("mean", "std")]
    write_csv(outdir / "m2_core_by_type.csv", core_header, core_rows)

    (outdir / "tex").mkdir(parents=True, exist_ok=True)
    fig = figtex.line_figure(
        m_id=M_ID, dat_name="m2_fiedler_drop.dat",
        columns=[(1, "intact core"), (2, "K1/K4 removed (SET-9)")],
        xlabel="persona (sorted by intact $\\lambda_2$)", ylabel="Fiedler value $\\lambda_2$",
        caption=("SET-9 ablation across the persona panel: removing Mandatory-Core layers "
                 "K1/K4 collapses algebraic connectivity $\\lambda_2$ "
                 f"(Hesaplanan; $n={n}$; seed={seed})."),
        label="fig:m2_fiedler", source=SOURCE, tier=Tier.HESAPLANAN.value, seed=seed)
    (outdir / "tex" / "m2_fiedler_fig.tex").write_text(fig, encoding="utf-8")

    core_tbl = figtex.table(
        header=["Domain"] + [f"{CORE_LABELS[i]} (μ±σ)" for i in core_idx],
        rows=[[r[0]] + [f"{r[1 + 2 * j]:.3f}±{r[2 + 2 * j]:.3f}" for j in range(len(core_idx))]
              for r in core_rows],
        caption=("Mandatory-Core layer activations by persona type (μ±σ). Low σ indicates "
                 f"a type-invariant core (Hesaplanan; seed={seed})."),
        label="tab:m2_core", source=SOURCE, tier=Tier.HESAPLANAN.value, seed=seed,
        col_spec="l" + "c" * len(core_idx), escape_cells=False)
    (outdir / "tex" / "m2_core_table.tex").write_text(core_tbl, encoding="utf-8")

    results = {
        "metadata": run_metadata(M_ID, seed, {"types": TYPES, "per_type": PER_TYPE}),
        "tool_usage": TOOL_USAGE,
        "basin_and_set9": aggregate,
        "core_by_type": {r[0]: {CORE_LABELS[core_idx[j]]: {"mean": r[1 + 2 * j],
                                                           "std": r[2 + 2 * j]}
                                for j in range(len(core_idx))} for r in core_rows},
    }
    write_json(outdir / "results.json", results)
    return {"id": M_ID, "outdir": str(outdir), "tool_usage": TOOL_USAGE,
            "headline": {"stable_frac": aggregate["stable_fraction"]["value"],
                         "set9_rate": aggregate["set9_confirmed_rate"]["value"]}}
