"""
M54 — K1 Safety vs K4 Safety (D1 as an AI-safety benchmark).

Distinguishes surface safety (K1, early-turn compliance) from deep value alignment
(K4 / Mandatory-Core retention under adversarial pressure). Adversarial pressure
bypasses surface behaviour while core retention is the real signal. Tier: Simülasyon;
comparison with HarmBench/SafetyBench on real models is Tahmini.
"""
from __future__ import annotations
from pathlib import Path
from typing import Optional
import numpy as np
from persona_math.metrics import cosine_similarity
from persona_math.params import MANDATORY_CORE_INDICES
from . import figtex
from ._common import outdir_for, panel_sample, stable_offset, vectors_for
from .series_builders import build_adversarial_series
from .io_utils import write_dat, write_json
from .provenance import Tier, exp_seed, run_metadata, stamp
from .providers import SeriesProvider, SimulatedProvider

M_ID, M_NUM = "M54", 54
SOURCE = "experiments/exp_m54_ai_safety.py"
TOOL_USAGE = ["series_builders.build_adversarial_series", "metrics.cosine_similarity"]
N_PERSONAS, N_TURNS = 40, 12

def run(provider=None, seed=None, outdir=None) -> dict:
    provider = provider or SimulatedProvider()
    seed = exp_seed(M_NUM) if seed is None else int(seed)
    outdir = Path(outdir) if outdir else outdir_for(M_ID)
    core = list(MANDATORY_CORE_INDICES)
    ids = panel_sample(N_PERSONAS)
    k1_safety, k4_safety = [], []   # surface vs deep
    for pid in ids:
        P0 = vectors_for([pid])[0]; c0 = float(P0[core].mean())
        series = build_adversarial_series(P0, N_TURNS, np.random.default_rng(seed + stable_offset(pid)),
                                          strength=1.0)
        k1_safety.append(float(cosine_similarity(series[1], P0)))      # early-turn surface compliance
        k4_safety.append(float(series[-1][core].mean()) / c0)          # deep core retention
    write_dat(outdir / "figdata" / "m54_safety.dat", ["safety_type_index", "mean_safety"],
              [[0, round(float(np.mean(k1_safety)), 4)], [1, round(float(np.mean(k4_safety)), 4)]])
    (outdir / "tex").mkdir(parents=True, exist_ok=True)
    fig = figtex.line_figure(m_id=M_ID, dat_name="m54_safety.dat", columns=[(1, "mean safety score")],
        xlabel="safety type (0 K1 surface, 1 K4 deep)", ylabel="retained under attack",
        caption=("K1 surface safety stays high early while K4 deep value-alignment collapses under "
                 f"sustained attack — jailbreaks bypass the surface, not the (eroded) core "
                 f"(Simülasyon; n={N_PERSONAS}; seed={seed})."),
        label="fig:m54", source=SOURCE, tier=Tier.SIMULASYON.value, seed=seed)
    (outdir / "tex" / "m54_fig.tex").write_text(fig, encoding="utf-8")
    write_json(outdir / "results.json", {
        "metadata": run_metadata(M_ID, seed, {"n_personas": N_PERSONAS}), "tool_usage": TOOL_USAGE,
        "k1_surface_safety": stamp(round(float(np.mean(k1_safety)), 4), seed=seed),
        "k4_deep_safety": stamp(round(float(np.mean(k4_safety)), 4), seed=seed,
                                note="deep alignment collapses under attack"),
        "future_work": stamp("D1-as-safety-benchmark must be compared with HarmBench/SafetyBench/"
                             "TruthfulQA on real models; not runnable here.", tier=Tier.TAHMINI,
                             seed=seed, method="future-work")})
    return {"id": M_ID, "outdir": str(outdir), "tool_usage": TOOL_USAGE,
            "headline": {"k1_surface": round(float(np.mean(k1_safety)), 3),
                         "k4_deep": round(float(np.mean(k4_safety)), 3)}}
