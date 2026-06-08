"""
M38 — Distributed Inference and Persona Stability.

Models quantization / substrate fragmentation as lossy transfer at decreasing
fidelity (F16 > Q8 > Q4) and measures individuation-recovery + Mandatory-Core
retention. Tier: Simülasyon; the real 3-device experiment (M4 MacBook / Honor Pad /
Samsung A35) data would be supplied by the author (Tahmini here).
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import numpy as np

from persona_math.params import MANDATORY_CORE_INDICES

from . import figtex
from ._common import (individuation_recovery, lossy_transfer, outdir_for, panel_sample,
                      stable_offset, vectors_for)
from .io_utils import write_dat, write_json
from .provenance import Tier, exp_seed, run_metadata, stamp
from .providers import SeriesProvider, SimulatedProvider

M_ID, M_NUM = "M38", 38
SOURCE = "experiments/exp_m38_distributed.py"
TOOL_USAGE = ["_common.lossy_transfer", "_common.individuation_recovery"]

N_PERSONAS = 40
QUANT = {"F16": 0.95, "Q8": 0.80, "Q4": 0.60}   # effective fidelity per quantization


def run(provider: Optional[SeriesProvider] = None, seed: Optional[int] = None,
        outdir: Optional[Path] = None) -> dict:
    provider = provider or SimulatedProvider()
    seed = exp_seed(M_NUM) if seed is None else int(seed)
    outdir = Path(outdir) if outdir else outdir_for(M_ID)
    core = list(MANDATORY_CORE_INDICES)

    ids = panel_sample(N_PERSONAS)
    vecs = vectors_for(ids)
    pop_mean = np.mean(vecs, axis=0)

    dat = []
    summary = {}
    for i, (q, fidelity) in enumerate(QUANT.items()):
        indiv, core_ret = [], []
        for pid, P0 in zip(ids, vecs):
            rng = np.random.default_rng(seed + stable_offset(f"{pid}{q}"))
            copy = lossy_transfer(P0, fidelity, rng)
            indiv.append(individuation_recovery(copy, P0, pop_mean))
            core_ret.append(float(copy[core].mean()) / float(P0[core].mean()))
        dat.append([i, round(float(np.mean(indiv)), 4), round(float(np.mean(core_ret)), 4)])
        summary[q] = {"individuation": round(float(np.mean(indiv)), 4),
                      "core_retention": round(float(np.mean(core_ret)), 4)}
    write_dat(outdir / "figdata" / "m38_quant.dat",
              ["quant_index", "individuation", "core_retention"], dat)

    (outdir / "tex").mkdir(parents=True, exist_ok=True)
    fig = figtex.line_figure(
        m_id=M_ID, dat_name="m38_quant.dat",
        columns=[(1, "individuation recovery"), (2, "core retention")],
        xlabel="quantization (0 F16, 1 Q8, 2 Q4)", ylabel="persona stability",
        caption=("Persona stability under quantization/fragmentation: lower precision (Q4) erodes "
                 f"individuating identity (Simülasyon; n={N_PERSONAS}; seed={seed}). Real 3-device "
                 "measurements would be supplied by the author."),
        label="fig:m38", source=SOURCE, tier=Tier.SIMULASYON.value, seed=seed)
    (outdir / "tex" / "m38_fig.tex").write_text(fig, encoding="utf-8")

    results = {
        "metadata": run_metadata(M_ID, seed, {"n_personas": N_PERSONAS, "quant": QUANT}),
        "tool_usage": TOOL_USAGE,
        "stability_by_quantization": {q: {k: stamp(v, seed=seed) for k, v in s.items()}
                                      for q, s in summary.items()},
        "future_work": stamp("The abstract's real 3-device experiment (Apple M4 / Honor Pad 9 / "
                             "Samsung A35, Termux) would supply measured data; here quantization is "
                             "a simulated lossy channel.", tier=Tier.TAHMINI, seed=seed,
                             method="future-work"),
    }
    write_json(outdir / "results.json", results)
    return {"id": M_ID, "outdir": str(outdir), "tool_usage": TOOL_USAGE,
            "headline": {q: s["individuation"] for q, s in summary.items()}}
