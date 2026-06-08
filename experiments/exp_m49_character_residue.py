"""
M49 — Character Residue and K-Layer Cross-Contamination.

Models long-term role-play as a transfer of the actor toward a character vector:
Stanislavski "merger" (high blend → high residue) vs Brecht "alienation" (low blend →
low residue). Residue = how much of the character's individuating profile persists in
the actor. Tier: Simülasyon; actor data is Tahmini.
"""
from __future__ import annotations
from pathlib import Path
from typing import Optional
import numpy as np
from . import figtex
from ._common import individuation_recovery, ids_by, outdir_for, stable_offset, vectors_for
from .io_utils import write_dat, write_json
from .provenance import Tier, exp_seed, run_metadata, stamp
from .providers import SeriesProvider, SimulatedProvider

M_ID, M_NUM = "M49", 49
SOURCE = "experiments/exp_m49_character_residue.py"
TOOL_USAGE = ["_common.individuation_recovery"]
STRATEGIES = {"Brecht (alienation)": 0.2, "method (partial)": 0.5, "Stanislavski (merger)": 0.85}

def run(provider=None, seed=None, outdir=None) -> dict:
    provider = provider or SimulatedProvider()
    seed = exp_seed(M_NUM) if seed is None else int(seed)
    outdir = Path(outdir) if outdir else outdir_for(M_ID)
    actors = vectors_for(ids_by(domain="Fiction", limit=30))
    characters = vectors_for(ids_by(domain="Leadership", limit=30))
    pm = np.mean(actors + characters, axis=0)
    dat, summary = [], {}
    for i, (name, blend) in enumerate(STRATEGIES.items()):
        res = []
        for A, C in zip(actors, characters):
            post = (1 - blend) * A + blend * C          # actor after the role
            res.append(individuation_recovery(post, C, pm))   # residue = character profile retained
        dat.append([i, round(float(np.mean(res)), 4)]); summary[name] = round(float(np.mean(res)), 4)
    write_dat(outdir / "figdata" / "m49_residue.dat", ["strategy_index", "character_residue"], dat)
    (outdir / "tex").mkdir(parents=True, exist_ok=True)
    fig = figtex.line_figure(m_id=M_ID, dat_name="m49_residue.dat", columns=[(1, "character residue")],
        xlabel="strategy (0 Brecht, 1 method, 2 Stanislavski)", ylabel="residue (character profile retained)",
        caption=("Character residue by acting strategy: Stanislavski merger leaves more cross-"
                 f"contamination than Brecht alienation (Simülasyon; seed={seed}). Actor data is future work."),
        label="fig:m49", source=SOURCE, tier=Tier.SIMULASYON.value, seed=seed)
    (outdir / "tex" / "m49_fig.tex").write_text(fig, encoding="utf-8")
    write_json(outdir / "results.json", {
        "metadata": run_metadata(M_ID, seed, {"strategies": STRATEGIES}), "tool_usage": TOOL_USAGE,
        "residue_by_strategy": {n: stamp(v, seed=seed) for n, v in summary.items()},
        "future_work": stamp("Real character-residue measurement needs actor CEID before/after long "
                             "runs; here it is simulated.", tier=Tier.TAHMINI, seed=seed,
                             method="future-work")})
    return {"id": M_ID, "outdir": str(outdir), "tool_usage": TOOL_USAGE, "headline": summary}
