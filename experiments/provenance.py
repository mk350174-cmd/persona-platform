"""
provenance — value-tier stamping for harness outputs.

Implements the numeric-value-status convention from
``docs/PM_Sistem_Promptu_v4.md``:

    Ölçülmüş   — real measured data (Holmes/Court/Kimera experiments)
    Tahmini    — estimated; experiment not yet run
    Hesaplanan — mathematically derived (non-experimental)

plus one harness-specific sub-tier:

    Simülasyon — a simulated run of the framework (the harness default)

Hard rule (``YAPMA LİSTESİ``): never present estimated/simulated values as
measured. This module makes that mechanical: ``stamp`` refuses to emit the
``Ölçülmüş`` tier, and a unit test asserts no result file ever carries it.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional

import persona_math
from persona_math.persona_library import PERSONA_LIBRARY

FRAMEWORK_VERSION: str = persona_math.__version__

# Single master seed (today's date) → fully reproducible runs.
MASTER_SEED: int = 20260607

# Keys every stamp() result is guaranteed to carry.
STAMP_KEYS = frozenset(
    {"value", "tier", "seed", "framework_version", "method", "library_n_personas", "note"}
)


class Tier(str, Enum):
    """Value-status tiers (str-valued so they serialize directly to JSON)."""

    OLCULMUS = "Ölçülmüş"      # real measured — NEVER emitted by this harness
    TAHMINI = "Tahmini"        # estimated; experiment not yet run
    HESAPLANAN = "Hesaplanan"  # mathematically derived (non-experimental)
    SIMULASYON = "Simülasyon"  # simulated run of the framework (default)


# Tiers the harness is permitted to emit.
ALLOWED_TIERS = frozenset({Tier.SIMULASYON, Tier.HESAPLANAN, Tier.TAHMINI})


def stamp(
    value: Any,
    *,
    tier: Tier = Tier.SIMULASYON,
    seed: int,
    method: str = "simulation",
    note: str = "",
) -> dict:
    """Wrap ``value`` with its provenance metadata.

    Raises
    ------
    ValueError
        If ``tier`` is ``Ölçülmüş``. The harness produces no real measurements,
        so labelling anything as measured would be a fabrication.
    """
    if tier == Tier.OLCULMUS:
        raise ValueError(
            "Harness must never emit the 'Ölçülmüş' (real-measurement) tier — "
            "simulated/calculated values cannot be labelled as measured."
        )
    return {
        "value": value,
        "tier": tier.value,
        "seed": int(seed),
        "framework_version": FRAMEWORK_VERSION,
        "method": method,
        "library_n_personas": len(PERSONA_LIBRARY),
        "note": note,
    }


def run_metadata(exp_id: str, seed: int, extra: Optional[dict] = None) -> dict:
    """One metadata block per ``results.json`` (the only place a timestamp lives,
    so result payloads stay byte-identical across runs)."""
    md = {
        "experiment": exp_id,
        "seed": int(seed),
        "master_seed": MASTER_SEED,
        "framework_version": FRAMEWORK_VERSION,
        "generated_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "library_n_personas": len(PERSONA_LIBRARY),
        "environment": "simulation — no real-LLM access (no API keys / no egress)",
        "integrity_note": (
            "All values are Simülasyon/Hesaplanan/Tahmini. No real-LLM "
            "measurement was performed; nothing here is 'Ölçülmüş'."
        ),
    }
    if extra:
        md.update(extra)
    return md


def exp_seed(m_number: int) -> int:
    """Deterministic per-experiment seed derived from the master seed."""
    return MASTER_SEED + int(m_number)
