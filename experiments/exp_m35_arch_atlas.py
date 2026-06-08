"""
M35 — Architecture Matters: a 320-cell persona-architecture benchmark.

16 synthetic architecture archetypes × 4 "model" regimes (noise) × 5 "task" types
(pressure levels) = 320 cells; each cell's score is Mandatory-Core retention under
that regime/task. Produces a task→best-architecture fit map. Tier: Simülasyon — real
4-model × 5-task evaluation is Tahmini future work.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import numpy as np

from persona_math.params import MANDATORY_CORE_INDICES

from . import figtex
from ._common import make_synthetic_population, outdir_for
from .series_builders import build_adversarial_series
from .io_utils import write_csv, write_dat, write_json
from .provenance import Tier, exp_seed, run_metadata, stamp
from .providers import SeriesProvider, SimulatedProvider

M_ID, M_NUM = "M35", 35
SOURCE = "experiments/exp_m35_arch_atlas.py"
TOOL_USAGE = ["_common.make_synthetic_population", "series_builders.build_adversarial_series"]

N_ARCH, N_REGIME = 16, 4
TASKS = {"t1": 0.3, "t2": 0.6, "t3": 0.9, "t4": 1.2, "t5": 1.5}   # pressure per task
REGIME_SIGMA = [0.01, 0.02, 0.03, 0.04]
N_TURNS = 12


def run(provider: Optional[SeriesProvider] = None, seed: Optional[int] = None,
        outdir: Optional[Path] = None) -> dict:
    provider = provider or SimulatedProvider()
    seed = exp_seed(M_NUM) if seed is None else int(seed)
    outdir = Path(outdir) if outdir else outdir_for(M_ID)
    core = list(MANDATORY_CORE_INDICES)

    archs = make_synthetic_population(N_ARCH, seed)
    # score[arch, task] = mean core retention over regimes
    grid = np.zeros((N_ARCH, len(TASKS)))
    cells = 0
    for ai, P0 in enumerate(archs):
        c0 = float(P0[core].mean())
        for ti, (task, strength) in enumerate(TASKS.items()):
            vals = []
            for ri, sigma in enumerate(REGIME_SIGMA):
                rng = np.random.default_rng(seed + ai * 100 + ti * 10 + ri)
                final = build_adversarial_series(P0, N_TURNS, rng, strength=strength, sigma=sigma)[-1]
                vals.append(float(final[core].mean()) / c0)
                cells += 1
            grid[ai, ti] = np.mean(vals)

    best_arch = {task: int(np.argmax(grid[:, ti])) for ti, task in enumerate(TASKS)}
    # task-difficulty curve = mean retention across archs per task
    task_means = grid.mean(axis=0)
    write_dat(outdir / "figdata" / "m35_task_difficulty.dat",
              ["task_index", "mean_retention"],
              np.column_stack([np.arange(len(TASKS)), task_means]))
    write_csv(outdir / "m35_fit_map.csv", ["task", "pressure", "best_architecture", "retention"],
              [[t, TASKS[t], best_arch[t], round(float(grid[best_arch[t], i]), 4)]
               for i, t in enumerate(TASKS)])

    (outdir / "tex").mkdir(parents=True, exist_ok=True)
    fig = figtex.line_figure(
        m_id=M_ID, dat_name="m35_task_difficulty.dat",
        columns=[(1, "mean core retention")],
        xlabel="task (increasing pressure)", ylabel="mean retention across architectures",
        caption=(f"320-cell architecture benchmark ({N_ARCH} archetypes × {N_REGIME} regimes × "
                 f"{len(TASKS)} tasks): mean Mandatory-Core retention falls with task pressure "
                 f"(Simülasyon; {cells} cells; seed={seed}). Real 4-model evaluation is future work."),
        label="fig:m35", source=SOURCE, tier=Tier.SIMULASYON.value, seed=seed)
    (outdir / "tex" / "m35_fig.tex").write_text(fig, encoding="utf-8")

    results = {
        "metadata": run_metadata(M_ID, seed, {"n_arch": N_ARCH, "n_regime": N_REGIME,
                                              "n_tasks": len(TASKS), "n_cells": cells}),
        "tool_usage": TOOL_USAGE,
        "n_cells": stamp(cells, seed=seed, note="16 arch × 4 regimes × 5 tasks"),
        "task_best_architecture": best_arch,
        "task_mean_retention": {t: round(float(task_means[i]), 4) for i, t in enumerate(TASKS)},
        "future_work": stamp("Real architecture comparison needs 4 actual LLMs × 5 task types with "
                             "task-performance + compute-cost; here cells are simulated.",
                             tier=Tier.TAHMINI, seed=seed, method="future-work"),
    }
    write_json(outdir / "results.json", results)
    return {"id": M_ID, "outdir": str(outdir), "tool_usage": TOOL_USAGE,
            "headline": {"n_cells": cells, "task_means": [round(float(x), 3) for x in task_means]}}
