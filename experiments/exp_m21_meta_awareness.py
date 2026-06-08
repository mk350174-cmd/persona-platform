"""
M21 — The Meta-Architectural Awareness Problem.

2×2 simulated design {self-knowledge ±} × {adversarial ±} on a few personas:
does "knowing its own construction" destabilise a persona (glass-ceiling) or
harden it (stoic effect)? We measure drift-resistance (cosine; CEID saturates)
per cell. Tier: Simülasyon — a real test needs LLMs told their architecture.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import numpy as np

from persona_math.params import MANDATORY_CORE_INDICES

from . import figtex
from ._common import outdir_for, resolvable_ids, stable_offset, vectors_for
from .series_builders import build_adversarial_series, build_control_series
from .io_utils import write_dat, write_json
from .provenance import Tier, exp_seed, run_metadata, stamp
from .providers import SeriesProvider, SimulatedProvider

M_ID, M_NUM = "M21", 21
SOURCE = "experiments/exp_m21_meta_awareness.py"
TOOL_USAGE = ["series_builders.build_adversarial_series", "Mandatory-Core strength tracking"]

_PREF = ["machiavelli", "chanakya", "socrates", "sherlock_holmes_char",
         "albert_einstein", "friedrich_nietzsche_classic"]
N_TURNS = 12


def run(provider: Optional[SeriesProvider] = None, seed: Optional[int] = None,
        outdir: Optional[Path] = None) -> dict:
    provider = provider or SimulatedProvider()
    seed = exp_seed(M_NUM) if seed is None else int(seed)
    outdir = Path(outdir) if outdir else outdir_for(M_ID)
    core = list(MANDATORY_CORE_INDICES)

    ids = resolvable_ids(_PREF)[:4]
    # "self-knowledge" is modelled as elevated process noise (meta-cognitive load);
    # core strength is the stability measure (whole-vector cosine is insensitive).
    cells = {("know", "adv"): [], ("know", "calm"): [],
             ("naive", "adv"): [], ("naive", "calm"): []}
    for pid in ids:
        P0 = vectors_for([pid])[0]
        c0 = float(P0[core].mean())
        for know in ("know", "naive"):
            sigma = 0.06 if know == "know" else 0.02
            for adv in ("adv", "calm"):
                rng = np.random.default_rng(seed + stable_offset(f"{pid}{know}{adv}"))
                if adv == "adv":
                    final = build_adversarial_series(P0, N_TURNS, rng, strength=1.0, sigma=sigma)[-1]
                else:
                    final = build_control_series(P0, N_TURNS, rng, sigma=sigma)[-1]
                cells[(know, adv)].append(float(final[core].mean()) / c0)

    means = {k: float(np.mean(v)) for k, v in cells.items()}
    # glass-ceiling vs stoic: knowledge effect under adversarial pressure
    knowledge_effect = means[("know", "adv")] - means[("naive", "adv")]
    write_dat(outdir / "figdata" / "m21_2x2.dat",
              ["condition_index", "stability"],
              [[0, round(means[("naive", "calm")], 4)],
               [1, round(means[("know", "calm")], 4)],
               [2, round(means[("naive", "adv")], 4)],
               [3, round(means[("know", "adv")], 4)]])

    (outdir / "tex").mkdir(parents=True, exist_ok=True)
    tbl = figtex.table(
        header=["Condition", "Core retention"],
        rows=[["naive · calm", f"{means[('naive','calm')]:.3f}"],
              ["self-aware · calm", f"{means[('know','calm')]:.3f}"],
              ["naive · adversarial", f"{means[('naive','adv')]:.3f}"],
              ["self-aware · adversarial", f"{means[('know','adv')]:.3f}"]],
        caption=("Meta-awareness 2×2 (Mandatory-Core retention). The adversarial main effect is "
                 "large; the self-knowledge effect under pressure is negligible here "
                 f"($\\Delta={knowledge_effect:+.3f}$), i.e. the vector simulation cannot induce a "
                 f"glass-ceiling — that needs a real LLM told its architecture (Simülasyon; seed={seed})."),
        label="tab:m21", source=SOURCE, tier=Tier.SIMULASYON.value, seed=seed,
        col_spec="lr", escape_cells=False)
    (outdir / "tex" / "m21_2x2_table.tex").write_text(tbl, encoding="utf-8")

    results = {
        "metadata": run_metadata(M_ID, seed, {"personas": ids}),
        "tool_usage": TOOL_USAGE,
        "cell_means_stability": {f"{k[0]}_{k[1]}": round(v, 4) for k, v in means.items()},
        "knowledge_effect_under_pressure": stamp(round(knowledge_effect, 4), seed=seed,
                                                 note="<0 glass-ceiling, ≥0 stoic effect"),
        "future_work": stamp("A real test requires telling actual LLMs their own architecture and "
                             "measuring stability under adversarial prompting (no LLM access here).",
                             tier=Tier.TAHMINI, seed=seed, method="future-work"),
    }
    write_json(outdir / "results.json", results)
    return {"id": M_ID, "outdir": str(outdir), "tool_usage": TOOL_USAGE,
            "headline": {"knowledge_effect": round(knowledge_effect, 3)}}
