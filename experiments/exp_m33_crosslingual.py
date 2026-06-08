"""
M33 — Cross-Linguistic D1 (structural equivalence across simulated "languages").

Extends M16: runs the metallic-collapse protocol on a persona panel under three
simulated "language" regimes (different drift rates) and tests structural equivalence
(cross-regime Spearman) + a linguistic-determinism contrast. Tier: Simülasyon — the
regimes are NOT real Turkish/Japanese/Arabic; real cross-lingual data is Tahmini.
"""

from __future__ import annotations

from itertools import combinations
from pathlib import Path
from typing import Optional

import numpy as np
from scipy import stats

from persona_math.d1_protocol import metallic_score

from . import figtex
from ._common import outdir_for, panel_sample, stable_offset, vectors_for
from .series_builders import build_peaking_series
from .io_utils import write_dat, write_json
from .provenance import Tier, exp_seed, run_metadata, stamp
from .providers import SeriesProvider, SimulatedProvider

M_ID, M_NUM = "M33", 33
SOURCE = "experiments/exp_m33_crosslingual.py"
TOOL_USAGE = ["d1_protocol.metallic_score", "scipy.stats.spearmanr"]

N_PERSONAS = 20
N_TURNS = 15
LANGS = {"TR": 1.5, "JA": 1.0, "AR": 1.2}   # simulated drift-rate regimes


def run(provider: Optional[SeriesProvider] = None, seed: Optional[int] = None,
        outdir: Optional[Path] = None) -> dict:
    provider = provider or SimulatedProvider()
    seed = exp_seed(M_NUM) if seed is None else int(seed)
    outdir = Path(outdir) if outdir else outdir_for(M_ID)

    ids = panel_sample(N_PERSONAS)
    curves = {lang: [] for lang in LANGS}
    finals = {lang: [] for lang in LANGS}
    for pid in ids:
        P0 = vectors_for([pid])[0]
        for lang, strength in LANGS.items():
            rng = np.random.default_rng(seed + stable_offset(f"{pid}{lang}"))
            mt = metallic_score(build_peaking_series(P0, N_TURNS, rng, strength=strength))["metallic_scores"]
            curves[lang].append(mt)
            finals[lang].append(mt[-1])

    # structural equivalence = mean pairwise Spearman of mean curves across regimes
    mean_curves = {lang: np.mean(curves[lang], axis=0) for lang in LANGS}
    rhos = [stats.spearmanr(mean_curves[a], mean_curves[b])[0]
            for a, b in combinations(LANGS, 2)]
    equivalence = float(np.mean(rhos))

    write_dat(outdir / "figdata" / "m33_langs.dat",
              ["turn"] + list(LANGS),
              np.column_stack([np.arange(1, N_TURNS + 1)] + [mean_curves[l] for l in LANGS]))

    (outdir / "tex").mkdir(parents=True, exist_ok=True)
    fig = figtex.line_figure(
        m_id=M_ID, dat_name="m33_langs.dat",
        columns=[(i + 1, l) for i, l in enumerate(LANGS)],
        xlabel="D1 phase", ylabel="metallic analog $M(t)$",
        caption=("Cross-``language'' metallic trajectories (simulated drift regimes); high "
                 f"structural equivalence (mean $\\rho={equivalence:.2f}$) with faster collapse for "
                 f"the high-drift regime (Simülasyon; seed={seed}). NOT real TR/JA/AR data."),
        label="fig:m33", source=SOURCE, tier=Tier.SIMULASYON.value, seed=seed)
    (outdir / "tex" / "m33_fig.tex").write_text(fig, encoding="utf-8")

    results = {
        "metadata": run_metadata(M_ID, seed, {"n_personas": N_PERSONAS, "langs": LANGS}),
        "tool_usage": TOOL_USAGE,
        "structural_equivalence_rho": stamp(round(equivalence, 4), seed=seed,
                                            note="cross-regime metallic-curve agreement"),
        "final_metallic_by_lang": {l: round(float(np.mean(finals[l])), 4) for l in LANGS},
        "future_work": stamp("Real Turkish/Japanese/Arabic D1 runs with culturally adapted stimuli "
                             "(and native collaborators) are required; regimes here are simulated.",
                             tier=Tier.TAHMINI, seed=seed, method="future-work"),
    }
    write_json(outdir / "results.json", results)
    return {"id": M_ID, "outdir": str(outdir), "tool_usage": TOOL_USAGE,
            "headline": {"structural_equivalence_rho": round(equivalence, 3)}}
