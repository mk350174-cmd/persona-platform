"""
M47 — The Parenting Persona (intergenerational K-layer transmission).

Three parenting archetypes (K2-integrated / K2-suppressed / K2-overactive) generate
"child" vectors by noisy transmission; the child's K2 (shadow, idx1) tracks the
parent's. Tier: Simülasyon; human parent-child data is Tahmini.
"""
from __future__ import annotations
from pathlib import Path
from typing import Optional
import numpy as np
from . import figtex
from ._common import k_layer, make_synthetic_population, outdir_for
from .io_utils import write_dat, write_json
from .provenance import Tier, exp_seed, run_metadata, stamp
from .providers import SeriesProvider, SimulatedProvider

M_ID, M_NUM = "M47", 47
SOURCE = "experiments/exp_m47_parenting.py"
TOOL_USAGE = ["_common.make_synthetic_population", "_common.k_layer"]
N_CHILDREN = 60
ARCH = {"K2-suppressed": 0.2, "K2-integrated": 0.55, "K2-overactive": 0.9}

def run(provider=None, seed=None, outdir=None) -> dict:
    provider = provider or SimulatedProvider()
    seed = exp_seed(M_NUM) if seed is None else int(seed)
    outdir = Path(outdir) if outdir else outdir_for(M_ID)
    base = make_synthetic_population(1, seed)[0]
    dat, summary = [], {}
    for i, (name, k2) in enumerate(ARCH.items()):
        parent = base.copy(); parent[1] = k2          # set parent K2 (idx1)
        rng = np.random.default_rng(seed + i)
        child_k2 = [float(np.clip(parent[1] + rng.normal(0, 0.08), 0, 1)) for _ in range(N_CHILDREN)]
        dat.append([i, round(parent[1], 4), round(float(np.mean(child_k2)), 4)])
        summary[name] = round(float(np.mean(child_k2)), 4)
    write_dat(outdir / "figdata" / "m47_transmission.dat",
              ["archetype_index", "parent_k2", "child_k2_mean"], dat)
    (outdir / "tex").mkdir(parents=True, exist_ok=True)
    fig = figtex.line_figure(m_id=M_ID, dat_name="m47_transmission.dat",
        columns=[(1, "parent K2"), (2, "child K2 (mean)")],
        xlabel="parenting archetype (0 suppressed,1 integrated,2 overactive)", ylabel="K2 (shadow) activation",
        caption=("Intergenerational transmission: child K2 (shadow) tracks the parenting archetype's "
                 f"K2 (Simülasyon; {N_CHILDREN} children/archetype; seed={seed}). Human data is future work."),
        label="fig:m47", source=SOURCE, tier=Tier.SIMULASYON.value, seed=seed)
    (outdir / "tex" / "m47_fig.tex").write_text(fig, encoding="utf-8")
    write_json(outdir / "results.json", {
        "metadata": run_metadata(M_ID, seed, {"archetypes": ARCH}), "tool_usage": TOOL_USAGE,
        "child_k2_by_archetype": {n: stamp(v, seed=seed) for n, v in summary.items()},
        "future_work": stamp("Real parent→child K-transmission needs attachment-cohort data "
                             "(Bowlby/Ainsworth); here it is simulated.", tier=Tier.TAHMINI,
                             seed=seed, method="future-work")})
    return {"id": M_ID, "outdir": str(outdir), "tool_usage": TOOL_USAGE, "headline": summary}
