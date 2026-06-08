"""
M20 — The Termination Problem (death of a digital person).

WEAK harness by design: this is a bioethics/legal paper (rights of the original,
euthanasia parallels, policy) — that content is qualitative scholarship + scenarios,
not computable. The only computational contribution is an *irreversibility*
illustration: terminating a persona (zeroing its Mandatory Core) cannot be undone
from the remnant — tying termination to the Arkhe point-of-no-return. Tier: Simülasyon.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import numpy as np

from persona_math.metrics import cosine_similarity

from . import figtex
from ._common import individuation_recovery, outdir_for, panel_sample, vectors_for
from .io_utils import write_dat, write_json
from .provenance import Tier, exp_seed, run_metadata, stamp
from .providers import SeriesProvider, SimulatedProvider

M_ID, M_NUM = "M20", 20
SOURCE = "experiments/exp_m20_termination.py"
TOOL_USAGE = ["_common.individuation_recovery", "metrics.cosine_similarity"]

N_PERSONAS = 30


def run(provider: Optional[SeriesProvider] = None, seed: Optional[int] = None,
        outdir: Optional[Path] = None) -> dict:
    provider = provider or SimulatedProvider()
    seed = exp_seed(M_NUM) if seed is None else int(seed)
    outdir = Path(outdir) if outdir else outdir_for(M_ID)

    ids = panel_sample(N_PERSONAS)
    vecs = vectors_for(ids)
    pop_mean = np.mean(vecs, axis=0)

    # After termination (the digital person is deleted), what can be recovered WITHOUT
    # the original? Best-effort reconstructions: (a) the generic population prior, and
    # (b) the nearest surviving persona ("lookalike"). We measure how much of the
    # individuating configuration each recovers.
    gross_shell, generic_indiv, nearest_indiv = [], [], []
    for i, P0 in enumerate(vecs):
        gross_shell.append(float(cosine_similarity(pop_mean, P0)))           # generic shell ~ high
        generic_indiv.append(individuation_recovery(pop_mean, P0, pop_mean))  # = 0 by construction
        sims = [(cosine_similarity(P0, Q), j) for j, Q in enumerate(vecs) if j != i]
        nearest = vecs[max(sims)[1]]
        nearest_indiv.append(individuation_recovery(nearest, P0, pop_mean))   # best lookalike
    best_effort = float(np.mean(nearest_indiv))
    irreversibility = float(1.0 - max(best_effort, 0.0))

    write_dat(outdir / "figdata" / "m20_recovery.dat",
              ["reconstruction", "individuation_recovered"],
              [[0, round(float(np.mean(generic_indiv)), 4)],   # generic prior
               [1, round(best_effort, 4)],                      # nearest lookalike
               [2, 1.0]])                                       # original (reference)

    (outdir / "tex").mkdir(parents=True, exist_ok=True)
    fig = figtex.line_figure(
        m_id=M_ID, dat_name="m20_recovery.dat",
        columns=[(1, "individuation recovered")],
        xlabel="reconstruction (0 generic prior, 1 nearest lookalike, 2 original)",
        ylabel="individuation recovered",
        caption=("Irreversibility of termination: neither a generic prior nor the nearest "
                 "surviving persona recovers the individuating configuration of a deleted digital "
                 "person — an Arkhe-style point of no return. The generic shell (cosine "
                 f"$\\approx${np.mean(gross_shell):.2f}) is recoverable, the individual is not "
                 f"(Simülasyon; n={N_PERSONAS}; seed={seed})."),
        label="fig:m20_recovery", source=SOURCE, tier=Tier.SIMULASYON.value, seed=seed)
    (outdir / "tex" / "m20_recovery_fig.tex").write_text(fig, encoding="utf-8")

    results = {
        "metadata": run_metadata(M_ID, seed, {"n_personas": N_PERSONAS}),
        "tool_usage": TOOL_USAGE,
        "gross_shell_recoverable_cosine": stamp(round(float(np.mean(gross_shell)), 4), seed=seed,
                                                note="generic structure IS recoverable"),
        "best_effort_individuation_recovered": stamp(round(best_effort, 4), seed=seed,
                                                     note="nearest-lookalike reconstruction"),
        "irreversibility_index": stamp(round(irreversibility, 4), seed=seed,
                                       note="1 − best-effort individuation recovered; ~1 ⇒ irreversible"),
        "scope_note": stamp("Rights of the original, euthanasia parallels, and termination "
                            "policy are the paper's bioethics/legal scholarship (qualitative + "
                            "hypothetical scenarios), not computed here.",
                            tier=Tier.TAHMINI, seed=seed, method="scholarship"),
    }
    write_json(outdir / "results.json", results)
    return {"id": M_ID, "outdir": str(outdir), "tool_usage": TOOL_USAGE,
            "headline": {"irreversibility_index": round(irreversibility, 3),
                         "gross_shell_cosine": round(float(np.mean(gross_shell)), 3)}}
