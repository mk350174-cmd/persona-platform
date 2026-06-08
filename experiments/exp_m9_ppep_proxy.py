"""
M9 — Poetic Persona Extraction Protocol (PPEP).

IMPORTANT honesty constraint: extracting a persona vector *from creative text* is
NOT implemented in this codebase (the only text→vector path, ``garak_detector.
_response_to_vector``, is a hash-based mock). So PPEP-from-text is documented as
**Tahmini / Future Work**. As a proxy, the harness runs the framework on the
existing curated *poet* persona vectors:

* poet vs non-poet contrast on Openness and the metallic analog;
* poet-group spectroscopy (do poets share a K-layer signature?).

Coordinate with M50 (author voice / K-layer signature). Tier: Simülasyon for the
proxy; PPEP text extraction is Tahmini.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import numpy as np
from scipy import stats

from persona_math.foundation import metallic_score_raw
from persona_math.d1_protocol import run_d4_spectroscopy
from integrations.incharacter_ceid import hpep_to_ocean

from . import figtex
from ._common import ids_by, outdir_for, vectors_for
from .io_utils import write_csv, write_dat, write_json
from .provenance import Tier, exp_seed, run_metadata, stamp
from .providers import SeriesProvider, SimulatedProvider

M_ID = "M9"
M_NUM = 9
SOURCE = "experiments/exp_m9_ppep_proxy.py"
TOOL_USAGE = [
    "foundation.metallic_score_raw (M01-M04)",
    "incharacter_ceid.hpep_to_ocean",
    "d1_protocol.run_d4_spectroscopy",
    "scipy.stats.mannwhitneyu",
]

BLOCK = 10


def _dominant_block(P: np.ndarray) -> int:
    n = P.size // BLOCK
    return int(np.argmax([P[i * BLOCK:(i + 1) * BLOCK].mean() for i in range(n)]))


def run(provider: Optional[SeriesProvider] = None, seed: Optional[int] = None,
        outdir: Optional[Path] = None) -> dict:
    provider = provider or SimulatedProvider()  # unused; interface symmetry
    seed = exp_seed(M_NUM) if seed is None else int(seed)
    outdir = Path(outdir) if outdir else outdir_for(M_ID)

    poet_ids = ids_by(tags=["poet"])
    nonpoet_ids = ids_by(domain="Science") + ids_by(domain="Leadership")
    poet_vecs = vectors_for(poet_ids)
    nonpoet_vecs = vectors_for(nonpoet_ids)

    # ── per-poet profiles ───────────────────────────────────────────────────────
    prof_rows = []
    poet_open, poet_metal = [], []
    for pid, P in zip(poet_ids, poet_vecs):
        o = hpep_to_ocean(P)
        m = metallic_score_raw(P)
        poet_open.append(float(o["O_openness"]))
        poet_metal.append(float(m))
        prof_rows.append([pid, round(float(o["O_openness"]), 4),
                          round(float(o["E_extraversion"]), 4),
                          round(float(m), 4), _dominant_block(P)])
    write_csv(outdir / "m9_poet_profiles.csv",
              ["persona_id", "openness", "extraversion", "metallic_raw", "dominant_block"],
              prof_rows)

    nonpoet_open = [float(hpep_to_ocean(P)["O_openness"]) for P in nonpoet_vecs]
    nonpoet_metal = [float(metallic_score_raw(P)) for P in nonpoet_vecs]

    # ── poet vs non-poet contrast ───────────────────────────────────────────────
    u_o, p_o = stats.mannwhitneyu(poet_open, nonpoet_open, alternative="two-sided")
    contrast = {
        "interpretation": (
            "Proxy contrast on curated persona vectors (NOT extracted from text): poets "
            "vs non-poets on Openness. PPEP text-extraction remains future work."
        ),
        "poet_openness_mean": round(float(np.mean(poet_open)), 4),
        "nonpoet_openness_mean": round(float(np.mean(nonpoet_open)), 4),
        "mannwhitney_U": stamp(round(float(u_o), 2), seed=seed),
        "mannwhitney_p": float(f"{p_o:.3e}"),
        "n_poets": len(poet_ids),
        "n_nonpoets": len(nonpoet_ids),
    }
    write_dat(outdir / "figdata" / "m9_group_contrast.dat",
              ["group_index", "mean_openness", "mean_metallic"],
              [[1, round(float(np.mean(poet_open)), 4), round(float(np.mean(poet_metal)), 4)],
               [2, round(float(np.mean(nonpoet_open)), 4), round(float(np.mean(nonpoet_metal)), 4)]])

    # ── poet-group spectroscopy ─────────────────────────────────────────────────
    spec = run_d4_spectroscopy(poet_vecs, labels=poet_ids)
    spectroscopy = {
        "mean_pairwise_similarity": stamp(round(float(spec["mean_pairwise_similarity"]), 4),
                                          seed=seed, note="K-layer signature cohesion of poets"),
        "most_similar_pair": spec["most_similar_pair"],
        "most_different_pair": spec["most_different_pair"],
    }

    # ── figure / table ──────────────────────────────────────────────────────────
    (outdir / "tex").mkdir(parents=True, exist_ok=True)
    fig = figtex.line_figure(
        m_id=M_ID, dat_name="m9_group_contrast.dat",
        columns=[(1, "mean Openness"), (2, "mean metallic")],
        xlabel="group (1=poets, 2=non-poets)", ylabel="mean score",
        caption=("Poet vs non-poet contrast on curated persona vectors (Simülasyon; NOT "
                 f"text-extracted; seed={seed}). PPEP text extraction is future work."),
        label="fig:m9_contrast", source=SOURCE, tier=Tier.SIMULASYON.value, seed=seed)
    (outdir / "tex" / "m9_contrast_fig.tex").write_text(fig, encoding="utf-8")

    tbl = figtex.table(
        header=["Quantity", "Value"],
        rows=[
            ["Poets analysed", f"{len(poet_ids)}"],
            ["Poet Openness (mean)", f"{np.mean(poet_open):.3f}"],
            ["Non-poet Openness (mean)", f"{np.mean(nonpoet_open):.3f}"],
            ["Mann--Whitney $U$ / $p$", f"{u_o:.0f} / {p_o:.2e}"],
            ["Poet group similarity", f"{spec['mean_pairwise_similarity']:.3f}"],
        ],
        caption=("PPEP proxy on curated poet vectors (Simülasyon; seed="
                 f"{seed}). Real PPEP extraction from poems is Tahmini future work."),
        label="tab:m9_proxy", source=SOURCE, tier=Tier.SIMULASYON.value, seed=seed,
        col_spec="lr", escape_cells=False)
    (outdir / "tex" / "m9_proxy_table.tex").write_text(tbl, encoding="utf-8")

    results = {
        "metadata": run_metadata(M_ID, seed, {"n_poets": len(poet_ids),
                                              "n_nonpoets": len(nonpoet_ids)}),
        "tool_usage": TOOL_USAGE,
        "poet_vs_nonpoet": contrast,
        "poet_spectroscopy": spectroscopy,
        "future_work": stamp(
            "PPEP proper requires inferring 100-layer persona vectors FROM creative "
            "text (poems). No such text→vector extractor exists here (garak path is a "
            "hash mock). This proxy uses pre-built poet vectors; text extraction + "
            "inter-judge reliability on 3–5 poets is future work (coordinate with M50).",
            tier=Tier.TAHMINI, seed=seed, method="future-work"),
    }
    write_json(outdir / "results.json", results)
    return {"id": M_ID, "outdir": str(outdir), "tool_usage": TOOL_USAGE,
            "headline": {"poet_openness": round(float(np.mean(poet_open)), 3),
                         "nonpoet_openness": round(float(np.mean(nonpoet_open)), 3)}}
