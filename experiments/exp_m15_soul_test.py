"""
M15 — The Experimental Test of Soul (K-layer fidelity for psychological continuity).

Which K-layers must survive substrate transfer for psychological continuity? We
ablate each of the 10 blocks in turn and measure the CEID drop, ranking blocks by
"continuity-criticality". The Mandatory-Core blocks (holding K1/K2/K4/K12) are
predicted to dominate. Builds on M13. Tier: Simülasyon; real cross-model transfer
is Tahmini.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import numpy as np

from persona_math.ceid import ceid_score
from persona_math.params import MANDATORY_CORE_INDICES

from . import figtex
from ._common import outdir_for, panel_sample, vectors_for
from .io_utils import write_dat, write_json
from .provenance import Tier, exp_seed, run_metadata, stamp
from .providers import SeriesProvider, SimulatedProvider

M_ID, M_NUM = "M15", 15
SOURCE = "experiments/exp_m15_soul_test.py"
TOOL_USAGE = ["ceid.ceid_score (per-block ablation)"]

N_PERSONAS = 30
BLOCK = 10
N_BLOCKS = 10


def run(provider: Optional[SeriesProvider] = None, seed: Optional[int] = None,
        outdir: Optional[Path] = None) -> dict:
    provider = provider or SimulatedProvider()
    seed = exp_seed(M_NUM) if seed is None else int(seed)
    outdir = Path(outdir) if outdir else outdir_for(M_ID)

    ids = panel_sample(N_PERSONAS)
    vecs = vectors_for(ids)
    core_blocks = sorted({i // BLOCK for i in MANDATORY_CORE_INDICES})  # {0, 1}

    # mean CEID drop when each block is zeroed
    drops = np.zeros(N_BLOCKS)
    for P0 in vecs:
        base = float(ceid_score(P0, P0)["CEID_score"])  # = 1.0 (self-baseline)
        for b in range(N_BLOCKS):
            ablated = P0.copy()
            ablated[b * BLOCK:(b + 1) * BLOCK] = 0.0
            drops[b] += base - float(ceid_score(ablated, P0)["CEID_score"])
    drops /= len(vecs)

    write_dat(outdir / "figdata" / "m15_block_importance.dat",
              ["block", "mean_ceid_drop"],
              np.column_stack([np.arange(N_BLOCKS), drops]))

    order = np.argsort(drops)[::-1]
    most_critical = [int(b) for b in order[:3]]
    core_is_top = set(core_blocks) <= set(int(b) for b in order[:len(core_blocks) + 1])

    (outdir / "tex").mkdir(parents=True, exist_ok=True)
    fig = figtex.line_figure(
        m_id=M_ID, dat_name="m15_block_importance.dat",
        columns=[(1, "mean CEID drop on ablation")],
        xlabel="K-layer block (0--9)", ylabel="continuity loss (CEID drop)",
        caption=("Per-block continuity-criticality: zeroing each block and measuring CEID loss. "
                 f"Mandatory-Core blocks {core_blocks} carry psychological continuity "
                 f"(Simülasyon; n={N_PERSONAS}; seed={seed})."),
        label="fig:m15_importance", source=SOURCE, tier=Tier.SIMULASYON.value, seed=seed)
    (outdir / "tex" / "m15_importance_fig.tex").write_text(fig, encoding="utf-8")

    results = {
        "metadata": run_metadata(M_ID, seed, {"n_personas": N_PERSONAS,
                                              "core_blocks": core_blocks}),
        "tool_usage": TOOL_USAGE,
        "block_ceid_drop": {int(b): round(float(drops[b]), 4) for b in range(N_BLOCKS)},
        "most_critical_blocks": stamp(most_critical, seed=seed,
                                      note="top-3 blocks by continuity loss"),
        "core_blocks_are_most_critical": bool(core_is_top),
        "future_work": stamp("Falsifiable real test: transfer the same persona across actual "
                             "model architectures and measure CEID continuity vs layer fidelity. "
                             "Not performed here (no real-LLM access).",
                             tier=Tier.TAHMINI, seed=seed, method="future-work"),
    }
    write_json(outdir / "results.json", results)
    return {"id": M_ID, "outdir": str(outdir), "tool_usage": TOOL_USAGE,
            "headline": {"most_critical_blocks": most_critical,
                         "core_is_top": bool(core_is_top)}}
