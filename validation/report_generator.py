"""
ValidationReportGenerator — turn validation results into the M61 LaTeX table, a numeric
summary for the M61 Results section, and a human-readable Markdown report.

``results`` is a ``{paper_id: validate_paper(...) dict}`` mapping (e.g. the contents of
``validation/progress.json``). With an untrained model every ``tier_after`` is the paper's
existing tier and ``Measured`` count is 0 — reported honestly.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from experiments import figtex
from .tier_updater import TierUpdater

_REPO = Path(__file__).resolve().parent.parent


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _sorted_items(results: dict):
    return sorted(results.items(), key=lambda kv: int(kv[0][1:]) if kv[0][1:].isdigit() else 999)


class ValidationReportGenerator:
    def generate_latex_table(self, results: dict,
                             output_path: str = "papers/M61_experiments/validation_table.tex") -> str:
        rows = []
        for pid, r in _sorted_items(results):
            rows.append([
                pid, r.get("tier_before", "?"), r.get("tier_after", "?"),
                f"{r.get('ceid_mae'):.4f}" if r.get("ceid_mae") is not None else "—",
                f"{r.get('drift_f1'):.3f}" if r.get("drift_f1") is not None else "—",
                f"{r.get('agreement'):.4f}" if r.get("agreement") is not None else "—",
            ])
        stats = self.generate_summary_stats(results)
        rows.append(["Summary", "", f"Measured: {stats['measured_count']}",
                     f"{stats['avg_ceid_mae']:.4f}" if stats["avg_ceid_mae"] is not None else "—",
                     f"{stats['avg_drift_f1']:.3f}" if stats["avg_drift_f1"] is not None else "—",
                     f"{stats['avg_agreement']:.4f}" if stats["avg_agreement"] is not None else "—"])
        tex = figtex.table(
            header=["ID", "Tier before", "Tier after", "CEID MAE", "Drift F1", "Agreement"],
            rows=rows, col_spec="lllrrr", longtable=True, escape_cells=False,
            caption=("PersonaNeedle re-measurement of the M1--M60 series. Tier-after equals "
                     "tier-before and Measured=0 while the model is untrained (persona_math "
                     "fallback); the Measured upgrade follows PATCH-04 training. Tier: Simülasyon."),
            label="tab:m61_validation", source="validation/report_generator.py",
            tier="Simülasyon", seed=0)
        out = _REPO / output_path
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(tex, encoding="utf-8")
        return tex

    def generate_summary_stats(self, results: dict) -> dict:
        maes = [r["ceid_mae"] for r in results.values() if r.get("ceid_mae") is not None]
        f1s = [r["drift_f1"] for r in results.values() if r.get("drift_f1") is not None]
        agrs = [r["agreement"] for r in results.values() if r.get("agreement") is not None]
        return {
            "avg_ceid_mae": round(sum(maes) / len(maes), 4) if maes else None,
            "avg_drift_f1": round(sum(f1s) / len(f1s), 4) if f1s else None,
            "avg_agreement": round(sum(agrs) / len(agrs), 4) if agrs else None,
            "tier_upgrade_count": sum(1 for r in results.values() if r.get("upgraded")),
            "measured_count": sum(1 for r in results.values() if r.get("tier_after") == "Measured"),
            "total_measurements": sum(r.get("n_personas", 0) for r in results.values()),
        }

    def generate_markdown_report(self, results: dict,
                                 output_path: str = "validation/REPORT.md") -> str:
        stats = self.generate_summary_stats(results)
        tier_report = TierUpdater().generate_tier_report()
        lines = [
            "# Academic Validation Report",
            "",
            f"_Generated {_now()} by `validation/report_generator.py`._",
            "",
            "## Status",
            "",
            f"- Papers validated: **{len(results)}**",
            f"- Measured tier reached: **{stats['measured_count']}** "
            f"(0 until PersonaNeedle is trained — PATCH-04)",
            f"- Tier upgrades: **{stats['tier_upgrade_count']}**",
            f"- Total persona measurements: **{stats['total_measurements']}**",
            f"- Avg CEID MAE: **{stats['avg_ceid_mae']}** · Avg agreement: **{stats['avg_agreement']}**",
            "",
            "## Tier distribution (per-paper highest tier)",
            "",
            "| Tier | Before | After |",
            "|------|--------|-------|",
        ]
        for t in ("Estimated", "Simulated", "Computed", "Measured"):
            lines.append(f"| {t} | {tier_report['before'].get(t, 0)} | {tier_report['after'].get(t, 0)} |")
        lines += [
            "",
            "## Integrity",
            "",
            "PersonaNeedle is **untrained** in this environment (no torch/GPU/checkpoint), so "
            "validation uses the `persona_math` reference fallback: measured values equal the "
            "reference, agreement is 1.0, and **no paper is upgraded to `Measured` / `Ölçülmüş`**. "
            "Running this pipeline on a trained model (PATCH-04) is what performs the real "
            "`Simulated → Measured` upgrade. No simulated value is ever presented as measured.",
            "",
        ]
        out = _REPO / output_path
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return "\n".join(lines)


def main(argv=None) -> int:
    import argparse
    import json
    ap = argparse.ArgumentParser(description="Generate validation report + M61 table")
    ap.add_argument("--output", default="validation/REPORT.md")
    args = ap.parse_args(argv)
    progress = _REPO / "validation" / "progress.json"
    results = json.loads(progress.read_text(encoding="utf-8")) if progress.exists() else {}
    gen = ValidationReportGenerator()
    gen.generate_markdown_report(results, output_path=args.output)
    gen.generate_latex_table(results)
    print(f"wrote {args.output} + papers/M61_experiments/validation_table.tex "
          f"({len(results)} papers)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
