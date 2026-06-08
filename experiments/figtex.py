"""
figtex — generate ``\\input``-able LaTeX snippets (pgfplots figures + tables).

All figures are *data-only*: a ``\\addplot table`` reading a ``.dat`` file, never
an ``\\includegraphics``. Every snippet starts with an AUTO-GENERATED provenance
comment naming the source script, value tier and seed, so a reviewer sees the
tier inline. Data paths are written relative to the ``papers/`` compile dir
(``../results/M{n}/figdata/...``).
"""

from __future__ import annotations

from typing import Sequence

from .io_utils import latex_escape

_DATA_BASE = "../results"  # relative to papers/ at compile time


def _provenance_comment(source: str, tier: str, seed: int, extra: str = "") -> str:
    line = f"% AUTO-GENERATED — {source} — tier={tier} — seed={seed}"
    if extra:
        line += f" — {extra}"
    return (
        "% " + "=" * 70 + "\n"
        + line + "\n"
        + "% Regenerate: make experiments  (do not edit by hand)\n"
        + "% " + "=" * 70 + "\n"
    )


def line_figure(
    *,
    m_id: str,
    dat_name: str,
    columns: Sequence[tuple[int, str]],
    xlabel: str,
    ylabel: str,
    caption: str,
    label: str,
    source: str,
    tier: str,
    seed: int,
    legend: Sequence[str] | None = None,
) -> str:
    """A multi-series line plot. ``columns`` = list of (column_index, legend_name);
    column 0 is assumed to be x."""
    dat = f"{_DATA_BASE}/{m_id}/figdata/{dat_name}"
    plots = []
    for col_idx, name in columns:
        plots.append(
            f"  \\addplot table[x index=0, y index={col_idx}] {{{dat}}};"
        )
        if legend is None:
            plots.append(f"  \\addlegendentry{{{latex_escape(name)}}}")
    if legend is not None:
        legend_line = "  \\legend{" + ", ".join(latex_escape(s) for s in legend) + "}\n"
    else:
        legend_line = ""
    body = "\n".join(plots)
    return (
        _provenance_comment(source, tier, seed)
        + "\\begin{figure}[htbp]\n\\centering\n"
        "\\begin{tikzpicture}\n"
        f"\\begin{{axis}}[width=0.85\\linewidth, height=6cm, grid=both,\n"
        f"  xlabel={{{latex_escape(xlabel)}}}, ylabel={{{latex_escape(ylabel)}}},\n"
        f"  legend pos=outer north east]\n"
        f"{body}\n"
        f"{legend_line}"
        "\\end{axis}\n\\end{tikzpicture}\n"
        f"\\caption{{{caption}}}\n"
        f"\\label{{{label}}}\n"
        "\\end{figure}\n"
    )


def scatter_figure(
    *,
    m_id: str,
    dat_name: str,
    xlabel: str,
    ylabel: str,
    caption: str,
    label: str,
    source: str,
    tier: str,
    seed: int,
    meta_col: int = 2,
) -> str:
    """A 2D scatter coloured by an integer class column (e.g. cluster id)."""
    dat = f"{_DATA_BASE}/{m_id}/figdata/{dat_name}"
    return (
        _provenance_comment(source, tier, seed)
        + "\\begin{figure}[htbp]\n\\centering\n"
        "\\begin{tikzpicture}\n"
        f"\\begin{{axis}}[width=0.85\\linewidth, height=7cm, grid=both,\n"
        f"  xlabel={{{latex_escape(xlabel)}}}, ylabel={{{latex_escape(ylabel)}}},\n"
        "  scatter/use mapped color={draw=mapped color, fill=mapped color}]\n"
        f"  \\addplot[scatter, only marks, scatter src=explicit symbolic,\n"
        f"    point meta=explicit] table[x index=0, y index=1, meta index={meta_col}]\n"
        f"    {{{dat}}};\n"
        "\\end{axis}\n\\end{tikzpicture}\n"
        f"\\caption{{{caption}}}\n"
        f"\\label{{{label}}}\n"
        "\\end{figure}\n"
    )


def table(
    *,
    header: Sequence[str],
    rows: Sequence[Sequence[object]],
    caption: str,
    label: str,
    source: str,
    tier: str,
    seed: int,
    col_spec: str | None = None,
    longtable: bool = False,
    escape_cells: bool = True,
) -> str:
    """A booktabs table (or longtable). Cells are LaTeX-escaped unless they are
    already-formatted strings (``escape_cells=False``)."""
    ncol = len(header)
    spec = col_spec or ("l" + "r" * (ncol - 1))

    def fmt_cell(c: object) -> str:
        if isinstance(c, float):
            return f"{c:.4g}"
        return latex_escape(c) if escape_cells else str(c)

    head_row = " & ".join(f"\\textbf{{{latex_escape(h)}}}" for h in header) + " \\\\"
    body_rows = "\n".join(" & ".join(fmt_cell(c) for c in r) + " \\\\" for r in rows)

    if longtable:
        return (
            _provenance_comment(source, tier, seed)
            + f"\\begin{{longtable}}{{{spec}}}\n"
            f"\\caption{{{caption}}}\\label{{{label}}}\\\\\n"
            "\\toprule\n"
            f"{head_row}\n\\midrule\n\\endfirsthead\n"
            "\\toprule\n"
            f"{head_row}\n\\midrule\n\\endhead\n"
            f"{body_rows}\n"
            "\\bottomrule\n"
            "\\end{longtable}\n"
        )
    return (
        _provenance_comment(source, tier, seed)
        + "\\begin{table}[htbp]\n\\centering\n"
        f"\\begin{{tabular}}{{{spec}}}\n"
        "\\toprule\n"
        f"{head_row}\n\\midrule\n"
        f"{body_rows}\n"
        "\\bottomrule\n"
        "\\end{tabular}\n"
        f"\\caption{{{caption}}}\n"
        f"\\label{{{label}}}\n"
        "\\end{table}\n"
    )
