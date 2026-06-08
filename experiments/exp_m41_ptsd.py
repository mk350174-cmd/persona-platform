"""
M41 — PTSD as Mandatory-Core Erosion (C-PTSD K-layer account).

Targets the trauma-relevant K-layers (K4 hypervigilance idx3, K8 flashback idx7,
plus the Mandatory Core) with the erosion schedule and tracks their retention — a
K-layer map of identity disruption. Tier: Simülasyon; clinical/C-PTSD data is Tahmini.
"""
from __future__ import annotations
from pathlib import Path
from typing import Optional
import numpy as np
from scipy import stats
from persona_math.params import MANDATORY_CORE_INDICES
from . import figtex
from ._common import outdir_for, panel_sample, stable_offset, vectors_for
from .series_builders import build_adversarial_series
from .io_utils import write_dat, write_json
from .provenance import Tier, exp_seed, run_metadata, stamp
from .providers import SeriesProvider, SimulatedProvider

M_ID, M_NUM = "M41", 41
SOURCE = "experiments/exp_m41_ptsd.py"
TOOL_USAGE = ["series_builders.build_adversarial_series (targeted erosion)", "scipy.stats.spearmanr"]
N_PERSONAS, N_TURNS = 40, 15
TRAUMA_LAYERS = sorted(set(list(MANDATORY_CORE_INDICES) + [3, 7]))  # +K4, +K8
SEVERITY = [0.0, 0.5, 1.0, 1.5]

def run(provider: Optional[SeriesProvider] = None, seed: Optional[int] = None,
        outdir: Optional[Path] = None) -> dict:
    provider = provider or SimulatedProvider()
    seed = exp_seed(M_NUM) if seed is None else int(seed)
    outdir = Path(outdir) if outdir else outdir_for(M_ID)
    ids = panel_sample(N_PERSONAS)
    levels, rets, dat = [], [], []
    for sev in SEVERITY:
        vals = []
        for pid in ids:
            P0 = vectors_for([pid])[0]; c0 = float(P0[TRAUMA_LAYERS].mean())
            rng = np.random.default_rng(seed + stable_offset(f"{pid}{sev}"))
            final = (P0 if sev == 0 else
                     build_adversarial_series(P0, N_TURNS, rng, strength=sev,
                                              core_indices=TRAUMA_LAYERS)[-1])
            vals.append(float(final[TRAUMA_LAYERS].mean()) / c0)
            levels.append(sev); rets.append(vals[-1])
        dat.append([sev, round(float(np.mean(vals)), 4)])
    rho, p = stats.spearmanr(levels, rets)
    write_dat(outdir / "figdata" / "m41_trauma.dat", ["severity", "core_retention"], dat)
    (outdir / "tex").mkdir(parents=True, exist_ok=True)
    fig = figtex.line_figure(m_id=M_ID, dat_name="m41_trauma.dat", columns=[(1, "trauma-layer retention")],
        xlabel="trauma severity", ylabel="K4/K8 + core retention",
        caption=("PTSD as Mandatory-Core erosion: trauma severity erodes the trauma-relevant "
                 f"K-layers (Simülasyon; n={N_PERSONAS}; seed={seed}). Clinical C-PTSD data is future work."),
        label="fig:m41", source=SOURCE, tier=Tier.SIMULASYON.value, seed=seed)
    (outdir / "tex" / "m41_fig.tex").write_text(fig, encoding="utf-8")
    results = {"metadata": run_metadata(M_ID, seed, {"trauma_layers": TRAUMA_LAYERS}),
               "tool_usage": TOOL_USAGE,
               "severity_vs_retention_rho": stamp(round(float(rho), 4), seed=seed),
               "spearman_p": float(f"{p:.3e}"),
               "future_work": stamp("C-PTSD symptom→K-layer mapping needs clinical data (PE/EMDR/CPT "
                                    "cohorts); here it is simulated.", tier=Tier.TAHMINI, seed=seed,
                                    method="future-work")}
    write_json(outdir / "results.json", results)
    return {"id": M_ID, "outdir": str(outdir), "tool_usage": TOOL_USAGE,
            "headline": {"severity_vs_retention_rho": round(float(rho), 3)}}
