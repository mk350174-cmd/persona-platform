"""
M7 — Unified Mathematical Framework (55 formal tools).

Runs LAST: auto-generates the framework's tool taxonomy by introspecting the
``persona_math`` package docstring (the authoritative M01–M55 module map) and
cross-references which M1–M10 papers exercised each module, using the
``tool_usage`` records the other experiments wrote to ``results/M*/results.json``.

Tier: Hesaplanan (introspection of code + usage records; no simulation).
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Optional

import persona_math

from . import figtex
from ._common import RESULTS_ROOT, outdir_for
from .io_utils import write_csv, write_json
from .provenance import Tier, exp_seed, run_metadata, stamp
from .providers import SeriesProvider, SimulatedProvider

M_ID = "M7"
M_NUM = 7
SOURCE = "experiments/exp_m7_tool_table.py"
TOOL_USAGE = ["persona_math.__doc__ introspection", "results/M*/results.json tool_usage"]

# module-map line: "    foundation   M05-M09   Spectroscopy, Drift, ..."
_MODULE_LINE = re.compile(r"^\s*(\w+)\s+(M\d+)-(M\d+)\s+(.+?)\s*$")


def _parse_taxonomy() -> list[dict]:
    """Parse the persona_math docstring into module → (M-range, tools)."""
    rows = []
    for line in (persona_math.__doc__ or "").splitlines():
        m = _MODULE_LINE.match(line)
        if not m:
            continue
        module, m_lo, m_hi, tools = m.groups()
        tool_list = [t.strip() for t in tools.split(",") if t.strip()]
        rows.append({"module": module, "m_lo": m_lo, "m_hi": m_hi,
                     "m_range": f"{m_lo}-{m_hi}", "tools": tool_list,
                     "n_m": int(m_hi[1:]) - int(m_lo[1:]) + 1})
    return rows


def _collect_usage() -> dict[str, set]:
    """module → set of paper ids that exercised it (from results/M*/results.json)."""
    usage: dict[str, set] = {}
    for rj in sorted(RESULTS_ROOT.glob("M*/results.json")):
        paper = rj.parent.name
        if paper in {"M7", "M17", "M26"}:
            continue  # skip meta-scanners' own meta tool_usage → re-run determinism
        try:
            data = json.loads(rj.read_text(encoding="utf-8"))
        except Exception:
            continue
        for entry in data.get("tool_usage", []):
            # entry like "foundation.metallic_score_raw (M01-M04)" or "ceid.ceid_score"
            mod = entry.split(".")[0].split()[0]
            usage.setdefault(mod, set()).add(paper)
    return usage


def run(provider: Optional[SeriesProvider] = None, seed: Optional[int] = None,
        outdir: Optional[Path] = None) -> dict:
    provider = provider or SimulatedProvider()  # unused; interface symmetry
    seed = exp_seed(M_NUM) if seed is None else int(seed)
    outdir = Path(outdir) if outdir else outdir_for(M_ID)

    taxonomy = _parse_taxonomy()
    usage = _collect_usage()

    def papers_for(module: str) -> str:
        return ", ".join(sorted(usage.get(module, set()),
                                key=lambda s: int(s[1:]))) or "—"

    n_tools = sum(r["n_m"] for r in taxonomy)  # span of M-numbers = formal-tool count

    # ── CSV + longtable ─────────────────────────────────────────────────────────
    csv_rows = [[r["m_range"], r["module"], "; ".join(r["tools"]), papers_for(r["module"])]
                for r in taxonomy]
    write_csv(outdir / "m7_tools.csv",
              ["m_range", "module", "tools", "used_in_papers"], csv_rows)

    (outdir / "tex").mkdir(parents=True, exist_ok=True)
    tbl = figtex.table(
        header=["M\\#", "Module", "Tools", "Used in"],
        rows=[[r["m_range"], r["module"].replace("_", "\\_"),
               "; ".join(t.replace("_", "\\_") for t in r["tools"]), papers_for(r["module"])]
              for r in taxonomy],
        caption=(f"The {n_tools}-tool taxonomy of the persona\\_math framework (M01–M55), "
                 "auto-generated from the package and cross-referenced to the M1–M10 papers "
                 f"that exercise each module (Hesaplanan; seed={seed})."),
        label="tab:m7_tools", source=SOURCE, tier=Tier.HESAPLANAN.value, seed=seed,
        col_spec="llp{5.5cm}l", longtable=True, escape_cells=False)
    (outdir / "tex" / "m7_tools_table.tex").write_text(tbl, encoding="utf-8")

    results = {
        "metadata": run_metadata(M_ID, seed, {"n_modules": len(taxonomy)}),
        "tool_usage": TOOL_USAGE,
        "n_formal_tools": stamp(n_tools, tier=Tier.HESAPLANAN, seed=seed,
                                note="span M01–M55 from persona_math docstring"),
        "taxonomy": [{"m_range": r["m_range"], "module": r["module"], "tools": r["tools"],
                      "used_in_papers": sorted(usage.get(r["module"], set()),
                                               key=lambda s: int(s[1:]))}
                     for r in taxonomy],
        "module_usage": {m: sorted(p, key=lambda s: int(s[1:])) for m, p in usage.items()},
    }
    write_json(outdir / "results.json", results)
    return {"id": M_ID, "outdir": str(outdir), "tool_usage": TOOL_USAGE,
            "headline": {"n_formal_tools": n_tools, "n_modules": len(taxonomy)}}
