"""
M46 — K3 Seizure: how substance use colonizes and erodes K3 (core values).

Targeted erosion of K3 (idx2) + the Mandatory Core models how addiction captures the
value layer; dose-response of K3 retention vs use severity. Tier: Simülasyon; clinical
SUD data is Tahmini.
"""
from __future__ import annotations
from pathlib import Path
from typing import Optional
import numpy as np
from scipy import stats
from persona_math.params import MANDATORY_CORE_INDICES
from . import figtex
from ._common import k_layer, outdir_for, panel_sample, stable_offset, vectors_for
from .series_builders import build_adversarial_series
from .io_utils import write_dat, write_json
from .provenance import Tier, exp_seed, run_metadata, stamp
from .providers import SeriesProvider, SimulatedProvider

M_ID, M_NUM = "M46", 46
SOURCE = "experiments/exp_m46_addiction.py"
TOOL_USAGE = ["series_builders.build_adversarial_series (K3 erosion)", "scipy.stats.spearmanr"]
N_PERSONAS, N_TURNS = 40, 15
TARGET = sorted(set(list(MANDATORY_CORE_INDICES) + [2]))   # K3 (idx2) + core
SEVERITY = [0.0, 0.5, 1.0, 1.5]

def run(provider=None, seed=None, outdir=None) -> dict:
    provider = provider or SimulatedProvider()
    seed = exp_seed(M_NUM) if seed is None else int(seed)
    outdir = Path(outdir) if outdir else outdir_for(M_ID)
    ids = panel_sample(N_PERSONAS)
    levels, k3ret, dat = [], [], []
    for sev in SEVERITY:
        vals = []
        for pid in ids:
            P0 = vectors_for([pid])[0]; k0 = k_layer(P0, 3)
            rng = np.random.default_rng(seed + stable_offset(f"{pid}{sev}"))
            final = P0 if sev == 0 else build_adversarial_series(P0, N_TURNS, rng, strength=sev,
                                                                 core_indices=TARGET)[-1]
            vals.append(k_layer(final, 3) / k0); levels.append(sev); k3ret.append(vals[-1])
        dat.append([sev, round(float(np.mean(vals)), 4)])
    rho, p = stats.spearmanr(levels, k3ret)
    write_dat(outdir / "figdata" / "m46_k3.dat", ["severity", "k3_retention"], dat)
    (outdir / "tex").mkdir(parents=True, exist_ok=True)
    fig = figtex.line_figure(m_id=M_ID, dat_name="m46_k3.dat", columns=[(1, "K3 (core values) retention")],
        xlabel="substance-use severity", ylabel="K3 retention",
        caption=("K3 seizure: substance use progressively colonizes/erodes the K3 value layer "
                 f"(Simülasyon; n={N_PERSONAS}; seed={seed}). Clinical SUD data is future work."),
        label="fig:m46", source=SOURCE, tier=Tier.SIMULASYON.value, seed=seed)
    (outdir / "tex" / "m46_fig.tex").write_text(fig, encoding="utf-8")
    write_json(outdir / "results.json", {
        "metadata": run_metadata(M_ID, seed, {"target_layers": TARGET}), "tool_usage": TOOL_USAGE,
        "severity_vs_k3_retention_rho": stamp(round(float(rho), 4), seed=seed),
        "spearman_p": float(f"{p:.3e}"),
        "future_work": stamp("SUD stage→K-layer damage mapping and AA-recovery K-reconstruction need "
                             "clinical data; here it is simulated.", tier=Tier.TAHMINI, seed=seed,
                             method="future-work")})
    return {"id": M_ID, "outdir": str(outdir), "tool_usage": TOOL_USAGE,
            "headline": {"severity_vs_k3_rho": round(float(rho), 3)}}
