"""
io_utils — result writers (JSON / CSV / pgfplots .dat), LaTeX escaping, and a
LaTeX-syntax linter (used as the figure-quality gate since no pdflatex exists).

Run the linter standalone::

    python -m experiments.io_utils --lint results/
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from pathlib import Path
from typing import Any, Iterable, Sequence

import numpy as np

# Compile from the papers/ directory: snippets reference ../results/... .
_REPO_ROOT = Path(__file__).resolve().parent.parent
_PAPERS_DIR = _REPO_ROOT / "papers"

__all__ = [
    "ensure_dir",
    "to_jsonable",
    "write_json",
    "write_csv",
    "write_dat",
    "latex_escape",
    "lint_tex_tree",
]


def ensure_dir(path: Path | str) -> Path:
    p = Path(path)
    p.mkdir(parents=True, exist_ok=True)
    return p


def to_jsonable(obj: Any) -> Any:
    """Recursively convert numpy scalars/arrays into plain Python for JSON."""
    if isinstance(obj, dict):
        return {str(k): to_jsonable(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [to_jsonable(v) for v in obj]
    if isinstance(obj, np.ndarray):
        return to_jsonable(obj.tolist())
    if isinstance(obj, (np.floating,)):
        return float(obj)
    if isinstance(obj, (np.integer,)):
        return int(obj)
    if isinstance(obj, (np.bool_,)):
        return bool(obj)
    return obj


def write_json(path: Path | str, obj: Any) -> Path:
    path = Path(path)
    ensure_dir(path.parent)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(to_jsonable(obj), f, ensure_ascii=False, indent=2, sort_keys=True)
        f.write("\n")
    return path


def write_csv(path: Path | str, header: Sequence[str], rows: Iterable[Sequence[Any]]) -> Path:
    path = Path(path)
    ensure_dir(path.parent)
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(list(header))
        for row in rows:
            w.writerow([_csv_cell(c) for c in row])
    return path


def _csv_cell(c: Any) -> Any:
    if isinstance(c, (np.floating, float)):
        return f"{float(c):.6g}"
    if isinstance(c, (np.integer,)):
        return int(c)
    return c


def _fmt_num(x: Any) -> str:
    return f"{float(x):.6g}"


def write_dat(path: Path | str, header: Sequence[str], data: Any) -> Path:
    """Write a pgfplots-friendly whitespace table with a ``# col col`` header."""
    path = Path(path)
    ensure_dir(path.parent)
    arr = np.asarray(data, dtype=float)
    if arr.ndim == 1:
        arr = arr.reshape(-1, 1)
    if arr.shape[1] != len(header):
        raise ValueError(
            f"{path.name}: {arr.shape[1]} columns but {len(header)} header labels"
        )
    with open(path, "w", encoding="utf-8") as f:
        f.write("# " + "   ".join(header) + "\n")
        for row in arr:
            f.write("   ".join(_fmt_num(v) for v in row) + "\n")
    return path


# ── LaTeX escaping ──────────────────────────────────────────────────────────────

_LATEX_SPECIAL = {
    "&": r"\&",
    "%": r"\%",
    "$": r"\$",
    "#": r"\#",
    "_": r"\_",
    "{": r"\{",
    "}": r"\}",
    "~": r"\textasciitilde{}",
    "^": r"\textasciicircum{}",
}


def latex_escape(s: Any) -> str:
    """Escape LaTeX-special characters in free text (captions, labels)."""
    out = []
    for ch in str(s):
        out.append(_LATEX_SPECIAL.get(ch, ch))
    return "".join(out)


# ── LaTeX-syntax linter (no pdflatex available) ─────────────────────────────────

_BEGIN_RE = re.compile(r"\\begin\{([^}]+)\}")
_END_RE = re.compile(r"\\end\{([^}]+)\}")
_ADDPLOT_TABLE_RE = re.compile(r"\\addplot[^;]*?table[^{]*\{([^}]+)\}")


def _lint_one(text: str, tex_path: Path, base_dir: Path) -> list[str]:
    problems: list[str] = []

    # 1. balanced braces (ignoring escaped \{ \})
    stripped = text.replace(r"\{", "").replace(r"\}", "")
    if stripped.count("{") != stripped.count("}"):
        problems.append(f"{tex_path.name}: unbalanced braces "
                        f"({stripped.count('{')} '{{' vs {stripped.count('}')} '}}')")

    # 2. balanced begin/end environments
    begins = sorted(_BEGIN_RE.findall(text))
    ends = sorted(_END_RE.findall(text))
    if begins != ends:
        problems.append(f"{tex_path.name}: \\begin/\\end mismatch {begins} vs {ends}")

    # 3. data-only: no raster/vector image includes
    if "\\includegraphics" in text:
        problems.append(f"{tex_path.name}: contains \\includegraphics (figures must "
                        f"be data-only pgfplots)")

    # 4. every \addplot table path resolves (relative to the compile dir = papers/)
    for rel in _ADDPLOT_TABLE_RE.findall(text):
        rel = rel.strip()
        resolved = (base_dir / rel).resolve()
        if not resolved.exists():
            problems.append(f"{tex_path.name}: \\addplot table path does not resolve: "
                            f"{rel} (looked at {resolved})")
    return problems


def lint_tex_tree(root: Path | str, base_dir: Path | None = None) -> list[str]:
    """Lint every ``*.tex`` under ``root``. ``base_dir`` is the LaTeX compile dir
    used to resolve ``\\addplot table`` paths (defaults to ``papers/``)."""
    root = Path(root)
    base_dir = Path(base_dir) if base_dir is not None else _PAPERS_DIR
    problems: list[str] = []
    for tex_path in sorted(root.rglob("*.tex")):
        text = tex_path.read_text(encoding="utf-8")
        problems.extend(_lint_one(text, tex_path, base_dir))
    return problems


def _main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Persona experiments I/O utilities")
    ap.add_argument("--lint", metavar="DIR", help="lint *.tex under DIR")
    ap.add_argument("--base-dir", default=None,
                    help="compile dir for resolving \\addplot paths (default papers/)")
    args = ap.parse_args(argv)
    if args.lint:
        problems = lint_tex_tree(args.lint, base_dir=args.base_dir)
        if problems:
            print(f"LaTeX lint FAILED ({len(problems)} problem(s)):")
            for p in problems:
                print("  -", p)
            return 1
        print(f"LaTeX lint OK — all *.tex under {args.lint} passed.")
        return 0
    ap.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
