"""
M6 — Arkhe (Irreversible Identity Commitment).

A theory-heavy paper; the harness contributes two small computational
illustrations (the phenomenological / Erikson–Marcia deepening is prose, not
simulated):

1. GWT-ignition phase transition — fraction of personas whose global workspace
   "ignites" as the ignition threshold varies (ties GWT ignition ↔ Arkhe).
2. Arkhe irreversibility illustration — Λ(t) along a simulated approach-to-telos
   trajectory and the commitment point t*.

Honesty: the specific τ_Arkhe value (≈3.5 in the design notes) is **Tahmini** —
not measured here. We use the framework's default τ and show the *mechanism*.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import numpy as np

from persona_math.consciousness import gwt_ignition
from persona_math.dynamics import arkhe_from_embeddings

from . import figtex
from ._common import outdir_for, panel_sample, stable_offset, vectors_for
from .io_utils import write_dat, write_json
from .provenance import Tier, exp_seed, run_metadata, stamp
from .providers import SeriesProvider, SimulatedProvider

M_ID = "M6"
M_NUM = 6
SOURCE = "experiments/exp_m6_arkhe.py"
TOOL_USAGE = [
    "consciousness.gwt_ignition (M22-M25)",
    "dynamics.arkhe_from_embeddings (M10-M15)",
]

N_PANEL = 40
N_ARKHE = 12
N_TURNS = 15
# Personas are highly activated, so the ignition transition lives near the top of
# the range — sample finely there to resolve it.
THRESHOLDS = [round(0.50 + 0.05 * i, 2) for i in range(9)] + [0.97, 0.98, 0.99]
BLOCK = 10


def _block_means(P: np.ndarray) -> np.ndarray:
    n = P.size // BLOCK
    return np.array([P[i * BLOCK:(i + 1) * BLOCK].mean() for i in range(n)])


def run(provider: Optional[SeriesProvider] = None, seed: Optional[int] = None,
        outdir: Optional[Path] = None) -> dict:
    provider = provider or SimulatedProvider()  # unused; interface symmetry
    seed = exp_seed(M_NUM) if seed is None else int(seed)
    outdir = Path(outdir) if outdir else outdir_for(M_ID)

    ids = panel_sample(N_PANEL)
    block_means = [_block_means(P) for P in vectors_for(ids)]

    # ── 1. GWT ignition phase transition ────────────────────────────────────────
    curve = []
    for thr in THRESHOLDS:
        flags, strengths = [], []
        for bm in block_means:
            g = gwt_ignition(bm, threshold=thr)
            flags.append(bool(g["ignition_occurred"]))
            strengths.append(float(g["global_broadcast_strength"]))
        curve.append([thr, round(float(np.mean(flags)), 4), round(float(np.mean(strengths)), 4)])
    write_dat(outdir / "figdata" / "m6_ignition_curve.dat",
              ["threshold", "ignition_fraction", "mean_broadcast"], curve)
    # critical threshold = highest threshold with >50% ignition
    above = [c[0] for c in curve if c[1] >= 0.5]
    critical_threshold = max(above) if above else None

    # ── 2. Arkhe irreversibility illustration ───────────────────────────────────
    arkhe_ids = panel_sample(N_ARKHE)
    lambda_stack, t_stars, achieved = [], [], 0
    for pid in arkhe_ids:
        P0 = vectors_for([pid])[0]
        rng = np.random.default_rng(seed + stable_offset(pid))
        # approach-to-telos: noise shrinks geometrically toward the persona spec
        emb = np.array([P0 + (0.5 * np.exp(-0.3 * t)) * rng.normal(0, 1, P0.shape)
                        for t in range(N_TURNS)])
        a = arkhe_from_embeddings(emb, P0)
        lam = np.asarray(a["Lambda"], dtype=float)
        lambda_stack.append(lam)
        t_stars.append(int(a["t_star"]))
        achieved += bool(a["arkhe_achieved"])
    mean_lambda = np.mean(lambda_stack, axis=0)
    write_dat(outdir / "figdata" / "m6_arkhe_lambda.dat",
              ["t", "mean_Lambda"],
              np.column_stack([np.arange(len(mean_lambda)), mean_lambda]))

    # ── figure ──────────────────────────────────────────────────────────────────
    (outdir / "tex").mkdir(parents=True, exist_ok=True)
    fig = figtex.line_figure(
        m_id=M_ID, dat_name="m6_ignition_curve.dat",
        columns=[(1, "ignition fraction"), (2, "mean broadcast strength")],
        xlabel="ignition threshold", ylabel="fraction / strength",
        caption=("Global-workspace ignition as a phase transition across the persona panel: "
                 "ignition fraction falls as the threshold rises, linking GWT ignition to "
                 f"Arkhe crystallisation (Simülasyon; $n={N_PANEL}$; seed={seed})."),
        label="fig:m6_ignition", source=SOURCE, tier=Tier.SIMULASYON.value, seed=seed)
    (outdir / "tex" / "m6_ignition_fig.tex").write_text(fig, encoding="utf-8")

    results = {
        "metadata": run_metadata(M_ID, seed, {"n_panel": N_PANEL, "n_arkhe": N_ARKHE,
                                              "thresholds": THRESHOLDS}),
        "tool_usage": TOOL_USAGE,
        "gwt_ignition": {
            "critical_threshold_50pct": stamp(critical_threshold, seed=seed,
                                              note="highest threshold with ≥50% ignition"),
            "ignition_fraction_at_0.6": stamp(
                next((c[1] for c in curve if abs(c[0] - 0.60) < 1e-9), None),
                seed=seed),
        },
        "arkhe": {
            "arkhe_achieved_fraction": stamp(round(achieved / len(arkhe_ids), 4), seed=seed,
                                             note="fraction reaching irreversible commitment"),
            "mean_t_star": stamp(round(float(np.mean(t_stars)), 3), seed=seed,
                                 note=("mean commitment turn t*; small because cosine-RC is "
                                       "high for bounded-positive persona vectors (proxy limit)")),
            "tau_used": 0.85,
            "tau_arkhe_note": stamp("τ_Arkhe ≈ 3.5 (design notes) is ESTIMATED, not "
                                    "measured; framework default τ=0.85 used here",
                                    tier=Tier.TAHMINI, seed=seed, method="estimate"),
        },
    }
    write_json(outdir / "results.json", results)
    return {"id": M_ID, "outdir": str(outdir), "tool_usage": TOOL_USAGE,
            "headline": {"critical_threshold": critical_threshold,
                         "arkhe_achieved_frac": round(achieved / len(arkhe_ids), 3)}}
