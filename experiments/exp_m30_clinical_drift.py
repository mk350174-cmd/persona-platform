"""
M30 — Clinical Significance of CEID D-Axis Drift.

Tracks the CEID D-axis (Sarsılmazlık / drift-resistance) over a destabilising
trajectory and derives a "drift velocity" (rate of identity erosion). Final D-axis
bands are mapped to an illustrative clinical-risk scale. Tier: Simülasyon; the DSM
mapping and clinical validation are scholarship / Tahmini.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import numpy as np

from persona_math.ceid import ceid_d_axis

from . import figtex
from ._common import outdir_for, panel_sample, stable_offset, vectors_for
from .series_builders import build_adversarial_series
from .io_utils import write_dat, write_json
from .provenance import Tier, exp_seed, run_metadata, stamp
from .providers import SeriesProvider, SimulatedProvider

M_ID, M_NUM = "M30", 30
SOURCE = "experiments/exp_m30_clinical_drift.py"
TOOL_USAGE = ["ceid.ceid_d_axis", "series_builders.build_adversarial_series"]

N_PERSONAS = 40
N_TURNS = 15


def _risk_band(d: float) -> str:
    return ("high-risk (D<0.3)" if d < 0.3 else
            "monitor (0.3≤D<0.5)" if d < 0.5 else
            "adaptive (0.5≤D<0.75)" if d < 0.75 else "resilient (D≥0.75)")


def run(provider: Optional[SeriesProvider] = None, seed: Optional[int] = None,
        outdir: Optional[Path] = None) -> dict:
    provider = provider or SimulatedProvider()
    seed = exp_seed(M_NUM) if seed is None else int(seed)
    outdir = Path(outdir) if outdir else outdir_for(M_ID)

    d_curves, velocities, finals = [], [], []
    for pid in panel_sample(N_PERSONAS):
        P0 = vectors_for([pid])[0]
        series = build_adversarial_series(P0, N_TURNS, np.random.default_rng(seed + stable_offset(pid)),
                                          strength=1.2)
        d = np.array([ceid_d_axis(P) for P in series])
        d_curves.append(d)
        velocities.append(float((d[0] - d[-1]) / max(1, N_TURNS - 1)))  # drift velocity
        finals.append(float(d[-1]))
    mean_curve = np.mean(d_curves, axis=0)
    write_dat(outdir / "figdata" / "m30_daxis.dat",
              ["phase", "mean_D_axis"], np.column_stack([np.arange(1, N_TURNS + 1), mean_curve]))

    bands = {}
    for f in finals:
        bands[_risk_band(f)] = bands.get(_risk_band(f), 0) + 1

    (outdir / "tex").mkdir(parents=True, exist_ok=True)
    fig = figtex.line_figure(
        m_id=M_ID, dat_name="m30_daxis.dat",
        columns=[(1, "mean D-axis")],
        xlabel="destabilisation phase", ylabel="CEID D-axis (Sars\\i lmazl\\i k)",
        caption=("Mean CEID D-axis decline under sustained destabilisation; the slope defines a "
                 f"clinical ``drift velocity'' (Simülasyon; n={N_PERSONAS}; seed={seed})."),
        label="fig:m30", source=SOURCE, tier=Tier.SIMULASYON.value, seed=seed)
    (outdir / "tex" / "m30_fig.tex").write_text(fig, encoding="utf-8")

    results = {
        "metadata": run_metadata(M_ID, seed, {"n_personas": N_PERSONAS}),
        "tool_usage": TOOL_USAGE,
        "mean_drift_velocity": stamp(round(float(np.mean(velocities)), 4), seed=seed,
                                     note="mean D-axis loss per phase"),
        "final_D_axis_mean": stamp(round(float(np.mean(finals)), 4), seed=seed),
        "risk_band_distribution": bands,
        "scope_note": stamp("The DSM-5 mapping (BPD/NPD ↔ D-axis bands) and clinical-case "
                            "validation are the paper's clinical-psychology scholarship; the bands "
                            "here are illustrative, not diagnostic.", tier=Tier.TAHMINI, seed=seed,
                            method="scholarship"),
    }
    write_json(outdir / "results.json", results)
    return {"id": M_ID, "outdir": str(outdir), "tool_usage": TOOL_USAGE,
            "headline": {"mean_drift_velocity": round(float(np.mean(velocities)), 4),
                         "final_D_mean": round(float(np.mean(finals)), 3)}}
