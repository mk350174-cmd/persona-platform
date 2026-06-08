"""
M50 — Textual K-Layer Extraction: literary style as K-layer signature.

FLAGSHIP / platform paper. Uses the REAL Kafka, Woolf and Dostoevsky personas from the
library, reporting each author's dominant K-layers (block signature) and their pairwise
distinctiveness (spectroscopy). Tier: Simülasyon on curated author vectors; true
extraction FROM literary text (TKE proper) is Tahmini future work.
"""
from __future__ import annotations
from pathlib import Path
from typing import Optional
import numpy as np
from persona_math.d1_protocol import run_d4_spectroscopy
from . import figtex
from ._common import k_block, outdir_for, resolvable_ids, vectors_for
from .io_utils import write_csv, write_dat, write_json
from .provenance import Tier, exp_seed, run_metadata, stamp
from .providers import SeriesProvider, SimulatedProvider

M_ID, M_NUM = "M50", 50
SOURCE = "experiments/exp_m50_author_voice.py"
TOOL_USAGE = ["_common.k_block", "d1_protocol.run_d4_spectroscopy"]
AUTHORS = ["franz_kafka", "virginia_woolf", "dostoevsky"]

def run(provider=None, seed=None, outdir=None) -> dict:
    provider = provider or SimulatedProvider()
    seed = exp_seed(M_NUM) if seed is None else int(seed)
    outdir = Path(outdir) if outdir else outdir_for(M_ID)
    authors = resolvable_ids(AUTHORS)
    vecs = vectors_for(authors)
    # block signatures + dominant K-layer per author
    cols = [np.arange(10)]
    rows = []
    for name, P in zip(authors, vecs):
        cols.append(np.array([float(k_block(P, b).mean()) for b in range(10)]))
        dom_layer = int(np.argmax(P)) + 1                     # dominant K-layer (1-indexed)
        rows.append([name, dom_layer, round(float(P.max()), 4)])
    write_dat(outdir / "figdata" / "m50_signatures.dat",
              ["block"] + authors, np.column_stack(cols))
    write_csv(outdir / "m50_dominant_layers.csv",
              ["author", "dominant_K_layer", "activation"], rows)
    spec = run_d4_spectroscopy(vecs, labels=authors)
    (outdir / "tex").mkdir(parents=True, exist_ok=True)
    fig = figtex.line_figure(m_id=M_ID, dat_name="m50_signatures.dat",
        columns=[(i + 1, a) for i, a in enumerate(authors)],
        xlabel="K-layer block (0--9)", ylabel="mean activation",
        caption=("Author K-layer signatures from the real Kafka/Woolf/Dostoevsky personas; each "
                 f"voice has a distinct block profile (Simülasyon; mean pairwise similarity "
                 f"{spec['mean_pairwise_similarity']:.2f}; seed={seed}). TKE from raw literary text "
                 "is future work."),
        label="fig:m50", source=SOURCE, tier=Tier.SIMULASYON.value, seed=seed)
    (outdir / "tex" / "m50_fig.tex").write_text(fig, encoding="utf-8")
    write_json(outdir / "results.json", {
        "metadata": run_metadata(M_ID, seed, {"authors": authors}), "tool_usage": TOOL_USAGE,
        "dominant_layers": {r[0]: {"K_layer": r[1], "activation": r[2]} for r in rows},
        "mean_pairwise_similarity": stamp(round(float(spec["mean_pairwise_similarity"]), 4), seed=seed,
                                          note="lower ⇒ more distinct author voices"),
        "future_work": stamp("TKE proper infers K-layers FROM an author's text; no text→vector "
                             "extractor exists here, so curated author vectors are used (coordinate "
                             "with M9).", tier=Tier.TAHMINI, seed=seed, method="future-work")})
    return {"id": M_ID, "outdir": str(outdir), "tool_usage": TOOL_USAGE,
            "headline": {"authors": authors, "dominant_layers": {r[0]: r[1] for r in rows}}}
