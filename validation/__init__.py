"""
validation — academic validation pipeline for the Persona series.

Re-measures the M1–M60 simulation results with PersonaNeedle and upgrades their tier to
``Measured`` once a trained model exists. Torch-free to import; with an untrained model it
runs the ``persona_math`` fallback and performs no Measured upgrade (honest tiers).
"""

from .validator import AcademicValidator
from .paper_probe import PaperProbe
from .tier_updater import TierUpdater, TIER_HIERARCHY
from .report_generator import ValidationReportGenerator

__all__ = ["AcademicValidator", "PaperProbe", "TierUpdater", "TIER_HIERARCHY",
           "ValidationReportGenerator"]
