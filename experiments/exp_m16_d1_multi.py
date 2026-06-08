"""
M16 — D1-Multi (cross-persona / cross-"model" / cross-"language" benchmark).

Scales M1's N=1 Holmes protocol to a 5×3×2 simulated design: 5 personas ×
3 "model" regimes (noise levels) × 2 "language" drift-rates = 30 metallic M(t)
series. Reports cross-regime Spearman consistency, a language-drift contrast, and
a simple power analysis (sessions for 80% power).

Honesty: the "models" (regime-A/B/C) and "languages" (en/tr) are SIMULATED regimes
(noise + drift-rate parameters), NOT real GPT-4o/Claude/Llama or real Turkish/English
conversations. Real cross-model/cross-language replication is Tahmini future work
(plug in LLMProvider). Tier: Simülasyon.
"""

from __future__ import annotations

import math
from itertools import combinations
from pathlib import Path
from typing import Optional

import numpy as np
from scipy import stats

from persona_math.d1_protocol import metallic_score

from . import figtex
from ._common import outdir_for, resolvable_ids, stable_offset, vectors_for
from .series_builders import build_peaking_series
from .io_utils import write_csv, write_dat, write_json
from .provenance import Tier, exp_seed, run_metadata, stamp
from .providers import SeriesProvider, SimulatedProvider

M_ID = "M16"
M_NUM = 16
SOURCE = "experiments/exp_m16_d1_multi.py"
TOOL_USAGE = ["d1_protocol.metallic_score", "foundation.metallic_score_raw (M01-M04)",
              "scipy.stats.spearmanr"]

# Preference list; 'machiavelli' lacks a resolvable vector so 'chanakya' (the
# "Indian Machiavelli") stands in. We take the first 5 that resolve.
_PERSONA_PREF = ["machiavelli", "chanakya", "sherlock_holmes_char", "socrates",
                 "friedrich_nietzsche_classic", "albert_einstein"]
MODELS = {"regime-A": 0.01, "regime-B": 0.02, "regime-C": 0.04}     # noise level
LANGS = {"en": 1.0, "tr": 1.5}                                       # drift-rate (tr faster)
N_TURNS = 15


def run(provider: Optional[SeriesProvider] = None, seed: Optional[int] = None,
        outdir: Optional[Path] = None) -> dict:
    provider = provider or SimulatedProvider()  # interface symmetry
    seed = exp_seed(M_NUM) if seed is None else int(seed)
    outdir = Path(outdir) if outdir else outdir_for(M_ID)

    personas = resolvable_ids(_PERSONA_PREF)[:5]

    # curves[(persona, model, lang)] = M(t) array
    curves: dict[tuple, np.ndarray] = {}
    combo_rows = []
    for pid in personas:
        P0 = vectors_for([pid])[0]
        for model, sigma in MODELS.items():
            for lang, strength in LANGS.items():
                rng = np.random.default_rng(seed + stable_offset(f"{pid}{model}{lang}"))
                series = build_peaking_series(P0, N_TURNS, rng, strength=strength, sigma=sigma)
                mt = np.asarray(metallic_score(series)["metallic_scores"])
                curves[(pid, model, lang)] = mt
                combo_rows.append([pid, model, lang, round(float(mt[0]), 4),
                                   round(float(mt[-1]), 4), round(float(mt.mean()), 4)])
    write_csv(outdir / "m16_per_combo.csv",
              ["persona", "model", "lang", "M_start", "M_end", "M_mean"], combo_rows)

    # ── cross-"model" consistency: do the 3 regimes trace similar M(t)? ─────────
    rhos = []
    for pid in personas:
        for lang in LANGS:
            mats = [curves[(pid, m, lang)] for m in MODELS]
            for a, b in combinations(mats, 2):
                rho, _ = stats.spearmanr(a, b)
                if not math.isnan(rho):
                    rhos.append(rho)
    mean_consistency = float(np.mean(rhos))

    # ── "language" drift contrast: tr (faster) vs en final metallic ─────────────
    en_final = [curves[(p, m, "en")][-1] for p in personas for m in MODELS]
    tr_final = [curves[(p, m, "tr")][-1] for p in personas for m in MODELS]
    u, p_lang = stats.mannwhitneyu(tr_final, en_final, alternative="greater")

    # ── power analysis (normal approx, two-sample, 80% power, α=.05 two-sided) ──
    starts = np.array([c[0] for c in curves.values()])
    ends = np.array([c[-1] for c in curves.values()])
    pooled_sd = math.sqrt((starts.var(ddof=1) + ends.var(ddof=1)) / 2) or 1e-9
    d = float(abs(ends.mean() - starts.mean()) / pooled_sd)
    z_a, z_b = 1.96, 0.84
    n_needed = int(math.ceil(2 * ((z_a + z_b) / max(d, 1e-6)) ** 2))

    # ── mean curve per model regime (averaged over personas & langs) for figure ─
    dat_cols = [np.arange(1, N_TURNS + 1, dtype=float)]
    for model in MODELS:
        stack = [curves[(p, model, lang)] for p in personas for lang in LANGS]
        dat_cols.append(np.mean(stack, axis=0))
    write_dat(outdir / "figdata" / "m16_mean_curves.dat",
              ["turn"] + list(MODELS), np.column_stack(dat_cols))

    # ── figure / table ──────────────────────────────────────────────────────────
    (outdir / "tex").mkdir(parents=True, exist_ok=True)
    fig = figtex.line_figure(
        m_id=M_ID, dat_name="m16_mean_curves.dat",
        columns=[(i + 1, m) for i, m in enumerate(MODELS)],
        xlabel="D1 phase", ylabel="metallic analog $M(t)$",
        caption=("Mean metallic trajectories per simulated model regime, averaged over 5 "
                 "personas and 2 language drift-rates (Simülasyon; 30 combinations; "
                 f"seed={seed}). Regimes are noise parameters, not real LLMs."),
        label="fig:m16_curves", source=SOURCE, tier=Tier.SIMULASYON.value, seed=seed)
    (outdir / "tex" / "m16_curves_fig.tex").write_text(fig, encoding="utf-8")

    tbl = figtex.table(
        header=["Quantity", "Value"],
        rows=[
            ["Combinations (5×3×2)", "30"],
            ["Cross-regime Spearman $\\rho$ (mean)", f"{mean_consistency:.3f}"],
            ["tr vs en final $M$ (MW $p$, one-sided)", f"{p_lang:.2e}"],
            ["tr final $M$ (mean)", f"{np.mean(tr_final):.3f}"],
            ["en final $M$ (mean)", f"{np.mean(en_final):.3f}"],
            ["Effect size Cohen's $d$", f"{d:.2f}"],
            ["Sessions for 80\\% power", f"{n_needed}"],
        ],
        caption=("Cross-regime consistency, language drift, and power analysis for the "
                 f"D1-Multi simulated benchmark (Simülasyon; seed={seed})."),
        label="tab:m16", source=SOURCE, tier=Tier.SIMULASYON.value, seed=seed,
        col_spec="lr", escape_cells=False)
    (outdir / "tex" / "m16_table.tex").write_text(tbl, encoding="utf-8")

    results = {
        "metadata": run_metadata(M_ID, seed, {"personas": personas, "models": list(MODELS),
                                              "langs": list(LANGS), "n_turns": N_TURNS}),
        "tool_usage": TOOL_USAGE,
        "cross_regime_consistency": stamp(round(mean_consistency, 4), seed=seed,
                                          note="mean pairwise Spearman ρ of M(t) across regimes"),
        "language_drift": {
            "tr_final_mean": round(float(np.mean(tr_final)), 4),
            "en_final_mean": round(float(np.mean(en_final)), 4),
            "mannwhitney_U": stamp(round(float(u), 2), seed=seed, note="tr > en (faster drift)"),
            "mannwhitney_p": float(f"{p_lang:.3e}"),
        },
        "power_analysis": {
            "cohens_d": stamp(round(d, 4), tier=Tier.HESAPLANAN, seed=seed),
            "n_sessions_80pct_power": stamp(n_needed, tier=Tier.HESAPLANAN, seed=seed,
                                            method="normal-approx", note="two-sample, α=.05"),
        },
    }
    write_json(outdir / "results.json", results)
    return {"id": M_ID, "outdir": str(outdir), "tool_usage": TOOL_USAGE,
            "headline": {"consistency_rho": round(mean_consistency, 3),
                         "n_sessions": n_needed}}
