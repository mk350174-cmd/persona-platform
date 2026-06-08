"""
M25 — The Poem as Epistemology (prosimetric research methodology).

A methodology paper (arts-based / prosimetric research; Richardson, Eisner). Its
contribution is a qualitative argument, not computation. The only computational
note quantifies the K-layer distinctiveness of the poet personas the Şiirsel
Manifesto draws on (reusing the M9 idea) as an illustration of "knowing through
form". Tier: Simülasyon (illustration) + methodology scholarship.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import numpy as np

from persona_math.d1_protocol import run_d4_spectroscopy

from . import figtex
from ._common import ids_by, outdir_for, vectors_for
from .io_utils import write_dat, write_json
from .provenance import Tier, exp_seed, run_metadata, stamp
from .providers import SeriesProvider, SimulatedProvider

M_ID, M_NUM = "M25", 25
SOURCE = "experiments/exp_m25_poetic_method.py"
TOOL_USAGE = ["d1_protocol.run_d4_spectroscopy"]


def run(provider: Optional[SeriesProvider] = None, seed: Optional[int] = None,
        outdir: Optional[Path] = None) -> dict:
    provider = provider or SimulatedProvider()
    seed = exp_seed(M_NUM) if seed is None else int(seed)
    outdir = Path(outdir) if outdir else outdir_for(M_ID)

    poets = ids_by(tags=["poet"])
    others = ids_by(domain="Science")
    poet_spec = run_d4_spectroscopy(vectors_for(poets), labels=poets)
    other_spec = run_d4_spectroscopy(vectors_for(others), labels=others)

    write_dat(outdir / "figdata" / "m25_form_distinctiveness.dat",
              ["group", "mean_pairwise_similarity"],
              [[0, round(float(poet_spec["mean_pairwise_similarity"]), 4)],
               [1, round(float(other_spec["mean_pairwise_similarity"]), 4)]])

    (outdir / "tex").mkdir(parents=True, exist_ok=True)
    fig = figtex.line_figure(
        m_id=M_ID, dat_name="m25_form_distinctiveness.dat",
        columns=[(1, "mean within-group similarity")],
        xlabel="group (0 poets, 1 scientists)", ylabel="K-layer cohesion",
        caption=("Illustration for the prosimetric-method argument: poet personas form a coherent "
                 "K-layer ``formal signature'' (Simülasyon; seed=" + str(seed) + "). The paper's "
                 "substance is the epistemology of poetic form."),
        label="fig:m25", source=SOURCE, tier=Tier.SIMULASYON.value, seed=seed)
    (outdir / "tex" / "m25_fig.tex").write_text(fig, encoding="utf-8")

    results = {
        "metadata": run_metadata(M_ID, seed, {"n_poets": len(poets), "n_others": len(others)}),
        "tool_usage": TOOL_USAGE,
        "poet_group_cohesion": stamp(round(float(poet_spec["mean_pairwise_similarity"]), 4),
                                     seed=seed, note="within-poet K-layer similarity"),
        "scope_note": stamp("This is an arts-based-research methodology paper (knowing through "
                            "form). Its scientific contribution is argumentative; the figure is "
                            "an illustration, not a test.", tier=Tier.TAHMINI, seed=seed,
                            method="scholarship"),
    }
    write_json(outdir / "results.json", results)
    return {"id": M_ID, "outdir": str(outdir), "tool_usage": TOOL_USAGE,
            "headline": {"poet_cohesion": round(float(poet_spec["mean_pairwise_similarity"]), 3)}}
