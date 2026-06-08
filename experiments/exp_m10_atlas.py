"""
M10 — HPEP-250 Atlas (Philosophical Persona Mapping).

The best-fit "populate" paper: maps philosopher-tagged personas with
``d1_protocol.run_d5_atlas`` (PCA → 2D + KMeans clustering) and analyses the
structure:

* 2D atlas embedding coloured by cluster;
* cluster table with exemplar philosophers (Stoics / Existentialists / …);
* outlier ranking + a famous-pair distance (e.g. Nietzsche vs Kant).

Honesty: the actual PCA explained-variance and ``manifold_verified`` flag are
reported as-is. If 2D variance is low, that is stated, not hidden. Tier:
Hesaplanan/Simülasyon.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import numpy as np

from persona_math.d1_protocol import run_d5_atlas
from persona_math.metrics import drift

from . import figtex
from ._common import ids_by, outdir_for, vectors_for
from .io_utils import write_csv, write_dat, write_json
from .provenance import Tier, exp_seed, run_metadata, stamp
from .providers import SeriesProvider, SimulatedProvider

M_ID = "M10"
M_NUM = 10
SOURCE = "experiments/exp_m10_atlas.py"
TOOL_USAGE = [
    "d1_protocol.run_d5_atlas (M16-M18 manifold + KMeans)",
    "metrics.drift (M05-M09)",
]

FAMOUS_PAIRS = [
    ("friedrich_nietzsche_classic", "immanuel_kant"),
    ("marcus_aurelius", "jean_paul_sartre"),
    ("zeno_of_citium", "albert_camus"),
]


def run(provider: Optional[SeriesProvider] = None, seed: Optional[int] = None,
        outdir: Optional[Path] = None) -> dict:
    provider = provider or SimulatedProvider()  # unused; interface symmetry
    seed = exp_seed(M_NUM) if seed is None else int(seed)
    outdir = Path(outdir) if outdir else outdir_for(M_ID)

    ids = ids_by(tags=["philosopher"])
    vecs = vectors_for(ids)
    atlas = run_d5_atlas(vecs, n_components=2)
    emb = np.asarray(atlas["embedding"], dtype=float)
    labels = np.asarray(atlas["cluster_labels"], dtype=int)

    # ── 2D atlas scatter ────────────────────────────────────────────────────────
    write_dat(outdir / "figdata" / "m10_atlas_2d.dat", ["x", "y", "cluster"],
              np.column_stack([emb[:, 0], emb[:, 1], labels]))

    # ── clusters with exemplars ─────────────────────────────────────────────────
    cluster_rows = []
    clusters = {}
    for c in sorted(set(labels.tolist())):
        members = [ids[i] for i in range(len(ids)) if labels[i] == c]
        clusters[int(c)] = members
        cluster_rows.append([int(c), len(members), ", ".join(members[:5])])
    write_csv(outdir / "m10_clusters.csv",
              ["cluster", "size", "exemplars"], cluster_rows)

    # ── outliers: distance to global centroid in embedding space ────────────────
    centroid = emb.mean(axis=0)
    dist = np.linalg.norm(emb - centroid, axis=1)
    order = np.argsort(dist)[::-1]
    outlier_rows = [[ids[i], round(float(dist[i]), 4), int(labels[i])] for i in order[:10]]
    write_csv(outdir / "m10_outliers.csv",
              ["persona_id", "distance_to_centroid", "cluster"], outlier_rows)

    # ── famous-pair distances ───────────────────────────────────────────────────
    id_set = set(ids)
    pair_distances = {}
    for a, b in FAMOUS_PAIRS:
        if a in id_set and b in id_set:
            Pa, Pb = vecs[ids.index(a)], vecs[ids.index(b)]
            pair_distances[f"{a}__vs__{b}"] = {
                "drift_1_minus_cos": stamp(round(float(drift(Pa, Pb)), 4), seed=seed),
                "euclidean": round(float(np.linalg.norm(Pa - Pb)), 4),
            }

    # ── figure / table ──────────────────────────────────────────────────────────
    (outdir / "tex").mkdir(parents=True, exist_ok=True)
    fig = figtex.scatter_figure(
        m_id=M_ID, dat_name="m10_atlas_2d.dat",
        xlabel="atlas dim 1", ylabel="atlas dim 2",
        caption=(f"2D HPEP atlas of {len(ids)} philosopher personas, coloured by KMeans "
                 f"cluster ({atlas['n_clusters']} clusters; PCA 2D explained variance "
                 f"{float(np.sum(atlas['explained_variance'])):.2f}; Hesaplanan; seed={seed})."),
        label="fig:m10_atlas", source=SOURCE, tier=Tier.HESAPLANAN.value, seed=seed)
    (outdir / "tex" / "m10_atlas_fig.tex").write_text(fig, encoding="utf-8")

    cl_tbl = figtex.table(
        header=["Cluster", "Size", "Exemplar philosophers"],
        rows=[[r[0], r[1], r[2]] for r in cluster_rows],
        caption=(f"Philosopher clusters in the HPEP atlas (Hesaplanan; seed={seed})."),
        label="tab:m10_clusters", source=SOURCE, tier=Tier.HESAPLANAN.value, seed=seed,
        col_spec="rlp{8cm}", longtable=False)
    (outdir / "tex" / "m10_cluster_table.tex").write_text(cl_tbl, encoding="utf-8")

    ev = [round(float(x), 4) for x in np.atleast_1d(atlas["explained_variance"])]
    results = {
        "metadata": run_metadata(M_ID, seed, {"n_philosophers": len(ids)}),
        "tool_usage": TOOL_USAGE,
        "atlas": {
            "n_personas": len(ids),
            "n_clusters": int(atlas["n_clusters"]),
            "explained_variance_2d": stamp(ev, tier=Tier.HESAPLANAN, seed=seed,
                                           note="PCA variance captured by the 2 atlas axes"),
            "explained_variance_total": round(float(np.sum(ev)), 4),
            "manifold_verified": bool(atlas.get("manifold_verified", False)),
            "intrinsic_dim_estimate": atlas.get("intrinsic_dim_estimate"),
            "honesty_note": (
                "explained_variance and manifold_verified are reported as computed; "
                f"if 2D variance ({float(np.sum(ev)):.2f}) is modest, the philosopher "
                "manifold is intrinsically >2D — stated rather than forced."
            ),
            "cluster_sizes": {int(c): len(m) for c, m in clusters.items()},
        },
        "famous_pair_distances": pair_distances,
        "top_outliers": [{"persona_id": r[0], "distance": r[1], "cluster": r[2]}
                         for r in outlier_rows[:5]],
    }
    write_json(outdir / "results.json", results)
    return {"id": M_ID, "outdir": str(outdir), "tool_usage": TOOL_USAGE,
            "headline": {"n_clusters": int(atlas["n_clusters"]),
                         "explained_var_2d": round(float(np.sum(ev)), 3)}}
