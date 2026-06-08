"""
run_all — run the M1–M10 experiment harness reproducibly.

    python -m experiments.run_all                 # run all, default master seed
    python -m experiments.run_all --only M1 M4     # subset
    python -m experiments.run_all --check-provenance   # audit results/, no run

Experiments run in pyramid order (Core Triple → Application → Field → M7 last,
since M7 consumes the others' tool_usage records).
"""

from __future__ import annotations

import argparse
import importlib
import json
import sys
import traceback
from pathlib import Path

from ._common import RESULTS_ROOT
from .provenance import FRAMEWORK_VERSION, MASTER_SEED, STAMP_KEYS, Tier

# (paper id, module) in execution order. Meta-scanners (M7 tool table, M17
# bibliometrics) run LAST so they capture every other paper's outputs.
REGISTRY = [
    # Batch 1
    ("M1", "experiments.exp_m1_metallic"),
    ("M2", "experiments.exp_m2_mandatory_core"),
    ("M3", "experiments.exp_m3_ceid_protocol"),
    ("M4", "experiments.exp_m4_court"),
    ("M5", "experiments.exp_m5_kimera_tensor"),
    ("M6", "experiments.exp_m6_arkhe"),
    ("M8", "experiments.exp_m8_hpep_convergent"),
    ("M9", "experiments.exp_m9_ppep_proxy"),
    ("M10", "experiments.exp_m10_atlas"),
    # Batch 2 (M16/M19 = empirical priorities first)
    ("M16", "experiments.exp_m16_d1_multi"),
    ("M19", "experiments.exp_m19_rock_river"),
    ("M11", "experiments.exp_m11_hegesias"),
    ("M14", "experiments.exp_m14_consent"),
    ("M12", "experiments.exp_m12_researcher"),
    ("M13", "experiments.exp_m13_digital_copy"),
    ("M15", "experiments.exp_m15_soul_test"),
    ("M18", "experiments.exp_m18_amcc"),
    ("M20", "experiments.exp_m20_termination"),
    # Batch 3 (M21–M30)
    ("M21", "experiments.exp_m21_meta_awareness"),
    ("M22", "experiments.exp_m22_synchrony"),
    ("M23", "experiments.exp_m23_hegesias_history"),
    ("M24", "experiments.exp_m24_vine_tree"),
    ("M25", "experiments.exp_m25_poetic_method"),
    ("M27", "experiments.exp_m27_organizational"),
    ("M28", "experiments.exp_m28_empathy"),
    ("M29", "experiments.exp_m29_faction"),
    ("M30", "experiments.exp_m30_clinical_drift"),
    # Batch 4 (M31–M40)
    ("M31", "experiments.exp_m31_ceid_validation"),
    ("M32", "experiments.exp_m32_hpep_short"),
    ("M33", "experiments.exp_m33_crosslingual"),
    ("M34", "experiments.exp_m34_chimera5"),
    ("M35", "experiments.exp_m35_arch_atlas"),
    ("M36", "experiments.exp_m36_hallucination"),
    ("M37", "experiments.exp_m37_dsuite"),
    ("M38", "experiments.exp_m38_distributed"),
    ("M39", "experiments.exp_m39_conflict"),
    ("M40", "experiments.exp_m40_finetuning"),
    # Batch 5 (M41–M50)
    ("M41", "experiments.exp_m41_ptsd"),
    ("M42", "experiments.exp_m42_adolescent_arkhe"),
    ("M43", "experiments.exp_m43_wisdom"),
    ("M44", "experiments.exp_m44_narcissism"),
    ("M45", "experiments.exp_m45_ego_dissolution"),
    ("M46", "experiments.exp_m46_addiction"),
    ("M47", "experiments.exp_m47_parenting"),
    ("M48", "experiments.exp_m48_musician"),
    ("M49", "experiments.exp_m49_character_residue"),
    ("M50", "experiments.exp_m50_author_voice"),
    # Batch 6 (M51–M60)
    ("M51", "experiments.exp_m51_cinema"),
    ("M52", "experiments.exp_m52_artist_block"),
    ("M53", "experiments.exp_m53_authoritarian"),
    ("M54", "experiments.exp_m54_ai_safety"),
    ("M55", "experiments.exp_m55_education"),
    ("M56", "experiments.exp_m56_collective_trauma"),
    ("M57", "experiments.exp_m57_climate"),
    ("M58", "experiments.exp_m58_free_will"),
    ("M59", "experiments.exp_m59_consciousness"),
    ("M60", "experiments.exp_m60_mortality"),
    # Meta-scanners LAST (consume others' tool_usage / cross-refs)
    ("M26", "experiments.exp_m26_institutional"),
    ("M7", "experiments.exp_m7_tool_table"),
    ("M17", "experiments.exp_m17_polymathy"),
]

# Paper ids whose tool_usage is meta (scanners) — excluded from each other's scans.
META_SCANNERS = {"M7", "M17", "M26"}


def _walk_stamps(obj):
    """Yield every provenance stamp dict found anywhere in ``obj``."""
    if isinstance(obj, dict):
        if "tier" in obj and "framework_version" in obj:
            yield obj
        for v in obj.values():
            yield from _walk_stamps(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from _walk_stamps(v)


def check_provenance(results_root: Path = RESULTS_ROOT) -> list[str]:
    """Audit every results.json: no Ölçülmüş tier, required keys, version match."""
    problems: list[str] = []
    files = sorted(results_root.glob("M*/results.json"))
    if not files:
        return ["no results/M*/results.json found — run experiments first"]
    for rj in files:
        data = json.loads(rj.read_text(encoding="utf-8"))
        for st in _walk_stamps(data):
            missing = STAMP_KEYS - set(st)
            if missing:
                problems.append(f"{rj.parent.name}: stamp missing keys {sorted(missing)}")
            if st.get("tier") == Tier.OLCULMUS.value:
                problems.append(f"{rj.parent.name}: FORBIDDEN 'Ölçülmüş' tier emitted")
            if st.get("tier") not in {t.value for t in Tier}:
                problems.append(f"{rj.parent.name}: unknown tier {st.get('tier')!r}")
            if st.get("framework_version") != FRAMEWORK_VERSION:
                problems.append(f"{rj.parent.name}: framework_version "
                                f"{st.get('framework_version')} != {FRAMEWORK_VERSION}")
    return problems


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Persona M1–M10 experiment harness")
    ap.add_argument("--only", nargs="+", metavar="Mn", help="run only these paper ids")
    ap.add_argument("--seed", type=int, default=None,
                    help=f"override per-experiment seed base (default master {MASTER_SEED})")
    ap.add_argument("--out", default=None, help="results output root (default results/)")
    ap.add_argument("--check-provenance", action="store_true",
                    help="audit results/ for tier/version integrity, then exit")
    args = ap.parse_args(argv)

    out_root = Path(args.out) if args.out else None

    if args.check_provenance:
        problems = check_provenance(out_root or RESULTS_ROOT)
        if problems:
            print(f"PROVENANCE CHECK FAILED ({len(problems)}):")
            for p in problems:
                print("  -", p)
            return 1
        print("PROVENANCE CHECK OK — no 'Ölçülmüş' tier; all stamps valid.")
        return 0

    todo = [(i, m) for i, m in REGISTRY if not args.only or i in set(args.only)]
    if not todo:
        print(f"nothing to run for --only {args.only}")
        return 1

    rc = 0
    summary = []
    for paper_id, modpath in todo:
        try:
            mod = importlib.import_module(modpath)
            outdir = (out_root / paper_id) if out_root else None
            res = mod.run(seed=args.seed, outdir=outdir)
            summary.append((paper_id, "OK", res.get("headline", {})))
            print(f"[{paper_id}] OK  {res.get('headline', {})}")
        except Exception as exc:  # noqa: BLE001
            rc = 1
            summary.append((paper_id, f"FAIL: {exc}", {}))
            print(f"[{paper_id}] FAILED: {exc}")
            traceback.print_exc()

    print("\n=== summary ===")
    for paper_id, status, head in summary:
        print(f"  {paper_id:4s} {status}")

    # auto-audit provenance after a full run
    if not args.only:
        prob = check_provenance(out_root or RESULTS_ROOT)
        if prob:
            rc = 1
            print("\nPROVENANCE problems:")
            for p in prob:
                print("  -", p)
        else:
            print("\nprovenance: OK (no 'Ölçülmüş' tier emitted)")
    return rc


if __name__ == "__main__":
    sys.exit(main())
