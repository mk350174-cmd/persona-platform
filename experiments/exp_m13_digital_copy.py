"""
M13 — Digital Copy Ontology (substrate independence / partial extension).

Transfers each persona to a "different substrate" at varying fidelity
(``lossy_transfer``) and measures continuity (CEID + cosine) vs fidelity, locating
the threshold X below which a copy is no longer continuous with the original.
Tier: Simülasyon (substrate = simulated lossy channel).
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import numpy as np

from persona_math.ceid import ceid_score

from . import figtex
from ._common import (individuation_recovery, lossy_transfer, outdir_for, panel_sample,
                      stable_offset, vectors_for)
from .io_utils import write_dat, write_json
from .provenance import Tier, exp_seed, run_metadata, stamp
from .providers import SeriesProvider, SimulatedProvider

M_ID, M_NUM = "M13", 13
SOURCE = "experiments/exp_m13_digital_copy.py"
TOOL_USAGE = ["_common.lossy_transfer", "ceid.ceid_score", "metrics.cosine_similarity"]

N_PERSONAS = 30
FIDELITIES = [round(0.1 * i, 1) for i in range(2, 11)]   # 0.2 … 1.0
CONTINUITY_THRESHOLD = 0.75   # CEID "STABLE" band


def run(provider: Optional[SeriesProvider] = None, seed: Optional[int] = None,
        outdir: Optional[Path] = None) -> dict:
    provider = provider or SimulatedProvider()
    seed = exp_seed(M_NUM) if seed is None else int(seed)
    outdir = Path(outdir) if outdir else outdir_for(M_ID)

    ids = panel_sample(N_PERSONAS)
    vecs = vectors_for(ids)
    pop_mean = np.mean(vecs, axis=0)
    dat, mean_indiv_by_f = [], {}
    for f in FIDELITIES:
        indiv, ceids = [], []
        for pid, P0 in zip(ids, vecs):
            rng = np.random.default_rng(seed + stable_offset(f"{pid}{f}"))
            copy = lossy_transfer(P0, f, rng)
            indiv.append(individuation_recovery(copy, P0, pop_mean))  # primary (discriminating)
            ceids.append(float(ceid_score(copy, P0)["CEID_score"]))   # secondary (saturates)
        mi = float(np.mean(indiv))
        mean_indiv_by_f[f] = mi
        dat.append([f, round(mi, 4), round(float(np.mean(ceids)), 4)])
    write_dat(outdir / "figdata" / "m13_continuity.dat",
              ["fidelity", "individuation_recovery", "ceid"], dat)

    # threshold: smallest fidelity whose mean individuation-recovery ≥ threshold
    above = [f for f in FIDELITIES if mean_indiv_by_f[f] >= CONTINUITY_THRESHOLD]
    threshold_x = min(above) if above else None

    (outdir / "tex").mkdir(parents=True, exist_ok=True)
    fig = figtex.line_figure(
        m_id=M_ID, dat_name="m13_continuity.dat",
        columns=[(1, "individuation recovery"), (2, "CEID (saturates)")],
        xlabel="transfer fidelity", ylabel="continuity",
        caption=("Partial-extension continuity vs transfer fidelity. Individuation recovery "
                 "(person-specific deviation captured) is the discriminating measure; raw CEID "
                 "saturates near 1.0 because personas share a generic backbone "
                 f"(Simülasyon; n={N_PERSONAS}; seed={seed})."),
        label="fig:m13_continuity", source=SOURCE, tier=Tier.SIMULASYON.value, seed=seed)
    (outdir / "tex" / "m13_continuity_fig.tex").write_text(fig, encoding="utf-8")

    results = {
        "metadata": run_metadata(M_ID, seed, {"n_personas": N_PERSONAS,
                                              "fidelities": FIDELITIES}),
        "tool_usage": TOOL_USAGE,
        "continuity_threshold_X": stamp(threshold_x, seed=seed,
                                        note=(f"min transfer fidelity with mean individuation-"
                                              f"recovery ≥ {CONTINUITY_THRESHOLD}")),
        "continuity_curve_individuation": {str(f): round(mean_indiv_by_f[f], 4) for f in FIDELITIES},
        "metric_note": stamp("Continuity is measured by individuation-recovery, not raw CEID: "
                             "CEID saturates (~1.0) for any structurally valid vector, so it does "
                             "not discriminate copy fidelity in this representation.",
                             tier=Tier.HESAPLANAN, seed=seed),
        "future_work": stamp("Real substrate-transfer continuity would require transferring a "
                             "persona across actual model architectures; here the substrate is a "
                             "simulated lossy channel.", tier=Tier.TAHMINI, seed=seed,
                             method="future-work"),
    }
    write_json(outdir / "results.json", results)
    return {"id": M_ID, "outdir": str(outdir), "tool_usage": TOOL_USAGE,
            "headline": {"continuity_threshold": threshold_x}}
