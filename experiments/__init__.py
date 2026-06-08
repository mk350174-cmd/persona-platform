"""
experiments — Reproducible computational-validation harness for the
Persona Engineering Research Series (M1–M10).

This package runs the *existing* persona_math / integrations framework on the
*existing* persona library (≈500 specs) to produce real, reproducible numbers
for the M1–M10 papers. It is built around a swappable data source
(``providers.SeriesProvider``) so that a real-LLM backend can be plugged in
later without touching any experiment logic.

INTEGRITY: every number produced here is stamped with a value tier
(``provenance.Tier``). The harness emits only ``Simülasyon`` / ``Hesaplanan`` /
``Tahmini`` tiers and NEVER ``Ölçülmüş`` (real measured) — see
``docs/PM_Sistem_Promptu_v4.md``. Simulated numbers must never be presented as
real LLM measurements.
"""

from .provenance import Tier, stamp, run_metadata, exp_seed, MASTER_SEED, FRAMEWORK_VERSION

__all__ = [
    "Tier",
    "stamp",
    "run_metadata",
    "exp_seed",
    "MASTER_SEED",
    "FRAMEWORK_VERSION",
]
