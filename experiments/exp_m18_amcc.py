"""
M18 — aMCC as Neural Substrate of the Mandatory Core.

WEAK harness by design: NeuroImage needs real fMRI / a meta-analysis of aMCC
studies, which cannot be produced here — that is flagged as Tahmini future work
(the user's own note: else submit to Cortex). The only computational contribution
is an illustration that K6 (Virtù, block index 5) activation predicts simulated
core robustness across the library, motivating the aMCC↔K6 anchoring hypothesis.
Tier: Simülasyon for the illustration; the neuroscience is Tahmini.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import numpy as np
from scipy import stats

from persona_math.params import MANDATORY_CORE_INDICES

from . import figtex
from ._common import k_layer, outdir_for, panel_sample, vectors_for
from .io_utils import write_dat, write_json
from .provenance import Tier, exp_seed, run_metadata, stamp
from .providers import SeriesProvider, SimulatedProvider

M_ID, M_NUM = "M18", 18
SOURCE = "experiments/exp_m18_amcc.py"
TOOL_USAGE = ["_common.k_layer", "scipy.stats.pearsonr"]

N_PERSONAS = 60
K6_INDEX = 6   # K6 "Virtù / Archetypal Foundation" = K-layer 6 → index 5 (KN = idx N-1)


def run(provider: Optional[SeriesProvider] = None, seed: Optional[int] = None,
        outdir: Optional[Path] = None) -> dict:
    provider = provider or SimulatedProvider()
    seed = exp_seed(M_NUM) if seed is None else int(seed)
    outdir = Path(outdir) if outdir else outdir_for(M_ID)
    core = list(MANDATORY_CORE_INDICES)

    ids = panel_sample(N_PERSONAS)
    vecs = vectors_for(ids)
    # Structural claim only: does K6 (Virtù) co-vary with Mandatory-Core strength?
    # A positive structural link motivates the aMCC↔core anchoring hypothesis without
    # claiming dynamic robustness (K6 is not itself a core layer).
    k6 = np.array([k_layer(P0, K6_INDEX) for P0 in vecs])
    core_strength = np.array([float(P0[core].mean()) for P0 in vecs])
    r, p = stats.pearsonr(k6, core_strength)

    order = np.argsort(k6)
    write_dat(outdir / "figdata" / "m18_k6_core.dat",
              ["k6_activation", "core_strength"],
              np.column_stack([k6[order], core_strength[order]]))

    (outdir / "tex").mkdir(parents=True, exist_ok=True)
    fig = figtex.line_figure(
        m_id=M_ID, dat_name="m18_k6_core.dat",
        columns=[(1, "Mandatory-Core strength")],
        xlabel="K6 (Virt\\`u) activation", ylabel="Mandatory-Core strength",
        caption=("Structural illustration: K6 (Virt\\`u) co-varies with Mandatory-Core strength "
                 f"(Pearson $r={r:.2f}$), motivating the aMCC$\\leftrightarrow$core anchoring "
                 f"hypothesis (Simülasyon; n={N_PERSONAS}; seed={seed}). NOT fMRI data."),
        label="fig:m18_k6", source=SOURCE, tier=Tier.SIMULASYON.value, seed=seed)
    (outdir / "tex" / "m18_k6_fig.tex").write_text(fig, encoding="utf-8")

    results = {
        "metadata": run_metadata(M_ID, seed, {"n_personas": N_PERSONAS, "k6_index": K6_INDEX}),
        "tool_usage": TOOL_USAGE,
        "k6_vs_core_strength": {
            "pearson_r": stamp(round(float(r), 4), seed=seed,
                               note="structural: K6 (Virtù) vs Mandatory-Core strength"),
            "pearson_p": float(f"{p:.3e}"),
        },
        "future_work": stamp("The core claim (aMCC as neural substrate of the Mandatory Core) "
                             "requires real fMRI data or a meta-analysis of aMCC activation "
                             "studies (e.g. Touroutoglou). NOT performed here — submit to "
                             "NeuroImage only with such data, else Cortex.",
                             tier=Tier.TAHMINI, seed=seed, method="future-work"),
    }
    write_json(outdir / "results.json", results)
    return {"id": M_ID, "outdir": str(outdir), "tool_usage": TOOL_USAGE,
            "headline": {"k6_vs_core_strength_r": round(float(r), 3)}}
