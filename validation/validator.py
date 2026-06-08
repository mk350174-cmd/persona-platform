"""
AcademicValidator — re-measure the M1–M60 simulation results with PersonaNeedle and (only
with a trained model) upgrade their tier from Simulated/Computed to Measured.

In this repo environment PersonaNeedle is untrained (no torch/GPU/checkpoint), so validation
runs the ``persona_math`` fallback: the "measured" values equal the reference, agreement is
1.0, and **no tier is upgraded to Measured** (``TierUpdater`` rejects Measured without a
trained model). The pipeline is the mechanism that performs the real upgrade once PATCH-04
training has run. Nothing here is ever stamped ``Ölçülmüş``.

    python -m validation.validator --paper M1 --dry-run
    python -m validation.validator --all --workers 2
"""

from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import numpy as np

from .paper_probe import PaperProbe, _ceid_fallback
from .tier_updater import TierUpdater

_REPO = Path(__file__).resolve().parent.parent


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class AcademicValidator:
    def __init__(self, needle_cache: Optional[dict] = None,
                 results_dir: str = "results/", papers_dir: str = "papers/",
                 out_dir: str = "validation/"):
        self.needle_cache = needle_cache or {}
        self.results_dir = _REPO / results_dir
        self.papers_dir = _REPO / papers_dir
        self.out_dir = _REPO / out_dir
        self.measured_dir = self.out_dir / "measured"
        self.progress_path = self.out_dir / "progress.json"
        self.probe = PaperProbe()
        self.tier_updater = TierUpdater()

    def _needle_for(self, persona_id: str):
        """A trained PersonaNeedle if one is cached/available, else None (fallback)."""
        if persona_id in self.needle_cache:
            return self.needle_cache[persona_id]
        return None

    def validate_paper(self, paper_id: str, dry_run: bool = False) -> dict:
        # reference per-persona CEID (from the library) = the simulation baseline
        scenario = self.probe.get_scenario(paper_id)
        needle = self._needle_for(scenario["personas"][0]) if scenario["personas"] else None
        measured = self.probe.run_scenario(paper_id, needle=needle)

        from persona_math.persona_library import get_library_persona
        diffs = []
        for pid, mvals in measured["measurements"].items():
            try:
                ref = _ceid_fallback(np.asarray(get_library_persona(pid), dtype=float))
            except Exception:
                continue
            diffs.append(abs(float(mvals.get("composite", ref["composite"])) - ref["composite"]))
        ceid_mae = round(float(np.mean(diffs)), 4) if diffs else 0.0
        agreement = round(1.0 - ceid_mae, 4)
        untrained = measured["untrained"]

        tier_before = self.tier_updater.current_tier(paper_id)
        # only a *trained* measurement can reach Measured; untrained → stays put
        upgraded = self.tier_updater.upgrade_tier(
            paper_id, "Measured",
            {"untrained": untrained, "ceid_mae": ceid_mae, "agreement": agreement,
             "metric": measured["metric"]}) if not dry_run else False
        tier_after = self.tier_updater.current_tier(paper_id)

        result = {
            "paper_id": paper_id,
            "tier_before": tier_before, "tier_after": tier_after, "upgraded": upgraded,
            "ceid_mae": ceid_mae, "drift_f1": None, "agreement": agreement,
            "n_personas": measured["n_personas"], "untrained": untrained,
            "validated_at": _now(),
            "note": ("untrained — persona_math fallback (measured==reference); no Measured upgrade"
                     if untrained else "measured with a trained PersonaNeedle"),
        }
        if not dry_run:
            self.measured_dir.mkdir(parents=True, exist_ok=True)
            (self.measured_dir / f"{paper_id}.json").write_text(
                json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        return result

    def validate_all(self, paper_ids: Optional[list] = None, resume: bool = True,
                     workers: int = 2) -> dict:
        ids = paper_ids or [f"M{i}" for i in range(1, 61)]
        done = {}
        if resume and self.progress_path.exists():
            done = json.loads(self.progress_path.read_text(encoding="utf-8"))
        pending = [p for p in ids if p not in done]

        results = dict(done)
        failed = []
        with ThreadPoolExecutor(max_workers=max(1, workers)) as ex:
            futures = {ex.submit(self.validate_paper, p): p for p in pending}
            for fut in as_completed(futures):
                pid = futures[fut]
                try:
                    results[pid] = fut.result()
                except Exception as exc:        # pragma: no cover
                    failed.append({"paper_id": pid, "error": str(exc)})
        self.out_dir.mkdir(parents=True, exist_ok=True)
        self.progress_path.write_text(json.dumps(results, ensure_ascii=False, indent=2),
                                      encoding="utf-8")

        maes = [r["ceid_mae"] for r in results.values() if r.get("ceid_mae") is not None]
        agrs = [r["agreement"] for r in results.values() if r.get("agreement") is not None]
        tier_changes = {}
        for r in results.values():
            if r.get("upgraded"):
                key = f"{r['tier_before']}→{r['tier_after']}"
                tier_changes[key] = tier_changes.get(key, 0) + 1
        return {
            "total": len(ids), "validated": len(results), "failed": failed,
            "avg_ceid_mae": round(float(np.mean(maes)), 4) if maes else None,
            "avg_agreement": round(float(np.mean(agrs)), 4) if agrs else None,
            "tier_changes": tier_changes,        # empty here (untrained → no Measured upgrades)
            "measured_count": sum(r.get("tier_after") == "Measured" for r in results.values()),
        }

    def update_manifest(self, validation_results: dict) -> dict:
        """Apply tier upgrades to the manifest (no-op while untrained). Returns the tier report."""
        return self.tier_updater.generate_tier_report()


def main(argv=None) -> int:
    import argparse
    ap = argparse.ArgumentParser(description="Academic validation of M1–M60 via PersonaNeedle")
    ap.add_argument("--paper", default=None, help="validate a single paper (e.g. M1)")
    ap.add_argument("--all", action="store_true", help="validate M1–M60")
    ap.add_argument("--workers", type=int, default=2)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args(argv)

    v = AcademicValidator()
    if args.paper:
        print(json.dumps(v.validate_paper(args.paper, dry_run=args.dry_run),
                         ensure_ascii=False, indent=2))
    elif args.all:
        print(json.dumps(v.validate_all(workers=args.workers), ensure_ascii=False, indent=2))
    else:
        ap.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
