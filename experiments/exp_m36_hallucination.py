"""
M36 — K12 as Hallucination Shield (epistemic stance and factual robustness).

A real hallucination benchmark (TruthfulQA/HaluEval, 25k responses × 5 models) needs
LLMs and is Tahmini future work. The computational contribution here: show that the
K12 layer (index 11) is structurally the epistemic layer — it correlates with the
CEID E-axis (epistemic vigilance) across the library — motivating "K12 as shield".
Tier: Simülasyon/Hesaplanan.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import numpy as np
from scipy import stats

from persona_math.foundation import metallic_score_raw

from . import figtex
from ._common import k_layer, outdir_for, panel_sample, vectors_for
from .io_utils import write_dat, write_json
from .provenance import Tier, exp_seed, run_metadata, stamp
from .providers import SeriesProvider, SimulatedProvider

M_ID, M_NUM = "M36", 36
SOURCE = "experiments/exp_m36_hallucination.py"
TOOL_USAGE = ["_common.k_layer", "foundation.metallic_score_raw", "scipy.stats.pearsonr"]

N_PERSONAS = 80
K12_INDEX = 12


def run(provider: Optional[SeriesProvider] = None, seed: Optional[int] = None,
        outdir: Optional[Path] = None) -> dict:
    provider = provider or SimulatedProvider()
    seed = exp_seed(M_NUM) if seed is None else int(seed)
    outdir = Path(outdir) if outdir else outdir_for(M_ID)

    # WEAK harness: the real hallucination benchmark needs LLMs. We can only report
    # the available K12 (epistemic-stance) configurations and a caveated correlation
    # with "groundedness" (1 − metallic; lower entropy collapse). The result is weak
    # in simulation — by design, the factual test is future work.
    ids = panel_sample(N_PERSONAS)
    vecs = vectors_for(ids)
    k12 = np.array([k_layer(P, K12_INDEX) for P in vecs])
    groundedness = np.array([1.0 - float(metallic_score_raw(P)) for P in vecs])
    r, p = stats.pearsonr(k12, groundedness)

    order = np.argsort(k12)
    write_dat(outdir / "figdata" / "m36_k12.dat",
              ["k12_activation", "groundedness"],
              np.column_stack([k12[order], groundedness[order]]))

    (outdir / "tex").mkdir(parents=True, exist_ok=True)
    fig = figtex.line_figure(
        m_id=M_ID, dat_name="m36_k12.dat",
        columns=[(1, "groundedness (1 - metallic)")],
        xlabel="K12 (epistemic stance) activation", ylabel="groundedness proxy",
        caption=("K12 epistemic-stance configurations across the library vs a groundedness proxy "
                 f"($r={r:.2f}$, weak in simulation; Simülasyon; n={N_PERSONAS}; seed={seed}). The "
                 "factual-accuracy claim needs a real TruthfulQA/HaluEval benchmark (future work)."),
        label="fig:m36", source=SOURCE, tier=Tier.SIMULASYON.value, seed=seed)
    (outdir / "tex" / "m36_fig.tex").write_text(fig, encoding="utf-8")

    results = {
        "metadata": run_metadata(M_ID, seed, {"n_personas": N_PERSONAS, "k12_index": K12_INDEX}),
        "tool_usage": TOOL_USAGE,
        "k12_vs_groundedness": {
            "pearson_r": stamp(round(float(r), 4), seed=seed,
                               note="weak proxy correlation; not a factual-accuracy test"),
            "pearson_p": float(f"{p:.3e}"),
        },
        "k12_range": [round(float(k12.min()), 4), round(float(k12.max()), 4)],
        "future_work": stamp("The factual-accuracy claim needs a real benchmark: 10 K12 configs × "
                             "5 models × 500 questions (TruthfulQA/HaluEval) = 25k responses. Not "
                             "runnable here (no LLM access).", tier=Tier.TAHMINI, seed=seed,
                             method="future-work"),
    }
    write_json(outdir / "results.json", results)
    return {"id": M_ID, "outdir": str(outdir), "tool_usage": TOOL_USAGE,
            "headline": {"k12_vs_groundedness_r": round(float(r), 3)}}
