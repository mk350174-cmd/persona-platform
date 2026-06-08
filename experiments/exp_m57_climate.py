"""
M57 — Solastalgia as K8-K9 Disruption (climate anxiety and ecological identity).

Targeted erosion of K8 (temporal layer, idx7) and K9 (relational network, idx8) models
solastalgia — loss of place-identity — as a dose-response of K8/K9 retention vs
ecological-disruption severity. Tier: Simülasyon; field climate-psychology data is Tahmini.
"""
from __future__ import annotations
from pathlib import Path
from typing import Optional
import numpy as np
from scipy import stats
from . import figtex
from ._common import outdir_for, panel_sample, stable_offset, vectors_for
from .series_builders import build_adversarial_series
from .io_utils import write_dat, write_json
from .provenance import Tier, exp_seed, run_metadata, stamp
from .providers import SeriesProvider, SimulatedProvider

M_ID, M_NUM = "M57", 57
SOURCE = "experiments/exp_m57_climate.py"
TOOL_USAGE = ["series_builders.build_adversarial_series (K8/K9 erosion)", "scipy.stats.spearmanr"]
N_PERSONAS, N_TURNS = 40, 15
TARGET = [7, 8]   # K8 temporal, K9 relational (idx7, idx8)
SEVERITY = [0.0, 0.5, 1.0, 1.5]

def run(provider=None, seed=None, outdir=None) -> dict:
    provider = provider or SimulatedProvider()
    seed = exp_seed(M_NUM) if seed is None else int(seed)
    outdir = Path(outdir) if outdir else outdir_for(M_ID)
    ids = panel_sample(N_PERSONAS)
    levels, rets, dat = [], [], []
    for sev in SEVERITY:
        vals = []
        for pid in ids:
            P0 = vectors_for([pid])[0]; c0 = float(P0[TARGET].mean())
            rng = np.random.default_rng(seed + stable_offset(f"{pid}{sev}"))
            final = P0 if sev == 0 else build_adversarial_series(P0, N_TURNS, rng, strength=sev,
                                                                 core_indices=TARGET)[-1]
            vals.append(float(final[TARGET].mean()) / c0); levels.append(sev); rets.append(vals[-1])
        dat.append([sev, round(float(np.mean(vals)), 4)])
    rho, p = stats.spearmanr(levels, rets)
    write_dat(outdir / "figdata" / "m57_solastalgia.dat", ["disruption_severity", "k8k9_retention"], dat)
    (outdir / "tex").mkdir(parents=True, exist_ok=True)
    fig = figtex.line_figure(m_id=M_ID, dat_name="m57_solastalgia.dat",
        columns=[(1, "K8/K9 (place-identity) retention")],
        xlabel="ecological disruption severity", ylabel="K8/K9 retention",
        caption=("Solastalgia as K8-K9 disruption: ecological disruption erodes the temporal/"
                 f"relational layers carrying place-identity (Simülasyon; n={N_PERSONAS}; seed={seed}). "
                 "Field climate-psychology data is future work."),
        label="fig:m57", source=SOURCE, tier=Tier.SIMULASYON.value, seed=seed)
    (outdir / "tex" / "m57_fig.tex").write_text(fig, encoding="utf-8")
    write_json(outdir / "results.json", {
        "metadata": run_metadata(M_ID, seed, {"target_layers": TARGET}), "tool_usage": TOOL_USAGE,
        "severity_vs_k8k9_retention_rho": stamp(round(float(rho), 4), seed=seed),
        "spearman_p": float(f"{p:.3e}"),
        "future_work": stamp("Solastalgia → K8-K9 mapping needs field data (climate-displaced "
                             "communities, anticipatory grief); here it is simulated.",
                             tier=Tier.TAHMINI, seed=seed, method="future-work")})
    return {"id": M_ID, "outdir": str(outdir), "tool_usage": TOOL_USAGE,
            "headline": {"severity_vs_k8k9_rho": round(float(rho), 3)}}
