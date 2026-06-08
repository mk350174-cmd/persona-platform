"""
M51 — Cinematic K6 Analysis (archetypal signatures of auteurs).

Director personas (Kubrick/Tarkovsky/Bergman/Kurosawa) are NOT in the library, so
this uses the Arts-domain personas as a PROXY panel to show K6 (Virtù/archetypal
foundation, idx5) varies and yields distinct K-layer signatures. Tier: Simülasyon
(proxy); applying CKA to real filmographies is future work (coordinate with M50).
"""
from __future__ import annotations
from pathlib import Path
from typing import Optional
import numpy as np
from persona_math.d1_protocol import run_d4_spectroscopy
from . import figtex
from ._common import ids_by, k_layer, outdir_for, vectors_for
from .io_utils import write_dat, write_json
from .provenance import Tier, exp_seed, run_metadata, stamp
from .providers import SeriesProvider, SimulatedProvider

M_ID, M_NUM = "M51", 51
SOURCE = "experiments/exp_m51_cinema.py"
TOOL_USAGE = ["_common.k_layer", "d1_protocol.run_d4_spectroscopy"]

def run(provider=None, seed=None, outdir=None) -> dict:
    provider = provider or SimulatedProvider()
    seed = exp_seed(M_NUM) if seed is None else int(seed)
    outdir = Path(outdir) if outdir else outdir_for(M_ID)
    ids = (ids_by(domain="Arts") + ids_by(domain="Art"))[:20]
    vecs = vectors_for(ids)
    k6 = np.sort(np.array([k_layer(P, 6) for P in vecs]))
    spec = run_d4_spectroscopy(vecs, labels=ids)
    write_dat(outdir / "figdata" / "m51_k6.dat", ["index", "k6_activation"],
              np.column_stack([np.arange(len(k6)), k6]))
    (outdir / "tex").mkdir(parents=True, exist_ok=True)
    fig = figtex.line_figure(m_id=M_ID, dat_name="m51_k6.dat", columns=[(1, "K6 (Virt\\`u) activation")],
        xlabel="artist (sorted)", ylabel="K6 archetypal-foundation activation",
        caption=("K6 archetypal signatures vary across an Arts-domain PROXY panel (directors are "
                 f"absent from the library); distinct K-layer profiles (mean pairwise sim "
                 f"{spec['mean_pairwise_similarity']:.2f}; Simülasyon; seed={seed}). CKA on real "
                 "filmographies is future work."),
        label="fig:m51", source=SOURCE, tier=Tier.SIMULASYON.value, seed=seed)
    (outdir / "tex" / "m51_fig.tex").write_text(fig, encoding="utf-8")
    write_json(outdir / "results.json", {
        "metadata": run_metadata(M_ID, seed, {"n_proxy": len(ids)}), "tool_usage": TOOL_USAGE,
        "k6_range": [round(float(k6.min()), 4), round(float(k6.max()), 4)],
        "mean_pairwise_similarity": stamp(round(float(spec["mean_pairwise_similarity"]), 4), seed=seed),
        "future_work": stamp("Cinematic K6 Analysis on real director filmographies (Kubrick/"
                             "Tarkovsky/Bergman/Kurosawa) is future work; an Arts proxy is used here.",
                             tier=Tier.TAHMINI, seed=seed, method="future-work")})
    return {"id": M_ID, "outdir": str(outdir), "tool_usage": TOOL_USAGE,
            "headline": {"k6_range": [round(float(k6.min()), 3), round(float(k6.max()), 3)]}}
