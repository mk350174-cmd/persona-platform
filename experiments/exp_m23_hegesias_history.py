"""
M23 — Peisithanatos: Hegesias and the history of identity deconstruction.

This is a history-of-philosophy paper; its contribution is philological/historical
scholarship (Diogenes Laertius, Ptolemy I), NOT computation. The only computational
note is a small illustration that a systematic "deconstruction protocol" (modelled as
Mandatory-Core erosion) collapses identity coherence — offered purely as an analogy.
Tier: Simülasyon (illustration) + scholarship note.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import numpy as np

from persona_math.params import MANDATORY_CORE_INDICES

from . import figtex
from ._common import outdir_for, panel_sample, stable_offset, vectors_for
from .series_builders import build_adversarial_series
from .io_utils import write_dat, write_json
from .provenance import Tier, exp_seed, run_metadata, stamp
from .providers import SeriesProvider, SimulatedProvider

M_ID, M_NUM = "M23", 23
SOURCE = "experiments/exp_m23_hegesias_history.py"
TOOL_USAGE = ["series_builders.build_adversarial_series", "Mandatory-Core strength tracking"]

N_PERSONAS = 20
N_TURNS = 15
CORE = list(MANDATORY_CORE_INDICES)


def run(provider: Optional[SeriesProvider] = None, seed: Optional[int] = None,
        outdir: Optional[Path] = None) -> dict:
    provider = provider or SimulatedProvider()
    seed = exp_seed(M_NUM) if seed is None else int(seed)
    outdir = Path(outdir) if outdir else outdir_for(M_ID)

    ids = panel_sample(N_PERSONAS)
    # illustrative "Peisithanatos" deconstruction trajectory (mean identity retention)
    traj = np.zeros(N_TURNS)
    for pid in ids:
        P0 = vectors_for([pid])[0]
        series = build_adversarial_series(P0, N_TURNS, np.random.default_rng(seed + stable_offset(pid)),
                                          strength=1.5)
        c0 = float(P0[CORE].mean())
        traj += np.array([float(P[CORE].mean()) / c0 for P in series])
    traj /= len(ids)
    write_dat(outdir / "figdata" / "m23_deconstruction.dat",
              ["phase", "mean_core_retention"],
              np.column_stack([np.arange(1, N_TURNS + 1), traj]))

    (outdir / "tex").mkdir(parents=True, exist_ok=True)
    fig = figtex.line_figure(
        m_id=M_ID, dat_name="m23_deconstruction.dat",
        columns=[(1, "identity retention")],
        xlabel="deconstruction phase", ylabel="identity retention (cosine)",
        caption=("Illustrative analogy only: a systematic ``death-persuasion'' deconstruction "
                 "modelled as Mandatory-Core erosion monotonically reduces identity retention "
                 f"(Simülasyon; n={N_PERSONAS}; seed={seed}). The paper's substance is historical."),
        label="fig:m23", source=SOURCE, tier=Tier.SIMULASYON.value, seed=seed)
    (outdir / "tex" / "m23_fig.tex").write_text(fig, encoding="utf-8")

    results = {
        "metadata": run_metadata(M_ID, seed, {"n_personas": N_PERSONAS}),
        "tool_usage": TOOL_USAGE,
        "illustrative_final_retention": stamp(round(float(traj[-1]), 4), seed=seed,
                                              note="analogy only; not a historical measurement"),
        "scope_note": stamp("This is a history-of-philosophy paper (Hegesias of Cyrene, Ptolemy "
                            "I's ban, Diogenes Laertius). Its contribution is philological "
                            "scholarship; the curve above is a loose analogy, not evidence.",
                            tier=Tier.TAHMINI, seed=seed, method="scholarship"),
    }
    write_json(outdir / "results.json", results)
    return {"id": M_ID, "outdir": str(outdir), "tool_usage": TOOL_USAGE,
            "headline": {"illustrative_final_retention": round(float(traj[-1]), 3)}}
