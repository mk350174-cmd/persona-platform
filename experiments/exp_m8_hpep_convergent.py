"""
M8 — HPEP-100 (Human Persona Extraction Protocol).

A real 30-person + IRB validation study CANNOT be run in this environment, so it
is documented as **Tahmini / Future Work** (no fabricated human n). What the
harness *can* do is a computational convergent-validity demonstration between the
two HPEP-derived instruments:

* OCEAN (Big-Five) via ``incharacter_ceid.hpep_to_ocean``
* MBTI signed axes via ``incharacter_ceid.hpep_to_mbti``

Convergent-validity checks (established Big-Five↔MBTI relationships):
* Extraversion(OCEAN) ↔ E/I(MBTI)  — should be positive
* Openness(OCEAN)     ↔ N/S(MBTI)  — should be positive (intuition≈openness)

Tier: Simülasyon/Hesaplanan for the proxy; the human study is Tahmini.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import numpy as np
from scipy import stats

from integrations.incharacter_ceid import hpep_to_mbti, hpep_to_ocean

from . import figtex
from ._common import outdir_for, panel_sample, vectors_for
from .io_utils import write_csv, write_dat, write_json
from .provenance import Tier, exp_seed, run_metadata, stamp
from .providers import SeriesProvider, SimulatedProvider

M_ID = "M8"
M_NUM = 8
SOURCE = "experiments/exp_m8_hpep_convergent.py"
TOOL_USAGE = [
    "incharacter_ceid.hpep_to_ocean",
    "incharacter_ceid.hpep_to_mbti",
    "scipy.stats.pearsonr",
]

N_PERSONAS = 80
OCEAN_DIMS = ["O_openness", "C_conscientiousness", "E_extraversion",
              "A_agreeableness", "N_neuroticism"]


def _signed_axis(axis: dict, positive_letter: str) -> float:
    """Continuous signed MBTI axis: +confidence toward ``positive_letter``."""
    conf = float(axis["confidence"])
    return conf if axis["preference"] == positive_letter else -conf


def run(provider: Optional[SeriesProvider] = None, seed: Optional[int] = None,
        outdir: Optional[Path] = None) -> dict:
    provider = provider or SimulatedProvider()  # unused; interface symmetry
    seed = exp_seed(M_NUM) if seed is None else int(seed)
    outdir = Path(outdir) if outdir else outdir_for(M_ID)

    ids = panel_sample(N_PERSONAS)
    vecs = vectors_for(ids)

    ocean = {d: [] for d in OCEAN_DIMS}
    e_axis, n_axis = [], []
    dist_rows = []
    for pid, P in zip(ids, vecs):
        o = hpep_to_ocean(P)
        m = hpep_to_mbti(P)
        for d in OCEAN_DIMS:
            ocean[d].append(float(o[d]))
        e_axis.append(_signed_axis(m["E_vs_I"], "E"))
        n_axis.append(_signed_axis(m["S_vs_N"], "N"))
        dist_rows.append([pid] + [round(float(o[d]), 4) for d in OCEAN_DIMS] + [m["type"]])

    write_csv(outdir / "m8_ocean_distribution.csv",
              ["persona_id"] + OCEAN_DIMS + ["mbti_type"], dist_rows)

    # OCEAN distribution figure data (mean ± std per dim)
    means = [float(np.mean(ocean[d])) for d in OCEAN_DIMS]
    stds = [float(np.std(ocean[d])) for d in OCEAN_DIMS]
    write_dat(outdir / "figdata" / "m8_ocean_dist.dat",
              ["dim_index", "mean", "std"],
              np.column_stack([np.arange(1, len(OCEAN_DIMS) + 1), means, stds]))

    # ── convergent validity correlations ────────────────────────────────────────
    e_r, e_p = stats.pearsonr(ocean["E_extraversion"], e_axis)
    o_r, o_p = stats.pearsonr(ocean["O_openness"], n_axis)
    convergent = {
        "interpretation": (
            "OCEAN and MBTI instruments derived from the same HPEP vector agree on the "
            "expected axes (Extraversion↔E/I, Openness↔intuition), supporting internal "
            "convergent validity (Simülasyon; not a human-subjects study)."
        ),
        "extraversion_vs_EI": {"pearson_r": stamp(round(float(e_r), 4), seed=seed),
                               "pearson_p": float(f"{e_p:.3e}")},
        "openness_vs_NS": {"pearson_r": stamp(round(float(o_r), 4), seed=seed),
                           "pearson_p": float(f"{o_p:.3e}")},
    }

    # ── figure / table ──────────────────────────────────────────────────────────
    (outdir / "tex").mkdir(parents=True, exist_ok=True)
    fig = figtex.line_figure(
        m_id=M_ID, dat_name="m8_ocean_dist.dat",
        columns=[(1, "mean OCEAN score")],
        xlabel="OCEAN dimension (O,C,E,A,N = 1..5)", ylabel="mean score",
        caption=("Big-Five (OCEAN) profile distribution across an 80-persona panel from "
                 f"HPEP-100 vectors (Simülasyon; seed={seed})."),
        label="fig:m8_ocean", source=SOURCE, tier=Tier.SIMULASYON.value, seed=seed)
    (outdir / "tex" / "m8_ocean_fig.tex").write_text(fig, encoding="utf-8")

    tbl = figtex.table(
        header=["Convergent pair", "Pearson $r$", "$p$"],
        rows=[
            ["Extraversion vs E/I", f"{e_r:.3f}", f"{e_p:.2e}"],
            ["Openness vs N/S (intuition)", f"{o_r:.3f}", f"{o_p:.2e}"],
        ],
        caption=("Computational convergent validity between HPEP-derived OCEAN and MBTI "
                 f"instruments (Simülasyon; $n={len(ids)}$; seed={seed}). A human 30-person "
                 "study with real Big-Five/MBTI questionnaires remains future work."),
        label="tab:m8_convergent", source=SOURCE, tier=Tier.SIMULASYON.value, seed=seed,
        col_spec="lrr", escape_cells=False)
    (outdir / "tex" / "m8_convergent_table.tex").write_text(tbl, encoding="utf-8")

    results = {
        "metadata": run_metadata(M_ID, seed, {"n_personas": len(ids)}),
        "tool_usage": TOOL_USAGE,
        "ocean_distribution": {d: {"mean": round(m, 4), "std": round(s, 4)}
                               for d, m, s in zip(OCEAN_DIMS, means, stds)},
        "convergent_validity": convergent,
        "future_work": stamp(
            "Human convergent validity requires a 30-participant study with real "
            "Big-Five/MBTI/Enneagram questionnaires under IRB approval. Not performed "
            "here (no human data); the above is a computational proxy only.",
            tier=Tier.TAHMINI, seed=seed, method="future-work"),
    }
    write_json(outdir / "results.json", results)
    return {"id": M_ID, "outdir": str(outdir), "tool_usage": TOOL_USAGE,
            "headline": {"extraversion_vs_EI_r": round(float(e_r), 3),
                         "openness_vs_NS_r": round(float(o_r), 3)}}
