"""
M24 — Vine and Tree: two archetypal identity-development trajectories.

Defines two K-layer archetypes — Tree (high Mandatory-Core / structural rigidity)
and Vine (high relational layers / low core rigidity) — computes their K-block
signatures, and classifies the persona library by nearest archetype. Tier:
Simülasyon (synthetic typology; human developmental data is future work).
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import numpy as np

from persona_math.metrics import cosine_similarity
from persona_math.params import MANDATORY_CORE_INDICES

from . import figtex
from ._common import k_block, outdir_for, panel_sample, vectors_for
from .io_utils import write_csv, write_dat, write_json
from .provenance import Tier, exp_seed, run_metadata, stamp
from .providers import SeriesProvider, SimulatedProvider

M_ID, M_NUM = "M24", 24
SOURCE = "experiments/exp_m24_vine_tree.py"
TOOL_USAGE = ["_common.k_block", "metrics.cosine_similarity"]

N_PERSONAS = 120
RELATIONAL_BLOCK = 8   # K81-K90 relational/network region (illustrative)


def _archetypes(pop_mean: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    core = list(MANDATORY_CORE_INDICES)
    tree = pop_mean.copy()
    tree[core] = np.clip(tree[core] + 0.2, 0, 1)                  # strong rigid core
    vine = pop_mean.copy()
    vine[core] = np.clip(vine[core] - 0.2, 0, 1)
    vine[RELATIONAL_BLOCK * 10:(RELATIONAL_BLOCK + 1) * 10] += 0.2  # strong relational reach
    return np.clip(tree, 0, 1), np.clip(vine, 0, 1)


def run(provider: Optional[SeriesProvider] = None, seed: Optional[int] = None,
        outdir: Optional[Path] = None) -> dict:
    provider = provider or SimulatedProvider()
    seed = exp_seed(M_NUM) if seed is None else int(seed)
    outdir = Path(outdir) if outdir else outdir_for(M_ID)

    ids = panel_sample(N_PERSONAS)
    vecs = vectors_for(ids)
    pop_mean = np.mean(vecs, axis=0)
    tree, vine = _archetypes(pop_mean)

    n_tree = n_vine = 0
    rows = []
    for pid, P in zip(ids, vecs):
        st, sv = cosine_similarity(P, tree), cosine_similarity(P, vine)
        label = "tree" if st >= sv else "vine"
        n_tree += label == "tree"; n_vine += label == "vine"
        rows.append([pid, round(st, 4), round(sv, 4), label])
    write_csv(outdir / "m24_classification.csv",
              ["persona_id", "sim_tree", "sim_vine", "archetype"], rows)

    # K-block signatures of the two archetypes (mean per block)
    sig = np.column_stack([np.arange(10),
                           [float(k_block(tree, b).mean()) for b in range(10)],
                           [float(k_block(vine, b).mean()) for b in range(10)]])
    write_dat(outdir / "figdata" / "m24_signatures.dat", ["block", "tree", "vine"], sig)

    (outdir / "tex").mkdir(parents=True, exist_ok=True)
    fig = figtex.line_figure(
        m_id=M_ID, dat_name="m24_signatures.dat",
        columns=[(1, "Tree"), (2, "Vine")],
        xlabel="K-layer block (0--9)", ylabel="mean activation",
        caption=("K-block signatures of the Tree (rigid core) vs Vine (relational reach) identity "
                 f"archetypes (Simülasyon; seed={seed})."),
        label="fig:m24", source=SOURCE, tier=Tier.SIMULASYON.value, seed=seed)
    (outdir / "tex" / "m24_fig.tex").write_text(fig, encoding="utf-8")

    results = {
        "metadata": run_metadata(M_ID, seed, {"n_personas": N_PERSONAS}),
        "tool_usage": TOOL_USAGE,
        "classification": {"n_tree": int(n_tree), "n_vine": int(n_vine),
                           "tree_fraction": stamp(round(n_tree / len(ids), 4), seed=seed)},
        "future_work": stamp("A Vine–Tree scale validated on human developmental data (Erikson/"
                             "Marcia statuses) is future work; here archetypes are synthetic.",
                             tier=Tier.TAHMINI, seed=seed, method="future-work"),
    }
    write_json(outdir / "results.json", results)
    return {"id": M_ID, "outdir": str(outdir), "tool_usage": TOOL_USAGE,
            "headline": {"n_tree": int(n_tree), "n_vine": int(n_vine)}}
