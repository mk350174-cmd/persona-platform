"""
TierUpdater — manage value-tier upgrades for the M1–M61 series.

Tiers form a strict hierarchy (weakest → strongest):

    Estimated  <  Simulated  <  Computed  <  Measured

mapped to the repo's Turkish ``provenance.Tier`` (Tahmini / Simülasyon / Hesaplanan /
Ölçülmüş). Upgrades are **monotonic** (never downgrade) and ``Measured`` is reachable
**only with real measured evidence** (``evidence["untrained"] is False`` — a trained
PersonaNeedle). With an untrained model the validation pipeline produces the persona_math
fallback, so nothing is upgraded to Measured — consistent with the series' integrity rule
that simulated values are never presented as ``Ölçülmüş``.

The source of truth for upgrades is ``validation/tiers.json``; the generated
``papers/manifest.json`` is patched in place only on a real upgrade (a no-op until a model
is trained), so this never fights ``experiments/build_manifest.py``.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

TIER_HIERARCHY = ["Estimated", "Simulated", "Computed", "Measured"]

# English tier ↔ Turkish provenance.Tier values
EN_TO_TR = {"Estimated": "Tahmini", "Simulated": "Simülasyon",
            "Computed": "Hesaplanan", "Measured": "Ölçülmüş"}
TR_TO_EN = {v: k for k, v in EN_TO_TR.items()}

_REPO = Path(__file__).resolve().parent.parent


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _rank(tier: str) -> int:
    return TIER_HIERARCHY.index(tier) if tier in TIER_HIERARCHY else -1


class TierUpdater:
    def __init__(self, manifest_path: str | Path = None, tiers_path: str | Path = None):
        self.manifest_path = Path(manifest_path) if manifest_path else _REPO / "papers" / "manifest.json"
        self.tiers_path = Path(tiers_path) if tiers_path else _REPO / "validation" / "tiers.json"
        self.tiers: dict = (json.loads(self.tiers_path.read_text(encoding="utf-8"))
                            if self.tiers_path.exists() else {})

    # ── per-paper tier ────────────────────────────────────────────────────────────
    def _manifest_papers(self) -> list[dict]:
        if not self.manifest_path.exists():
            return []
        return json.loads(self.manifest_path.read_text(encoding="utf-8")).get("papers", [])

    @staticmethod
    def _tier_from_value_tiers(value_tiers: list[str]) -> str:
        """Highest English tier present in a manifest entry's value_tiers_present."""
        ens = [TR_TO_EN.get(t) for t in (value_tiers or []) if t in TR_TO_EN]
        return max(ens, key=_rank) if ens else "Simulated"

    def current_tier(self, paper_id: str) -> str:
        if paper_id in self.tiers:
            return self.tiers[paper_id]["tier"]
        for p in self._manifest_papers():
            if p["id"] == paper_id:
                return self._tier_from_value_tiers(p.get("value_tiers_present"))
        return "Simulated"

    # ── upgrade (monotonic; Measured needs a trained model) ───────────────────────
    def upgrade_tier(self, paper_id: str, new_tier: str, evidence: dict) -> bool:
        if new_tier not in TIER_HIERARCHY:
            raise ValueError(f"unknown tier {new_tier!r}; expected one of {TIER_HIERARCHY}")
        if _rank(new_tier) <= _rank(self.current_tier(paper_id)):
            return False                                   # never downgrade / no-op
        if new_tier == "Measured" and evidence.get("untrained", True):
            return False                                   # no Measured without a trained model
        self.tiers[paper_id] = {"tier": new_tier, "evidence": evidence, "updated_at": _now()}
        self._save()
        if new_tier == "Measured":
            self._patch_manifest(paper_id, new_tier)
        return True

    def _save(self) -> None:
        self.tiers_path.parent.mkdir(parents=True, exist_ok=True)
        self.tiers_path.write_text(json.dumps(self.tiers, ensure_ascii=False, indent=2),
                                   encoding="utf-8")

    def _patch_manifest(self, paper_id: str, new_tier: str) -> None:
        """Record a real Measured upgrade in manifest.json (only called on a real upgrade)."""
        if not self.manifest_path.exists():
            return
        data = json.loads(self.manifest_path.read_text(encoding="utf-8"))
        for p in data.get("papers", []):
            if p["id"] == paper_id:
                p["tier"] = new_tier
                p["measured_at"] = self.tiers[paper_id]["updated_at"]
        self.manifest_path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n",
                                      encoding="utf-8")

    # ── report ────────────────────────────────────────────────────────────────────
    def generate_tier_report(self) -> dict:
        """Per-paper highest-tier histogram, before vs after applying validation upgrades."""
        before = {t: 0 for t in TIER_HIERARCHY}
        after = {t: 0 for t in TIER_HIERARCHY}
        for p in self._manifest_papers():
            base = self._tier_from_value_tiers(p.get("value_tiers_present"))
            before[base] += 1
            upgraded = self.tiers.get(p["id"], {}).get("tier", base)
            after[max(base, upgraded, key=_rank)] += 1
        return {"before": before, "after": after,
                "measured_after": after["Measured"], "upgrades": len(self.tiers)}
