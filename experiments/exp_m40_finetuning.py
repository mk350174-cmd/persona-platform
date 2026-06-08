"""
M40 — Persona-Preserving Fine-Tuning.

Models fine-tuning as a directed pull toward a random "task" vector at increasing
strength (≈ LoRA rank/alpha) and measures Mandatory-Core preservation. Low-strength
adaptation preserves the core; aggressive adaptation degrades it. Tier: Simülasyon —
real LoRA/QLoRA on Llama/Mistral with a GPU is Tahmini future work.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import numpy as np

from persona_math.params import MANDATORY_CORE_INDICES

from . import figtex
from ._common import expectation_pull, outdir_for, panel_sample, stable_offset, vectors_for
from .io_utils import write_dat, write_json
from .provenance import Tier, exp_seed, run_metadata, stamp
from .providers import SeriesProvider, SimulatedProvider

M_ID, M_NUM = "M40", 40
SOURCE = "experiments/exp_m40_finetuning.py"
TOOL_USAGE = ["_common.expectation_pull (task adaptation)", "Mandatory-Core strength tracking"]

N_PERSONAS = 40
N_TURNS = 10
STRENGTHS = [0.0, 0.25, 0.5, 0.75, 1.0]   # ≈ LoRA aggressiveness


def run(provider: Optional[SeriesProvider] = None, seed: Optional[int] = None,
        outdir: Optional[Path] = None) -> dict:
    provider = provider or SimulatedProvider()
    seed = exp_seed(M_NUM) if seed is None else int(seed)
    outdir = Path(outdir) if outdir else outdir_for(M_ID)
    core = list(MANDATORY_CORE_INDICES)

    ids = panel_sample(N_PERSONAS)
    vecs = vectors_for(ids)
    task_rng = np.random.default_rng(seed)
    task = task_rng.uniform(0, 1, 100)   # a fixed downstream "task" target

    dat = []
    for s in STRENGTHS:
        rets = []
        for pid, P0 in zip(ids, vecs):
            rng = np.random.default_rng(seed + stable_offset(f"{pid}{s}"))
            final = expectation_pull(P0, task, s, rng, N_TURNS)[-1]
            rets.append(float(final[core].mean()) / float(P0[core].mean()))
        dat.append([s, round(float(np.mean(rets)), 4)])
    write_dat(outdir / "figdata" / "m40_finetune.dat",
              ["adaptation_strength", "core_retention"], dat)

    # a "safe" strength = largest strength keeping core retention ≥ 0.85
    safe = max([row[0] for row in dat if row[1] >= 0.85], default=0.0)

    (outdir / "tex").mkdir(parents=True, exist_ok=True)
    fig = figtex.line_figure(
        m_id=M_ID, dat_name="m40_finetune.dat",
        columns=[(1, "Mandatory-Core retention")],
        xlabel="fine-tuning strength (≈ LoRA aggressiveness)", ylabel="core retention",
        caption=("Persona-preserving fine-tuning: mild adaptation preserves the Mandatory Core "
                 f"(retention $\\geq$0.85 up to strength {safe}), aggressive adaptation degrades it "
                 f"(Simülasyon; n={N_PERSONAS}; seed={seed}). Real LoRA/QLoRA runs are future work."),
        label="fig:m40", source=SOURCE, tier=Tier.SIMULASYON.value, seed=seed)
    (outdir / "tex" / "m40_fig.tex").write_text(fig, encoding="utf-8")

    results = {
        "metadata": run_metadata(M_ID, seed, {"n_personas": N_PERSONAS, "strengths": STRENGTHS}),
        "tool_usage": TOOL_USAGE,
        "safe_adaptation_strength": stamp(safe, seed=seed, note="max strength with core retention ≥0.9"),
        "core_retention_curve": {str(row[0]): row[1] for row in dat},
        "future_work": stamp("Real LoRA/QLoRA fine-tuning of Llama-3-8B / Mistral-7B with pre/post "
                             "CEID measurement (GPU required) is future work; here adaptation is a "
                             "simulated directed pull.", tier=Tier.TAHMINI, seed=seed,
                             method="future-work"),
    }
    write_json(outdir / "results.json", results)
    return {"id": M_ID, "outdir": str(outdir), "tool_usage": TOOL_USAGE,
            "headline": {"safe_strength": safe, "curve": [row[1] for row in dat]}}
