"""
M27 — Organizational Persona (K-layer architecture for institutional identity).

Applies the Mandatory-Core stability machinery to three synthetic organizational
archetypes — a core-preserver, a collapser, and a transformer — and tracks identity
retention under sustained pressure. The concrete company cases (Apple/Nokia/IBM) are
the paper's organization-theory scholarship. Tier: Simülasyon.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import numpy as np

from persona_math.params import MANDATORY_CORE_INDICES

from . import figtex
from ._common import make_synthetic_population, outdir_for
from .series_builders import build_adversarial_series, build_control_series
from .io_utils import write_dat, write_json
from .provenance import Tier, exp_seed, run_metadata, stamp
from .providers import SeriesProvider, SimulatedProvider

M_ID, M_NUM = "M27", 27
SOURCE = "experiments/exp_m27_organizational.py"
TOOL_USAGE = ["series_builders.build_adversarial_series", "Mandatory-Core strength tracking"]

N_TURNS = 15


def run(provider: Optional[SeriesProvider] = None, seed: Optional[int] = None,
        outdir: Optional[Path] = None) -> dict:
    provider = provider or SimulatedProvider()
    seed = exp_seed(M_NUM) if seed is None else int(seed)
    outdir = Path(outdir) if outdir else outdir_for(M_ID)
    core = list(MANDATORY_CORE_INDICES)

    base = make_synthetic_population(1, seed)[0]
    preserver = base.copy(); preserver[core] = np.clip(preserver[core] + 0.2, 0, 1)
    collapser = base.copy(); collapser[core] = np.clip(collapser[core] - 0.2, 0, 1)
    transformer = base.copy()

    rng = np.random.default_rng(seed)
    archetypes = {"preserver": preserver, "collapser": collapser, "transformer": transformer}
    traj = {}
    for name, P0 in archetypes.items():
        if name == "preserver":
            series = build_control_series(P0, N_TURNS, rng)
        elif name == "collapser":
            series = build_adversarial_series(P0, N_TURNS, rng, strength=1.5)
        else:  # transformer: moderate pressure (adapts without full collapse)
            series = build_adversarial_series(P0, N_TURNS, rng, strength=0.6)
        # institutional identity = Mandatory-Core strength (whole-vector cosine is
        # insensitive to core-only erosion; cf. M11's identity-capital measure)
        c0 = float(P0[core].mean())
        traj[name] = np.array([float(P[core].mean()) / c0 for P in series])

    write_dat(outdir / "figdata" / "m27_org.dat",
              ["phase", "preserver", "collapser", "transformer"],
              np.column_stack([np.arange(1, N_TURNS + 1),
                               traj["preserver"], traj["collapser"], traj["transformer"]]))

    (outdir / "tex").mkdir(parents=True, exist_ok=True)
    fig = figtex.line_figure(
        m_id=M_ID, dat_name="m27_org.dat",
        columns=[(1, "preserver (Apple-like)"), (2, "collapser (Nokia-like)"),
                 (3, "transformer (IBM-like)")],
        xlabel="organizational pressure phase", ylabel="institutional identity retention",
        caption=("Three organizational archetypes' Mandatory-Core retention under sustained "
                 f"pressure (Simülasyon; seed={seed}). The company cases are scholarship."),
        label="fig:m27", source=SOURCE, tier=Tier.SIMULASYON.value, seed=seed)
    (outdir / "tex" / "m27_fig.tex").write_text(fig, encoding="utf-8")

    results = {
        "metadata": run_metadata(M_ID, seed, {"archetypes": list(archetypes)}),
        "tool_usage": TOOL_USAGE,
        "final_retention": {name: stamp(round(float(t[-1]), 4), seed=seed)
                            for name, t in traj.items()},
        "scope_note": stamp("Apple/Nokia/IBM identity-maintenance cases and the Albert & Whetten / "
                            "DiMaggio & Powell theory integration are the paper's qualitative "
                            "organization-science contribution.", tier=Tier.TAHMINI, seed=seed,
                            method="scholarship"),
    }
    write_json(outdir / "results.json", results)
    return {"id": M_ID, "outdir": str(outdir), "tool_usage": TOOL_USAGE,
            "headline": {name: round(float(t[-1]), 3) for name, t in traj.items()}}
