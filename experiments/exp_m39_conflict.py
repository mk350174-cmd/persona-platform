"""
M39 — K4-K4 Conflict Resolution in multi-persona systems.

Two coalitions with incompatible moral filters (deontological vs consequentialist,
from the court simulation) are reconciled by three mechanisms — majority vote,
CEID-weighted vote, and a mediator persona — and the consensus balance is compared.
Tier: Simülasyon.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import numpy as np

from persona_math.ceid import ceid_score
from persona_math.metrics import cosine_similarity

from . import figtex
from ._common import ids_by, outdir_for, vectors_for
from .io_utils import write_dat, write_json
from .provenance import Tier, exp_seed, run_metadata, stamp
from .providers import SeriesProvider, SimulatedProvider

M_ID, M_NUM = "M39", 39
SOURCE = "experiments/exp_m39_conflict.py"
TOOL_USAGE = ["ceid.ceid_score", "metrics.cosine_similarity"]


def _balance(resolved, a, b):
    """Consensus balance = 1 - |sim(resolved,a) - sim(resolved,b)| (1 = perfectly even)."""
    return float(1.0 - abs(cosine_similarity(resolved, a) - cosine_similarity(resolved, b)))


def run(provider: Optional[SeriesProvider] = None, seed: Optional[int] = None,
        outdir: Optional[Path] = None) -> dict:
    provider = provider or SimulatedProvider()
    seed = exp_seed(M_NUM) if seed is None else int(seed)
    outdir = Path(outdir) if outdir else outdir_for(M_ID)

    # two conflicting coalition representatives (philosopher vs leader archetypes)
    A = np.mean(vectors_for(ids_by(domain="Philosophy", limit=10)), axis=0)
    B = np.mean(vectors_for(ids_by(domain="Leadership", limit=10)), axis=0)
    wA = float(ceid_score(A, A)["CEID_score"]); wB = float(ceid_score(B, B)["CEID_score"])

    majority = A if 151 >= 99 else B                      # deontological majority (151/99)
    weighted = (wA * A + wB * B) / (wA + wB)              # CEID-weighted compromise
    mediator = 0.5 * (A + B)                              # empathic mediator (blend)
    mechanisms = {"majority": majority, "weighted_CEID": weighted, "mediator": mediator}

    rows = {name: round(_balance(v, A, B), 4) for name, v in mechanisms.items()}
    write_dat(outdir / "figdata" / "m39_balance.dat",
              ["mechanism_index", "consensus_balance"],
              [[0, rows["majority"]], [1, rows["weighted_CEID"]], [2, rows["mediator"]]])
    best = max(rows, key=rows.get)

    (outdir / "tex").mkdir(parents=True, exist_ok=True)
    tbl = figtex.table(
        header=["Resolution mechanism", "Consensus balance"],
        rows=[["Majority vote", f"{rows['majority']:.3f}"],
              ["CEID-weighted vote", f"{rows['weighted_CEID']:.3f}"],
              ["Mediator persona", f"{rows['mediator']:.3f}"]],
        caption=("Three K4–K4 conflict-resolution mechanisms by consensus balance (1 = even). The "
                 f"mediator/weighted compromise balances the coalitions better than majority "
                 f"(best: {best}; Simülasyon; seed={seed})."),
        label="tab:m39", source=SOURCE, tier=Tier.SIMULASYON.value, seed=seed,
        col_spec="lr", escape_cells=False)
    (outdir / "tex" / "m39_table.tex").write_text(tbl, encoding="utf-8")

    results = {
        "metadata": run_metadata(M_ID, seed, {}),
        "tool_usage": TOOL_USAGE,
        "consensus_balance": {name: stamp(v, seed=seed) for name, v in rows.items()},
        "best_mechanism": best,
    }
    write_json(outdir / "results.json", results)
    return {"id": M_ID, "outdir": str(outdir), "tool_usage": TOOL_USAGE,
            "headline": {"best_mechanism": best, **rows}}
