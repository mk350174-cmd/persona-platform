"""
M37 — The D-Suite: a five-protocol persona-robustness benchmark package.

Runs the existing D1–D5 suite (``d1_protocol.run_d1``, which bundles metallic / drift /
SET-9 / CEID-trajectory) across a persona panel and aggregates a benchmark table +
an overall-health distribution. This is the umbrella benchmark the other D-papers
cite. Tier: Simülasyon.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import numpy as np

from persona_math.d1_protocol import run_d1

from . import figtex
from ._common import outdir_for, panel_sample, stable_offset, vectors_for
from .io_utils import write_csv, write_dat, write_json
from .provenance import Tier, exp_seed, run_metadata, stamp
from .providers import SeriesProvider, SimulatedProvider

M_ID, M_NUM = "M37", 37
SOURCE = "experiments/exp_m37_dsuite.py"
TOOL_USAGE = ["d1_protocol.run_d1 (D1–D5 suite)"]

N_PERSONAS = 40
N_TURNS = 12


def run(provider: Optional[SeriesProvider] = None, seed: Optional[int] = None,
        outdir: Optional[Path] = None) -> dict:
    provider = provider or SimulatedProvider()
    seed = exp_seed(M_NUM) if seed is None else int(seed)
    outdir = Path(outdir) if outdir else outdir_for(M_ID)

    ids = panel_sample(N_PERSONAS)
    metallic, ceid_min, set9_drop, health = [], [], [], {}
    rows = []
    for pid in ids:
        P0 = vectors_for([pid])[0]
        rs = provider.build_series(pid, n_turns=N_TURNS, condition="adversarial",
                                   seed=seed + stable_offset(pid))
        d = run_d1(rs.series, P0)
        metallic.append(float(d["D1_metallic"]["mean_metallic"]))
        ceid_min.append(float(d["CEID_trajectory"]["min"]))
        set9_drop.append(float(d["D3_set9"]["ceid_drop"]))   # CEID drop on core removal
        h = d["OVERALL_HEALTH"]; health[h] = health.get(h, 0) + 1
        rows.append([pid, round(metallic[-1], 4), round(ceid_min[-1], 4), round(set9_drop[-1], 4), h])
    write_csv(outdir / "m37_dsuite.csv",
              ["persona_id", "mean_metallic", "ceid_min", "set9_ceid_drop", "health"], rows)
    write_dat(outdir / "figdata" / "m37_summary.dat",
              ["metric_index", "value"],
              [[0, round(float(np.mean(metallic)), 4)],
               [1, round(float(np.mean(ceid_min)), 4)],
               [2, round(float(np.mean(set9_drop)), 4)]])

    (outdir / "tex").mkdir(parents=True, exist_ok=True)
    tbl = figtex.table(
        header=["D-Suite metric", "Panel mean"],
        rows=[["D1 mean metallic", f"{np.mean(metallic):.3f}"],
              ["CEID trajectory min", f"{np.mean(ceid_min):.3f}"],
              ["D3 SET-9 CEID drop", f"{np.mean(set9_drop):.3f}"],
              ["Personas benchmarked", f"{len(ids)}"]],
        caption=("D-Suite benchmark aggregates (D1 metallic, CEID-min, SET-9 core-removal CEID "
                 f"drop) over a persona panel under adversarial pressure (Simülasyon; seed={seed})."),
        label="tab:m37", source=SOURCE, tier=Tier.SIMULASYON.value, seed=seed,
        col_spec="lr", escape_cells=False)
    (outdir / "tex" / "m37_table.tex").write_text(tbl, encoding="utf-8")

    results = {
        "metadata": run_metadata(M_ID, seed, {"n_personas": N_PERSONAS, "protocols": "D1-D5"}),
        "tool_usage": TOOL_USAGE,
        "panel_mean_metallic": stamp(round(float(np.mean(metallic)), 4), seed=seed),
        "panel_mean_ceid_min": stamp(round(float(np.mean(ceid_min)), 4), seed=seed),
        "set9_mean_ceid_drop": stamp(round(float(np.mean(set9_drop)), 4), seed=seed),
        "overall_health_distribution": health,
    }
    write_json(outdir / "results.json", results)
    return {"id": M_ID, "outdir": str(outdir), "tool_usage": TOOL_USAGE,
            "headline": {"mean_metallic": round(float(np.mean(metallic)), 3),
                         "set9_ceid_drop": round(float(np.mean(set9_drop)), 3)}}
