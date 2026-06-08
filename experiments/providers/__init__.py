"""
providers — swappable data sources for the experiment harness.

``SimulatedProvider`` (default) synthesizes persona-conditioned vector series
from the existing persona library, deterministically. ``LLMProvider`` is the
documented plug-in point for real-LLM runs (not executed in this environment).

Every ``exp_m*`` module takes a ``SeriesProvider`` argument, so switching from
simulated to real data changes the source without touching experiment logic.
"""

from .base import SeriesProvider, ResponseSeries
from .simulated import SimulatedProvider
from .llm_stub import LLMProvider

__all__ = ["SeriesProvider", "ResponseSeries", "SimulatedProvider", "LLMProvider"]
