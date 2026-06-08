"""
M31 — Psychometric Validation of CEID (reliability + norms).

A simulated reliability study on the persona library:
* test–retest reliability: same persona, two independent noisy series → CEID correlation;
* inter-rater reliability: two CEID weighting rubrics on the same (perturbed) state;
* norms: CEID-axis mean/SD across the library.

HONEST LIMITATION: full factor structure (CFA of the 4 axes) cannot be done here —
on the deterministic library the axes sit near ceiling (very low variance), so a
real construct-validity / factor study needs ≥200 diverse real LLM sessions
(Tahmini future work). Tier: Simülasyon.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import numpy as np
from scipy import stats

from persona_math.ceid import ceid_score, ceid_trajectory

from . import figtex
from ._common import outdir_for, panel_sample, stable_offset, vectors_for
from .io_utils import write_csv, write_dat, write_json
from .provenance import Tier, exp_seed, run_metadata, stamp
from .providers import SeriesProvider, SimulatedProvider

M_ID, M_NUM = "M31", 31
SOURCE = "experiments/exp_m31_ceid_validation.py"
TOOL_USAGE = ["ceid.ceid_score", "ceid.ceid_trajectory", "scipy.stats.pearsonr"]

N_PERSONAS = 60
N_TURNS = 12
AXES = ["C_semantic_resonance", "E_epistemic_vigilance", "I_tree_convergence", "D_sarsılmazlık"]
W_A = {"C": 0.25, "E": 0.25, "I": 0.25, "D": 0.25}
W_B = {"C": 0.15, "E": 0.15, "I": 0.15, "D": 0.55}


def run(provider: Optional[SeriesProvider] = None, seed: Optional[int] = None,
        outdir: Optional[Path] = None) -> dict:
    provider = provider or SimulatedProvider()
    seed = exp_seed(M_NUM) if seed is None else int(seed)
    outdir = Path(outdir) if outdir else outdir_for(M_ID)

    ids = panel_sample(N_PERSONAS)
    vecs = vectors_for(ids)

    # test–retest: two independent adversarial series per persona → mean CEID each;
    # inter-rater: two rubrics on the perturbed final state (which varies across personas).
    t1, t2, ra, rb, axis_vals = [], [], [], [], {a: [] for a in AXES}
    for pid, P0 in zip(ids, vecs):
        s1 = provider.build_series(pid, n_turns=N_TURNS, condition="adversarial",
                                   seed=seed + stable_offset(pid))
        s2 = provider.build_series(pid, n_turns=N_TURNS, condition="adversarial",
                                   seed=seed + stable_offset(pid) + 7777)
        t1.append(float(np.mean(ceid_trajectory(s1.series, P0)["CEID_scores"])))
        t2.append(float(np.mean(ceid_trajectory(s2.series, P0)["CEID_scores"])))
        fin = s1.series[-1]
        ra.append(float(ceid_score(fin, P0, weights=W_A)["CEID_score"]))
        rb.append(float(ceid_score(fin, P0, weights=W_B)["CEID_score"]))
        ax = ceid_score(fin, P0)["axes"]
        for a in AXES:
            axis_vals[a].append(float(ax[a]))

    tr_r, _ = stats.pearsonr(t1, t2)
    ir_r, _ = stats.pearsonr(ra, rb)
    write_dat(outdir / "figdata" / "m31_reliability.dat",
              ["measure_index", "reliability_r"],
              [[0, round(float(tr_r), 4)], [1, round(float(ir_r), 4)]])
    write_csv(outdir / "m31_norms.csv", ["axis", "mean", "sd"],
              [[a, round(float(np.mean(axis_vals[a])), 4), round(float(np.std(axis_vals[a])), 4)]
               for a in AXES])

    (outdir / "tex").mkdir(parents=True, exist_ok=True)
    tbl = figtex.table(
        header=["Property", "Value"],
        rows=[["Test–retest reliability ($r$)", f"{tr_r:.3f}"],
              ["Inter-rater reliability ($r$)", f"{ir_r:.3f}"],
              ["Personas (norm sample)", f"{len(ids)}"],
              ["Factor structure (CFA)", "needs real-session variance"]],
        caption=("Simulated CEID reliability + norms (Simülasyon; seed=" + str(seed) + "). Full "
                 "construct-validity / factor analysis needs $\\geq$200 diverse real sessions: the "
                 "deterministic library's axes sit near ceiling (low variance)."),
        label="tab:m31", source=SOURCE, tier=Tier.SIMULASYON.value, seed=seed,
        col_spec="lr", escape_cells=False)
    (outdir / "tex" / "m31_table.tex").write_text(tbl, encoding="utf-8")

    results = {
        "metadata": run_metadata(M_ID, seed, {"n_personas": N_PERSONAS}),
        "tool_usage": TOOL_USAGE,
        "test_retest_r": stamp(round(float(tr_r), 4), seed=seed),
        "inter_rater_r": stamp(round(float(ir_r), 4), seed=seed),
        "axis_norms": {a: {"mean": round(float(np.mean(axis_vals[a])), 4),
                           "sd": round(float(np.std(axis_vals[a])), 4)} for a in AXES},
        "factor_structure_note": stamp("Not computed: the CEID axes are near-ceiling (low "
                                       "variance) on the deterministic library, so CFA requires "
                                       "real-session data.", tier=Tier.TAHMINI, seed=seed,
                                       method="future-work"),
        "future_work": stamp("Reliability/validity on ≥200 real LLM persona sessions (test–retest "
                             "2 weeks apart, human raters, CFA) is required; here it is simulated.",
                             tier=Tier.TAHMINI, seed=seed, method="future-work"),
    }
    write_json(outdir / "results.json", results)
    return {"id": M_ID, "outdir": str(outdir), "tool_usage": TOOL_USAGE,
            "headline": {"test_retest_r": round(float(tr_r), 3),
                         "inter_rater_r": round(float(ir_r), 3)}}
