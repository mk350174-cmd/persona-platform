"""
M59 — Hard Problem, Personal Identity, and the Mandatory Core (three theses).

A philosophy-of-mind paper. Computational illustration: the GWT-ignition phase
transition (a candidate "minimum condition" for global broadcast / experience) across
the persona library, tied to K6. The hard problem and AI-consciousness questions are
left open and argued in prose. Tier: Simülasyon.
"""
from __future__ import annotations
from pathlib import Path
from typing import Optional
import numpy as np
from persona_math.consciousness import gwt_ignition
from . import figtex
from ._common import outdir_for, panel_sample, vectors_for
from .io_utils import write_dat, write_json
from .provenance import Tier, exp_seed, run_metadata, stamp
from .providers import SeriesProvider, SimulatedProvider

M_ID, M_NUM = "M59", 59
SOURCE = "experiments/exp_m59_consciousness.py"
TOOL_USAGE = ["consciousness.gwt_ignition"]
N_PANEL = 60
THRESHOLDS = [round(0.50 + 0.05 * i, 2) for i in range(9)] + [0.97, 0.99]

def _bm(P):
    return np.array([P[i * 10:(i + 1) * 10].mean() for i in range(10)])

def run(provider=None, seed=None, outdir=None) -> dict:
    provider = provider or SimulatedProvider()
    seed = exp_seed(M_NUM) if seed is None else int(seed)
    outdir = Path(outdir) if outdir else outdir_for(M_ID)
    bms = [_bm(P) for P in vectors_for(panel_sample(N_PANEL))]
    curve = []
    for thr in THRESHOLDS:
        frac = float(np.mean([bool(gwt_ignition(bm, threshold=thr)["ignition_occurred"]) for bm in bms]))
        curve.append([thr, round(frac, 4)])
    write_dat(outdir / "figdata" / "m59_ignition.dat", ["threshold", "ignition_fraction"], curve)
    above = [c[0] for c in curve if c[1] >= 0.5]
    critical = max(above) if above else None
    (outdir / "tex").mkdir(parents=True, exist_ok=True)
    fig = figtex.line_figure(m_id=M_ID, dat_name="m59_ignition.dat", columns=[(1, "ignition fraction")],
        xlabel="ignition threshold", ylabel="fraction with global broadcast",
        caption=("Global-workspace ignition as a candidate minimum condition for experience, as a "
                 f"phase transition across the library (critical threshold $\\approx${critical}; "
                 f"Simülasyon; seed={seed}). The hard problem + AI-consciousness questions are left "
                 "open philosophically."),
        label="fig:m59", source=SOURCE, tier=Tier.SIMULASYON.value, seed=seed)
    (outdir / "tex" / "m59_fig.tex").write_text(fig, encoding="utf-8")
    write_json(outdir / "results.json", {
        "metadata": run_metadata(M_ID, seed, {"n_panel": N_PANEL}), "tool_usage": TOOL_USAGE,
        "ignition_critical_threshold": stamp(critical, seed=seed,
                                             note="candidate minimum-broadcast condition"),
        "scope_note": stamp("The three theses (hard problem & K6, Parfit continuity, AI "
                            "consciousness) are philosophical; the AI-consciousness question is "
                            "explicitly left open.", tier=Tier.TAHMINI, seed=seed, method="scholarship")})
    return {"id": M_ID, "outdir": str(outdir), "tool_usage": TOOL_USAGE,
            "headline": {"ignition_critical_threshold": critical}}
