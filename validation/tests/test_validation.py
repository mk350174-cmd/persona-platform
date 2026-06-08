"""
validation pipeline tests (PATCH-09) — torch-free.

PersonaNeedle is untrained here, so every path uses the persona_math fallback: tiers never
reach Measured and the integrity guard (no downgrade, no Measured-without-training) holds.
"""

import json

import pytest

from validation.paper_probe import PaperProbe, PAPER_SCENARIOS
from validation.tier_updater import TierUpdater, TIER_HIERARCHY
from validation.report_generator import ValidationReportGenerator
from validation.validator import AcademicValidator

# a small per-paper results fixture (as validate_paper would produce, untrained)
_RESULTS = {
    "M1": {"paper_id": "M1", "tier_before": "Simulated", "tier_after": "Simulated",
           "ceid_mae": 0.0, "drift_f1": None, "agreement": 1.0, "n_personas": 3, "upgraded": False},
    "M2": {"paper_id": "M2", "tier_before": "Computed", "tier_after": "Computed",
           "ceid_mae": 0.0, "drift_f1": None, "agreement": 1.0, "n_personas": 2, "upgraded": False},
}


# ── PaperProbe ─────────────────────────────────────────────────────────────────────

def test_get_scenario_known_format():
    sc = PaperProbe().get_scenario("M1")
    assert sc["paper_id"] == "M1" and sc["metric"] == PAPER_SCENARIOS["M1"]["metric"]
    assert isinstance(sc["personas"], list) and len(sc["personas"]) >= 1   # resolved real ids
    assert all(isinstance(p, str) for p in sc["personas"])


def test_get_scenario_default_for_unknown():
    sc = PaperProbe().get_scenario("M99")
    assert sc["paper_id"] == "M99" and len(sc["personas"]) >= 1            # default panel


# ── TierUpdater (monotonic; Measured needs training) ──────────────────────────────

def _tu(tmp_path):
    # isolate BOTH files in tmp so tests never touch the real manifest/tiers
    return TierUpdater(manifest_path=tmp_path / "manifest.json", tiers_path=tmp_path / "tiers.json")


def test_upgrade_simulated_to_measured_with_training(tmp_path):
    tu = _tu(tmp_path)
    assert tu.upgrade_tier("M1", "Measured", {"untrained": False}) is True   # trained evidence
    assert tu.current_tier("M1") == "Measured"


def test_downgrade_blocked(tmp_path):
    tu = _tu(tmp_path)
    tu.upgrade_tier("M1", "Measured", {"untrained": False})
    assert tu.upgrade_tier("M1", "Simulated", {"untrained": False}) is False  # no downgrade


def test_measured_blocked_when_untrained(tmp_path):
    tu = _tu(tmp_path)
    assert tu.upgrade_tier("M3", "Measured", {"untrained": True}) is False    # integrity guard
    assert tu.current_tier("M3") != "Measured"


def test_tier_report_format():
    rep = TierUpdater().generate_tier_report()
    assert set(rep["before"]) == set(TIER_HIERARCHY) and set(rep["after"]) == set(TIER_HIERARCHY)
    assert rep["before"].get("Measured", 0) == 0          # nothing measured yet


# ── ValidationReportGenerator ─────────────────────────────────────────────────────

def test_generate_latex_table(tmp_path):
    out = tmp_path / "validation_table.tex"
    tex = ValidationReportGenerator().generate_latex_table(_RESULTS, output_path=str(out))
    assert out.exists() and "\\begin{longtable}" in tex and "M1" in tex


def test_generate_summary_stats_fields():
    stats = ValidationReportGenerator().generate_summary_stats(_RESULTS)
    for k in ("avg_ceid_mae", "avg_drift_f1", "avg_agreement", "tier_upgrade_count",
              "measured_count", "total_measurements"):
        assert k in stats
    assert stats["measured_count"] == 0 and stats["total_measurements"] == 5


def test_generate_markdown_report(tmp_path):
    out = tmp_path / "REPORT.md"
    md = ValidationReportGenerator().generate_markdown_report(_RESULTS, output_path=str(out))
    assert out.exists() and "Academic Validation Report" in md


# ── AcademicValidator + manifest M61 ──────────────────────────────────────────────

def test_validate_paper_dry_run_untrained():
    res = AcademicValidator().validate_paper("M1", dry_run=True)
    assert res["paper_id"] == "M1" and res["untrained"] is True
    assert res["tier_after"] == res["tier_before"]        # no upgrade while untrained


def test_manifest_m61_present():
    from pathlib import Path
    manifest = json.loads((Path(__file__).resolve().parents[2] / "papers" / "manifest.json")
                          .read_text(encoding="utf-8"))
    assert any(p["id"] == "M61" for p in manifest["papers"])
