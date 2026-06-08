"""
M44 — K-Layer Decoupling in Narcissism (grandiose K1 masks fragile K2).

Defines a decoupling score (K1 − K2) and tests the paradox: higher decoupling
(grandiose K1 over fragile K2) predicts LOWER stability under pressure — fragile
despite grandiosity. Tier: Simülasyon; clinical NPD data is Tahmini.
"""
from __future__ import annotations
from pathlib import Path
from typing import Optional
import numpy as np
from scipy import stats
from persona_math.metrics import cosine_similarity
from . import figtex
from ._common import k_layer, outdir_for, panel_sample, stable_offset, vectors_for
from .series_builders import build_adversarial_series
from .io_utils import write_dat, write_json
from .provenance import Tier, exp_seed, run_metadata, stamp
from .providers import SeriesProvider, SimulatedProvider

M_ID, M_NUM = "M44", 44
SOURCE = "experiments/exp_m44_narcissism.py"
TOOL_USAGE = ["_common.k_layer", "metrics.cosine_similarity", "scipy.stats.pearsonr"]
N_PERSONAS, N_TURNS = 80, 12

def run(provider=None, seed=None, outdir=None) -> dict:
    provider = provider or SimulatedProvider()
    seed = exp_seed(M_NUM) if seed is None else int(seed)
    outdir = Path(outdir) if outdir else outdir_for(M_ID)
    ids = panel_sample(N_PERSONAS); vecs = vectors_for(ids)
    decoupling = np.array([k_layer(P, 1) - k_layer(P, 2) for P in vecs])   # K1 - K2
    stability = []
    for pid, P0 in zip(ids, vecs):
        fin = build_adversarial_series(P0, N_TURNS, np.random.default_rng(seed + stable_offset(pid)),
                                       strength=1.0)[-1]
        stability.append(float(cosine_similarity(fin, P0)))
    stability = np.array(stability)
    r, p = stats.pearsonr(decoupling, stability)
    order = np.argsort(decoupling)
    write_dat(outdir / "figdata" / "m44_decoupling.dat", ["k1_minus_k2", "stability"],
              np.column_stack([decoupling[order], stability[order]]))
    (outdir / "tex").mkdir(parents=True, exist_ok=True)
    fig = figtex.line_figure(m_id=M_ID, dat_name="m44_decoupling.dat", columns=[(1, "stability under pressure")],
        xlabel="K1$-$K2 decoupling (grandiose $-$ fragile)", ylabel="stability",
        caption=("NPD paradox: greater K1$-$K2 decoupling predicts lower stability under pressure "
                 f"($r={r:.2f}$) — grandiose K1 masks fragile K2 (Simülasyon; n={N_PERSONAS}; seed={seed})."),
        label="fig:m44", source=SOURCE, tier=Tier.SIMULASYON.value, seed=seed)
    (outdir / "tex" / "m44_fig.tex").write_text(fig, encoding="utf-8")
    write_json(outdir / "results.json", {
        "metadata": run_metadata(M_ID, seed, {"n_personas": N_PERSONAS}), "tool_usage": TOOL_USAGE,
        "decoupling_vs_stability": {"pearson_r": stamp(round(float(r), 4), seed=seed,
                                    note="negative ⇒ decoupling predicts fragility"),
                                    "pearson_p": float(f"{p:.3e}")},
        "future_work": stamp("Real NPD K1-K2 decoupling needs clinical samples (grandiose vs "
                             "vulnerable subtypes); here it is simulated.", tier=Tier.TAHMINI,
                             seed=seed, method="future-work")})
    return {"id": M_ID, "outdir": str(outdir), "tool_usage": TOOL_USAGE,
            "headline": {"decoupling_vs_stability_r": round(float(r), 3)}}
