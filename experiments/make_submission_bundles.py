"""
make_submission_bundles — build self-contained, uploadable bundles per finalized paper.

The finalized papers ``\\input{../results/M{n}/tex/…}`` and those snippets
``\\addplot table {../results/M{n}/figdata/…}``. That works for a local compile from
``papers/`` but NOT for a journal/arXiv upload, which must be self-contained. This
tool produces, for each finalized paper::

    submissions/M{n}/<paper>.tex      # \\input paths rewritten to local tex/
    submissions/M{n}/tex/*.tex        # snippets, \\addplot paths rewritten to local figdata/
    submissions/M{n}/figdata/*.dat    # the pgfplots data
    submissions/M{n}/README.md        # compile + provenance note

Each bundle compiles standalone (``cd submissions/M{n} && pdflatex <paper>.tex``) once
a LaTeX toolchain is available. Idempotent: rebuilds submissions/ from scratch.

    python -m experiments.make_submission_bundles
"""

from __future__ import annotations

import re
import shutil
from pathlib import Path

from .build_manifest import FINALIZED

_REPO = Path(__file__).resolve().parent.parent
_PAPERS = _REPO / "papers"
_RESULTS = _REPO / "results"
_OUT = _REPO / "submissions"

_PAPER_INPUT = re.compile(r"\\input\{\.\./results/(M\d+)/tex/([^}]+)\}")
_SNIPPET_DAT = re.compile(r"(\\addplot[^;]*?table[^{]*\{)\.\./results/M\d+/figdata/([^}]+)(\})")
_DAT_REF = re.compile(r"\.\./results/M\d+/figdata/([^}]+\.dat)")

_README = """# Submission bundle — {pid}

Self-contained copy of `{paper}` with all `\\input`/`\\addplot` paths rewritten to be
local (`tex/`, `figdata/`). Compile from this directory:

    pdflatex {paper}   # (run twice for refs); or latexmk -pdf {paper}

Figures are pgfplots data (`figdata/*.dat`) — no external assets. All embedded numbers
are simulation/calculation results (tier-stamped Simülasyon/Hesaplanan/Tahmini in
`../../results/{pid}/results.json`); none is a real-LLM measurement. Regenerate results
with `make experiments` at the repo root.
"""


def _paper_file(pid: str) -> Path | None:
    hits = sorted(_PAPERS.glob(f"{pid}_*.tex"))
    return hits[0] if hits else None


def build_bundle(pid: str) -> dict:
    paper = _paper_file(pid)
    if paper is None:
        return {"id": pid, "status": "no .tex"}
    text = paper.read_text(encoding="utf-8")
    bundle = _OUT / pid
    (bundle / "tex").mkdir(parents=True, exist_ok=True)
    (bundle / "figdata").mkdir(parents=True, exist_ok=True)

    n_snip = n_dat = 0
    for m in _PAPER_INPUT.finditer(text):
        snip_pid, snip_name = m.group(1), m.group(2)
        snip_src = _RESULTS / snip_pid / "tex" / snip_name
        if not snip_src.exists():
            continue
        snip = snip_src.read_text(encoding="utf-8")
        # copy referenced .dat files
        for dat_name in _DAT_REF.findall(snip):
            dat_src = _RESULTS / snip_pid / "figdata" / dat_name
            if dat_src.exists():
                shutil.copy2(dat_src, bundle / "figdata" / dat_name)
                n_dat += 1
        # rewrite snippet \addplot paths → local figdata/
        snip_local = _SNIPPET_DAT.sub(r"\1figdata/\2\3", snip)
        (bundle / "tex" / snip_name).write_text(snip_local, encoding="utf-8")
        n_snip += 1

    # rewrite paper \input paths → local tex/
    paper_local = _PAPER_INPUT.sub(r"\\input{tex/\2}", text)
    (bundle / paper.name).write_text(paper_local, encoding="utf-8")
    (bundle / "README.md").write_text(_README.format(pid=pid, paper=paper.name), encoding="utf-8")
    return {"id": pid, "status": "ok", "paper": paper.name, "snippets": n_snip, "dat": n_dat}


def main() -> int:
    if _OUT.exists():
        shutil.rmtree(_OUT)
    _OUT.mkdir(parents=True, exist_ok=True)
    rows = [build_bundle(pid) for pid in sorted(FINALIZED, key=lambda s: int(s[1:]))]
    ok = sum(r["status"] == "ok" for r in rows)
    for r in rows:
        if r["status"] == "ok":
            print(f"  {r['id']:4s} {r['paper']:34s} tex={r['snippets']} dat={r['dat']}")
        else:
            print(f"  {r['id']:4s} {r['status']}")
    (_OUT / "README.md").write_text(
        "# Submission bundles\n\nOne self-contained, uploadable bundle per finalized paper "
        "(M1–M60). Each `M{n}/` compiles standalone (see its README). Regenerate with "
        "`python -m experiments.make_submission_bundles`. Journal/arXiv submission itself is a "
        "manual step (no outbound network here).\n", encoding="utf-8")
    print(f"\nbuilt {ok}/{len(rows)} bundles in submissions/")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
