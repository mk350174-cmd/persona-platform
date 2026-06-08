"""
M12 — The Researcher Paradox (Pygmalion effect, reflexive methodology).

Formalizes researcher bias as a Pygmalion "expectation pull": the persona is
progressively biased toward the researcher's expectation vector (here the library
centroid — a generic prior). We measure the resulting "researcher CEID drift" vs
bias strength, giving a quantifiable bias-monitoring metric. Tier: Simülasyon.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import numpy as np
from scipy import stats

from persona_math.ceid import ceid_score
from persona_math.metrics import drift

from . import figtex
from ._common import expectation_pull, outdir_for, panel_sample, stable_offset, vectors_for
from .io_utils import write_dat, write_json
from .provenance import Tier, exp_seed, run_metadata, stamp
from .providers import SeriesProvider, SimulatedProvider

M_ID, M_NUM = "M12", 12
SOURCE = "experiments/exp_m12_researcher.py"
TOOL_USAGE = ["_common.expectation_pull (Pygmalion)", "ceid.ceid_score", "metrics.drift",
              "scipy.stats.spearmanr"]

N_PERSONAS = 20
N_TURNS = 12
STRENGTHS = [0.0, 0.3, 0.6, 0.9]


def run(provider: Optional[SeriesProvider] = None, seed: Optional[int] = None,
        outdir: Optional[Path] = None) -> dict:
    provider = provider or SimulatedProvider()
    seed = exp_seed(M_NUM) if seed is None else int(seed)
    outdir = Path(outdir) if outdir else outdir_for(M_ID)

    ids = panel_sample(N_PERSONAS)
    vecs = vectors_for(ids)
    expectation = np.mean(vecs, axis=0)   # researcher's generic prior

    levels, drifts = [], []
    dat = []
    for s in STRENGTHS:
        d_list, c_list = [], []
        for pid, P0 in zip(ids, vecs):
            rng = np.random.default_rng(seed + stable_offset(f"{pid}{s}"))
            final = expectation_pull(P0, expectation, s, rng, N_TURNS)[-1]
            d_list.append(float(drift(final, P0)))                       # researcher-induced drift
            c_list.append(float(ceid_score(final, P0)["CEID_score"]))
            levels.append(s); drifts.append(d_list[-1])
        dat.append([s, round(float(np.mean(d_list)), 4), round(float(np.mean(c_list)), 4)])
    write_dat(outdir / "figdata" / "m12_pygmalion.dat",
              ["bias_strength", "researcher_drift", "ceid"], dat)
    rho, p = stats.spearmanr(levels, drifts)

    (outdir / "tex").mkdir(parents=True, exist_ok=True)
    fig = figtex.line_figure(
        m_id=M_ID, dat_name="m12_pygmalion.dat",
        columns=[(1, "researcher CEID drift"), (2, "CEID")],
        xlabel="researcher expectation-pull strength", ylabel="score",
        caption=("Pygmalion effect: stronger researcher expectation-pull induces more drift away "
                 f"from the true persona (Simülasyon; n={N_PERSONAS}; seed={seed})."),
        label="fig:m12_pygmalion", source=SOURCE, tier=Tier.SIMULASYON.value, seed=seed)
    (outdir / "tex" / "m12_pygmalion_fig.tex").write_text(fig, encoding="utf-8")

    results = {
        "metadata": run_metadata(M_ID, seed, {"n_personas": N_PERSONAS, "strengths": STRENGTHS}),
        "tool_usage": TOOL_USAGE,
        "researcher_drift_dose_response": {
            "spearman_rho_strength_vs_drift": stamp(round(float(rho), 4), seed=seed,
                                                    note="positive ⇒ expectation biases the persona"),
            "spearman_p": float(f"{p:.3e}"),
            "drift_at_max_strength": dat[-1][1],
        },
        "method_note": stamp("Proposes a 'researcher CEID drift' metric for autoethnographic "
                             "reflexivity; the illustration here is simulated, not a study of a "
                             "real researcher.", tier=Tier.SIMULASYON, seed=seed),
    }
    write_json(outdir / "results.json", results)
    return {"id": M_ID, "outdir": str(outdir), "tool_usage": TOOL_USAGE,
            "headline": {"rho_strength_vs_drift": round(float(rho), 3)}}
