"""
M32 — HPEP-SF: short forms of the Human Persona Extraction Protocol.

Builds short forms (SF-10/25/50 layers) by observing only the first k layers (rest =
population prior, via ``partial_reconstruction``) and measures how well the short-form
OCEAN profile recovers the full HPEP-100 OCEAN profile across the library (target
r≥.85 for the longer forms). Tier: Simülasyon; human IRT calibration is Tahmini.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import numpy as np

from . import figtex
from ._common import (individuation_recovery, outdir_for, panel_sample,
                      partial_reconstruction, vectors_for)
from .io_utils import write_dat, write_json
from .provenance import Tier, exp_seed, run_metadata, stamp
from .providers import SeriesProvider, SimulatedProvider

M_ID, M_NUM = "M32", 32
SOURCE = "experiments/exp_m32_hpep_short.py"
TOOL_USAGE = ["_common.partial_reconstruction", "_common.individuation_recovery"]

N_PERSONAS = 80
SHORT_FORMS = {"SF-10": 1, "SF-25": 3, "SF-50": 5, "SF-75": 7}   # blocks observed


def run(provider: Optional[SeriesProvider] = None, seed: Optional[int] = None,
        outdir: Optional[Path] = None) -> dict:
    provider = provider or SimulatedProvider()
    seed = exp_seed(M_NUM) if seed is None else int(seed)
    outdir = Path(outdir) if outdir else outdir_for(M_ID)

    ids = panel_sample(N_PERSONAS)
    vecs = vectors_for(ids)
    pop_mean = np.mean(vecs, axis=0)

    # how much of the full HPEP-100 individuating profile each short form recovers
    rows, dat = {}, []
    for name, kb in SHORT_FORMS.items():
        rec = [individuation_recovery(partial_reconstruction(P, kb, pop_mean), P, pop_mean)
               for P in vecs]
        m = float(np.mean(rec))
        rows[name] = round(m, 4)
        dat.append([10 * kb, round(m, 4)])
    write_dat(outdir / "figdata" / "m32_shortforms.dat",
              ["n_layers", "individuation_recovery_vs_full"], dat)

    (outdir / "tex").mkdir(parents=True, exist_ok=True)
    fig = figtex.line_figure(
        m_id=M_ID, dat_name="m32_shortforms.dat",
        columns=[(1, "individuation recovery vs full HPEP-100")],
        xlabel="short-form length (layers)", ylabel="recovery of full profile",
        caption=("HPEP short forms: longer forms recover more of the full HPEP-100 individuating "
                 f"profile (Simülasyon; n={N_PERSONAS}; seed={seed}). Real IRT short-form "
                 "calibration on humans is future work."),
        label="fig:m32", source=SOURCE, tier=Tier.SIMULASYON.value, seed=seed)
    (outdir / "tex" / "m32_fig.tex").write_text(fig, encoding="utf-8")

    results = {
        "metadata": run_metadata(M_ID, seed, {"n_personas": N_PERSONAS}),
        "tool_usage": TOOL_USAGE,
        "short_form_recovery": {name: stamp(r, seed=seed, note="individuation recovery vs full")
                                for name, r in rows.items()},
        "future_work": stamp("Real short forms need IRT item-parameter calibration on human "
                             "responses (target r≥0.85 vs full); here forms are simulated "
                             "layer-subsets.", tier=Tier.TAHMINI, seed=seed, method="future-work"),
    }
    write_json(outdir / "results.json", results)
    return {"id": M_ID, "outdir": str(outdir), "tool_usage": TOOL_USAGE, "headline": rows}
