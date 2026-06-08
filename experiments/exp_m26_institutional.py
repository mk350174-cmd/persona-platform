"""
M26 — Institutional Disruption of AI-Augmented Polymathy (sociological follow-up to M17).

Computes repository-level bibliometrics (discipline spread via journal targets,
cross-reference network growth) as the case-study evidence. External Web-of-Science /
Scopus bibliometrics and university-policy analysis are the paper's empirical/policy
work, flagged Tahmini. Self-contained scanner. Tier: Hesaplanan.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Optional

from . import figtex
from ._common import outdir_for
from .io_utils import write_dat, write_json
from .provenance import Tier, exp_seed, run_metadata, stamp
from .providers import SeriesProvider, SimulatedProvider

M_ID, M_NUM = "M26", 26
SOURCE = "experiments/exp_m26_institutional.py"
TOOL_USAGE = ["papers/*.tex journal+cross-ref scan"]

_PAPERS = Path(__file__).resolve().parent.parent / "papers"
_ID_RE = re.compile(r"^(M\d+)_")
_CITE_RE = re.compile(r"ManuscriptM(\d+)")
_TARGET_RE = re.compile(r"%\s*(?:Target(?:\s*Journal)?|Hedef)\s*:\s*(.+)")


def run(provider: Optional[SeriesProvider] = None, seed: Optional[int] = None,
        outdir: Optional[Path] = None) -> dict:
    provider = provider or SimulatedProvider()
    seed = exp_seed(M_NUM) if seed is None else int(seed)
    outdir = Path(outdir) if outdir else outdir_for(M_ID)

    journals, edges, n_papers = set(), 0, 0
    cumulative = []   # (m_number, cumulative distinct journals) — "disciplinary growth"
    for path in sorted(_PAPERS.glob("M*"), key=lambda p: int(_ID_RE.match(p.name).group(1)[1:])
                       if _ID_RE.match(p.name) else 999):
        if path.suffix not in {".tex", ".txt"}:
            continue
        m = _ID_RE.match(path.name)
        if not m:
            continue
        n_papers += 1
        text = path.read_text(encoding="utf-8", errors="replace")
        edges += len({f"M{n}" for n in _CITE_RE.findall(text)} - {m.group(1)})
        tgt = _TARGET_RE.search(text)
        if tgt:
            journals.add(tgt.group(1).strip())
        cumulative.append([int(m.group(1)[1:]), len(journals)])

    density = edges / (n_papers * (n_papers - 1)) if n_papers > 1 else 0.0
    write_dat(outdir / "figdata" / "m26_growth.dat",
              ["paper_number", "cumulative_distinct_journals"], cumulative)

    (outdir / "tex").mkdir(parents=True, exist_ok=True)
    fig = figtex.line_figure(
        m_id=M_ID, dat_name="m26_growth.dat",
        columns=[(1, "cumulative distinct journals")],
        xlabel="paper number (M\\#)", ylabel="distinct target journals",
        caption=("Disciplinary spread of the single-author series: distinct target journals "
                 f"accumulate across the 60 papers (Hesaplanan; seed={seed}). External WoS/Scopus "
                 "bibliometrics and university-policy analysis are future work."),
        label="fig:m26", source=SOURCE, tier=Tier.HESAPLANAN.value, seed=seed)
    (outdir / "tex" / "m26_fig.tex").write_text(fig, encoding="utf-8")

    results = {
        "metadata": run_metadata(M_ID, seed, {"n_papers": n_papers}),
        "tool_usage": TOOL_USAGE,
        "distinct_journal_targets": stamp(len(journals), tier=Tier.HESAPLANAN, seed=seed),
        "citation_network_density": stamp(round(density, 4), tier=Tier.HESAPLANAN, seed=seed),
        "future_work": stamp("Institutional-disruption claims require external bibliometrics "
                             "(Web of Science / Scopus 2022–2026) and a comparison of university AI "
                             "policies — not computed here.", tier=Tier.TAHMINI, seed=seed,
                             method="future-work"),
    }
    write_json(outdir / "results.json", results)
    return {"id": M_ID, "outdir": str(outdir), "tool_usage": TOOL_USAGE,
            "headline": {"distinct_journals": len(journals), "density": round(density, 3)}}
