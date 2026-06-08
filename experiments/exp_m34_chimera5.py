"""
M34 — Chimera v2: five-motor synchronization, chaos, and phase diagram.

Models the five "motors" as coupled phase oscillators (Kuramoto) and computes the
synchronization order parameter r as a function of coupling K — a phase diagram from
desynchronized (low r) to synchronized (high r), with a critical coupling. Tier:
Hesaplanan (deterministic dynamical-systems simulation).
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import numpy as np

from . import figtex
from ._common import outdir_for
from .io_utils import write_dat, write_json
from .provenance import Tier, exp_seed, run_metadata, stamp
from .providers import SeriesProvider, SimulatedProvider

M_ID, M_NUM = "M34", 34
SOURCE = "experiments/exp_m34_chimera5.py"
TOOL_USAGE = ["Kuramoto 5-oscillator synchronization (numpy)"]

N_MOTORS = 5
COUPLINGS = [round(0.25 * i, 2) for i in range(0, 17)]   # 0 … 4
STEPS, DT = 3000, 0.05


def _order_parameter(K: float, rng: np.random.Generator) -> float:
    omega = rng.normal(0.0, 1.0, N_MOTORS)
    theta = rng.uniform(0.0, 2 * np.pi, N_MOTORS)
    for _ in range(STEPS):
        diff = theta[None, :] - theta[:, None]
        dtheta = omega + (K / N_MOTORS) * np.sin(diff).sum(axis=1)
        theta = theta + DT * dtheta
    return float(np.abs(np.mean(np.exp(1j * theta))))


def run(provider: Optional[SeriesProvider] = None, seed: Optional[int] = None,
        outdir: Optional[Path] = None) -> dict:
    provider = provider or SimulatedProvider()
    seed = exp_seed(M_NUM) if seed is None else int(seed)
    outdir = Path(outdir) if outdir else outdir_for(M_ID)

    rs = []
    for K in COUPLINGS:
        # fixed per-K seed → deterministic phase diagram
        rs.append(_order_parameter(K, np.random.default_rng(seed + int(K * 1000))))
    rs = np.array(rs)
    write_dat(outdir / "figdata" / "m34_phase.dat",
              ["coupling_K", "order_parameter_r"], np.column_stack([COUPLINGS, rs]))

    above = [k for k, r in zip(COUPLINGS, rs) if r >= 0.5]
    critical_K = min(above) if above else None

    (outdir / "tex").mkdir(parents=True, exist_ok=True)
    fig = figtex.line_figure(
        m_id=M_ID, dat_name="m34_phase.dat",
        columns=[(1, "order parameter $r$")],
        xlabel="motor coupling $K$", ylabel="synchronization $r$",
        caption=("Five-motor synchronization phase diagram: the order parameter rises from "
                 f"desynchronized to synchronized near $K_c\\approx{critical_K}$ "
                 f"(Hesaplanan; seed={seed})."),
        label="fig:m34", source=SOURCE, tier=Tier.HESAPLANAN.value, seed=seed)
    (outdir / "tex" / "m34_fig.tex").write_text(fig, encoding="utf-8")

    results = {
        "metadata": run_metadata(M_ID, seed, {"n_motors": N_MOTORS, "couplings": COUPLINGS}),
        "tool_usage": TOOL_USAGE,
        "critical_coupling_Kc": stamp(critical_K, tier=Tier.HESAPLANAN, seed=seed,
                                      note="min K with order parameter r≥0.5"),
        "order_parameter_curve": {str(k): round(float(r), 4) for k, r in zip(COUPLINGS, rs)},
    }
    write_json(outdir / "results.json", results)
    return {"id": M_ID, "outdir": str(outdir), "tool_usage": TOOL_USAGE,
            "headline": {"critical_coupling_Kc": critical_K, "r_max": round(float(rs.max()), 3)}}
