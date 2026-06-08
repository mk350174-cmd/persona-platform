"""
M14 — Public Data Is Not Consent (persona-extraction scale).

Quantifies "how much data extracts how much identity": reconstruct each persona
from only k observed blocks (``partial_reconstruction``, rest = population mean)
and measure reconstruction fidelity (CEID + cosine) vs the fraction of data
observed. The legal analysis (GDPR/CCPA/KVKK) is the paper's qualitative
contribution, not computed here. Tier: Simülasyon.
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

M_ID, M_NUM = "M14", 14
SOURCE = "experiments/exp_m14_consent.py"
TOOL_USAGE = ["_common.partial_reconstruction", "_common.individuation_recovery"]

N_PERSONAS = 40
K_RANGE = list(range(0, 11))   # blocks observed: 0 … 10 (= fraction 0 … 1.0)


def run(provider: Optional[SeriesProvider] = None, seed: Optional[int] = None,
        outdir: Optional[Path] = None) -> dict:
    provider = provider or SimulatedProvider()
    seed = exp_seed(M_NUM) if seed is None else int(seed)
    outdir = Path(outdir) if outdir else outdir_for(M_ID)

    ids = panel_sample(N_PERSONAS)
    vecs = vectors_for(ids)
    pop_mean = np.mean(vecs, axis=0)

    dat = []
    for k in K_RANGE:
        indiv = [individuation_recovery(partial_reconstruction(P0, k, pop_mean), P0, pop_mean)
                 for P0 in vecs]
        dat.append([k / 10.0, round(float(np.mean(indiv)), 4)])
    write_dat(outdir / "figdata" / "m14_extraction.dat",
              ["data_fraction", "individuation_recovery"], dat)

    # fraction of personal data at which most individuating identity is reconstructable
    half = next((row[0] for row in dat if row[1] >= 0.75), None)

    (outdir / "tex").mkdir(parents=True, exist_ok=True)
    fig = figtex.line_figure(
        m_id=M_ID, dat_name="m14_extraction.dat",
        columns=[(1, "individuation recovery")],
        xlabel="fraction of persona data observed", ylabel="identity reconstructed",
        caption=("Persona-extraction scale: how much individuating identity (deviation from the "
                 "population) is reconstructable from a fraction of observed data — quantifying "
                 f"that public fragments already enable extraction (Simülasyon; n={N_PERSONAS}; "
                 f"seed={seed})."),
        label="fig:m14_extraction", source=SOURCE, tier=Tier.SIMULASYON.value, seed=seed)
    (outdir / "tex" / "m14_extraction_fig.tex").write_text(fig, encoding="utf-8")

    results = {
        "metadata": run_metadata(M_ID, seed, {"n_personas": N_PERSONAS}),
        "tool_usage": TOOL_USAGE,
        "data_fraction_for_075_individuation": stamp(half, seed=seed,
                                                     note="data fraction at which individuation-recovery ≥ 0.75"),
        "extraction_curve_individuation": {str(row[0]): row[1] for row in dat},
        "scope_note": stamp("GDPR/CCPA/KVKK comparison and the 'public data ≠ consent' argument "
                            "are the paper's legal-ethical scholarship — qualitative, not computed.",
                            tier=Tier.TAHMINI, seed=seed, method="scholarship"),
    }
    write_json(outdir / "results.json", results)
    return {"id": M_ID, "outdir": str(outdir), "tool_usage": TOOL_USAGE,
            "headline": {"data_fraction_for_075": half}}
