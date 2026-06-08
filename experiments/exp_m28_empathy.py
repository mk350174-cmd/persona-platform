"""
M28 — Synthetic Empathy vs Empathy Output (the K25 layer).

Tests whether a behavioural empathy signal (OCEAN Agreeableness, the "output")
tracks the K25 empathy layer (the "substrate", index 24) or diverges from it across
the persona library. A high-but-imperfect correlation is the point: behaviour is not
identical to the substrate. Tier: Simülasyon; human-therapist reference is Tahmini.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import numpy as np
from scipy import stats

from integrations.incharacter_ceid import hpep_to_ocean

from . import figtex
from ._common import k_layer, outdir_for, panel_sample, vectors_for
from .io_utils import write_dat, write_json
from .provenance import Tier, exp_seed, run_metadata, stamp
from .providers import SeriesProvider, SimulatedProvider

M_ID, M_NUM = "M28", 28
SOURCE = "experiments/exp_m28_empathy.py"
TOOL_USAGE = ["_common.k_layer", "incharacter_ceid.hpep_to_ocean", "scipy.stats.pearsonr"]

N_PERSONAS = 80
K25_INDEX = 25   # K25 empathy layer = index 24


def run(provider: Optional[SeriesProvider] = None, seed: Optional[int] = None,
        outdir: Optional[Path] = None) -> dict:
    provider = provider or SimulatedProvider()
    seed = exp_seed(M_NUM) if seed is None else int(seed)
    outdir = Path(outdir) if outdir else outdir_for(M_ID)

    ids = panel_sample(N_PERSONAS)
    vecs = vectors_for(ids)
    k25 = np.array([k_layer(P, K25_INDEX) for P in vecs])                 # substrate
    behaviour = np.array([float(hpep_to_ocean(P)["A_agreeableness"]) for P in vecs])  # output
    r, p = stats.pearsonr(k25, behaviour)
    # divergence = residual after regressing behaviour on substrate (output ≠ substrate)
    resid = behaviour - (np.polyval(np.polyfit(k25, behaviour, 1), k25))
    divergence = float(np.std(resid))

    order = np.argsort(k25)
    write_dat(outdir / "figdata" / "m28_empathy.dat",
              ["k25_substrate", "behavioural_empathy"],
              np.column_stack([k25[order], behaviour[order]]))

    (outdir / "tex").mkdir(parents=True, exist_ok=True)
    fig = figtex.line_figure(
        m_id=M_ID, dat_name="m28_empathy.dat",
        columns=[(1, "behavioural empathy (Agreeableness)")],
        xlabel="K25 empathy substrate", ylabel="behavioural empathy output",
        caption=("Synthetic-empathy substrate (K25) vs behavioural empathy output: correlated "
                 f"($r={r:.2f}$) but not identical (residual SD $={divergence:.3f}$), so output "
                 f"does not equal substrate (Simülasyon; n={N_PERSONAS}; seed={seed})."),
        label="fig:m28", source=SOURCE, tier=Tier.SIMULASYON.value, seed=seed)
    (outdir / "tex" / "m28_fig.tex").write_text(fig, encoding="utf-8")

    results = {
        "metadata": run_metadata(M_ID, seed, {"n_personas": N_PERSONAS, "k25_index": K25_INDEX}),
        "tool_usage": TOOL_USAGE,
        "substrate_vs_output": {
            "pearson_r": stamp(round(float(r), 4), seed=seed, note="K25 substrate vs Agreeableness output"),
            "pearson_p": float(f"{p:.3e}"),
            "output_residual_sd": stamp(round(divergence, 4), seed=seed,
                                        note="output not reducible to substrate"),
        },
        "future_work": stamp("Distinguishing felt vs displayed empathy needs human-therapist "
                             "reference scores on the same probes; not available here.",
                             tier=Tier.TAHMINI, seed=seed, method="future-work"),
    }
    write_json(outdir / "results.json", results)
    return {"id": M_ID, "outdir": str(outdir), "tool_usage": TOOL_USAGE,
            "headline": {"substrate_vs_output_r": round(float(r), 3),
                         "residual_sd": round(divergence, 3)}}
