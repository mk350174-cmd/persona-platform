"""
M17 — AI-Augmented Polymathy (meta-paper; the series as its own case study).

Self-referential bibliometrics computed directly from the repository:
* cross-reference network among papers (``\\cite{ManuscriptM…}``) → density;
* journal-target diversity (interdisciplinary spread);
* tool-reuse across papers (from ``results/M*/results.json`` ``tool_usage``) →
  "epistemic velocity" (how far a shared toolkit propagates).

Self-contained: reads ``papers/`` and ``results/`` directly (no manifest dependency).
Tier: Hesaplanan (descriptive metrics of this repo).
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Optional

from . import figtex
from ._common import outdir_for, RESULTS_ROOT
from .io_utils import write_csv, write_json
from .provenance import Tier, exp_seed, run_metadata, stamp
from .providers import SeriesProvider, SimulatedProvider

M_ID, M_NUM = "M17", 17
SOURCE = "experiments/exp_m17_polymathy.py"
TOOL_USAGE = ["papers/*.tex cross-ref scan", "results/M*/results.json tool_usage scan"]

_PAPERS = Path(__file__).resolve().parent.parent / "papers"
_ID_RE = re.compile(r"^(M\d+)_")
_CITE_RE = re.compile(r"ManuscriptM(\d+)")
_TARGET_RE = re.compile(r"%\s*(?:Target(?:\s*Journal)?|Hedef)\s*:\s*(.+)")


def run(provider: Optional[SeriesProvider] = None, seed: Optional[int] = None,
        outdir: Optional[Path] = None) -> dict:
    provider = provider or SimulatedProvider()
    seed = exp_seed(M_NUM) if seed is None else int(seed)
    outdir = Path(outdir) if outdir else outdir_for(M_ID)

    # ── cross-reference network + journal diversity from paper sources ──────────
    adjacency: dict[str, set] = {}
    journals: set = set()
    for path in sorted(_PAPERS.glob("M*")):
        if path.suffix not in {".tex", ".txt"}:
            continue
        m = _ID_RE.match(path.name)
        if not m:
            continue
        pid = m.group(1)
        text = path.read_text(encoding="utf-8", errors="replace")
        adjacency[pid] = {f"M{n}" for n in _CITE_RE.findall(text)} - {pid}
        tgt = _TARGET_RE.search(text)
        if tgt:
            journals.add(tgt.group(1).strip())

    n_papers = len(adjacency)
    n_edges = sum(len(v) for v in adjacency.values())
    density = n_edges / (n_papers * (n_papers - 1)) if n_papers > 1 else 0.0

    # ── tool reuse from results metadata ────────────────────────────────────────
    module_papers: dict[str, set] = {}
    for rj in sorted(RESULTS_ROOT.glob("M*/results.json")):
        paper = rj.parent.name
        if paper in {"M7", "M17", "M26"}:
            continue  # skip meta-scanners' own meta tool_usage
        try:
            data = json.loads(rj.read_text(encoding="utf-8"))
        except Exception:
            continue
        for entry in data.get("tool_usage", []):
            mod = entry.split(".")[0].split()[0]
            module_papers.setdefault(mod, set()).add(paper)

    reuse_rows = sorted(((m, len(p)) for m, p in module_papers.items()),
                        key=lambda r: (-r[1], r[0]))
    write_csv(outdir / "m17_module_reuse.csv", ["module", "n_papers_using"],
              [[m, n] for m, n in reuse_rows])
    n_modules = len(module_papers)
    mean_reuse = (sum(n for _, n in reuse_rows) / n_modules) if n_modules else 0.0

    (outdir / "tex").mkdir(parents=True, exist_ok=True)
    tbl = figtex.table(
        header=["Metric", "Value"],
        rows=[
            ["Papers in series", f"{n_papers}"],
            ["Distinct journal targets", f"{len(journals)}"],
            ["Cross-reference edges", f"{n_edges}"],
            ["Citation-network density", f"{density:.3f}"],
            ["Shared framework modules reused", f"{n_modules}"],
            ["Mean papers per module (reuse)", f"{mean_reuse:.2f}"],
        ],
        caption=("Bibliometrics of the series as its own case study: an interdisciplinary "
                 "spread bound by a dense cross-reference network and a heavily reused shared "
                 f"toolkit (Hesaplanan; seed={seed})."),
        label="tab:m17", source=SOURCE, tier=Tier.HESAPLANAN.value, seed=seed,
        col_spec="lr", escape_cells=False)
    (outdir / "tex" / "m17_metrics_table.tex").write_text(tbl, encoding="utf-8")

    results = {
        "metadata": run_metadata(M_ID, seed, {"n_papers_scanned": n_papers}),
        "tool_usage": TOOL_USAGE,
        "cross_reference_network": {
            "n_papers": n_papers,
            "n_edges": n_edges,
            "density": stamp(round(density, 4), tier=Tier.HESAPLANAN, seed=seed,
                             note="directed citation density across the 60-paper series"),
        },
        "interdisciplinarity": {
            "distinct_journal_targets": stamp(len(journals), tier=Tier.HESAPLANAN, seed=seed),
        },
        "epistemic_velocity": {
            "framework_modules_reused": stamp(n_modules, tier=Tier.HESAPLANAN, seed=seed),
            "mean_papers_per_module": round(mean_reuse, 3),
            "top_reused": reuse_rows[:5],
        },
    }
    write_json(outdir / "results.json", results)
    return {"id": M_ID, "outdir": str(outdir), "tool_usage": TOOL_USAGE,
            "headline": {"n_journals": len(journals), "citation_density": round(density, 3),
                         "modules_reused": n_modules}}
