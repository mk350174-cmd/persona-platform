"""Minimal feature-flag system (T2-031). Env-var backed, default-off — no
external flag service (LaunchDarkly/GrowthBook/etc.) is wired up; that
would need a real account, a business decision left to the user."""
from __future__ import annotations

import os

_TRUE_VALUES = {"1", "true", "yes", "on"}


def is_enabled(flag_name: str) -> bool:
    """`FEATURE_<FLAG_NAME_UPPER>=1` (or true/yes/on) enables a flag."""
    env_var = f"FEATURE_{flag_name.upper()}"
    return os.environ.get(env_var, "").strip().lower() in _TRUE_VALUES
