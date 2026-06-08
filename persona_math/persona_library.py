"""
Persona Library — bulk registration engine.

Imports all category files and registers every persona spec into:
  - persona_math.compiler.PERSONA_CATALOG   (metadata + API)
  - persona_math.compiler._PERSONA_BLOCK_RULES (behavioral anchors)
  - api.catalog.PERSONA_VECTORS             (vector factories)
  - PERSONA_LIBRARY                         (local index)

Usage:
    from persona_math.persona_library import PERSONA_LIBRARY, get_library_persona
    specs = list(PERSONA_LIBRARY.values())          # all 500+ specs
    P = get_library_persona("aristotle")            # get vector
"""

from __future__ import annotations

import importlib
import logging
from typing import Optional

import numpy as np

from persona_math.persona_factory import make_persona_vector
from persona_math.compiler import PERSONA_CATALOG, _PERSONA_BLOCK_RULES

logger = logging.getLogger(__name__)

# ── Master index ───────────────────────────────────────────────────────────────
PERSONA_LIBRARY: dict[str, dict] = {}

# ── Default mandatory core if not specified ────────────────────────────────────
_DEFAULT_CORE = {0: 0.72, 1: 0.70, 3: 0.68, 11: 0.65}


def _build_factory(spec: dict):
    """Return a closure that builds the persona vector deterministically."""
    def _factory(s=spec):
        block_input = {}
        for b_num, val in s["blocks"].items():
            b_num = int(b_num)
            if isinstance(val, (int, float)):
                block_input[b_num] = {"base": float(val), "variance": 0.035}
            else:
                block_input[b_num] = val

        core = s.get("mandatory_core", _DEFAULT_CORE)
        # ensure all four mandatory indices present
        merged_core = dict(_DEFAULT_CORE)
        merged_core.update({int(k): float(v) for k, v in core.items()})

        return make_persona_vector({
            "seed": s.get("seed", abs(hash(s["id"])) % (2 ** 31)),
            "base": s.get("base_activation", 0.50),
            "blocks": block_input,
            "mandatory_core": merged_core,
        })

    return _factory


def register_persona(spec: dict) -> None:
    """Register one persona spec into all subsystems."""
    pid = spec["id"]

    if pid in PERSONA_LIBRARY:
        return  # already registered (catalog.py pre-registered personas)

    # ── Catalog metadata ───────────────────────────────────────────────────────
    PERSONA_CATALOG[pid] = {
        "name":              spec["name"],
        "label":             spec.get("label", ""),
        "era":               spec.get("era", ""),
        "tagline":           spec.get("tagline", ""),
        "style":             spec.get("style", ""),
        "voice":             spec.get("voice", ""),
        "incompatibilities": spec.get("incompatibilities", ""),
        "price_usd":         float(spec.get("price_usd", 19.99)),
        "ceid_certified":    True,
        "domain":            spec.get("domain", "General"),
        "tags":              spec.get("tags", []),
    }

    # ── Block rules ────────────────────────────────────────────────────────────
    if "block_rules" in spec:
        _PERSONA_BLOCK_RULES[pid] = {
            int(k): v for k, v in spec["block_rules"].items()
        }

    # ── Vector factory ─────────────────────────────────────────────────────────
    try:
        from api.catalog import PERSONA_VECTORS
        if pid not in PERSONA_VECTORS:
            PERSONA_VECTORS[pid] = _build_factory(spec)
    except ImportError:
        pass  # headless / test environment

    PERSONA_LIBRARY[pid] = spec


def _load_category(module_path: str) -> list[dict]:
    """Import a category module and return its PERSONAS list."""
    try:
        mod = importlib.import_module(module_path)
        personas = getattr(mod, "PERSONAS", [])
        logger.debug("Loaded %d personas from %s", len(personas), module_path)
        return personas
    except Exception as exc:
        logger.warning("Failed to load %s: %s", module_path, exc)
        return []


# ── Category modules ───────────────────────────────────────────────────────────
_CATEGORY_MODULES = [
    "persona_math.personas.ancient",
    "persona_math.personas.medieval_modern",
    "persona_math.personas.scientists_artists",
    "persona_math.personas.fictional",
    "persona_math.personas.mythological_archetypes",
    "persona_math.personas.leaders_warriors",
]


def load_all_personas() -> int:
    """Load and register all category files. Returns total count."""
    total = 0
    for module_path in _CATEGORY_MODULES:
        specs = _load_category(module_path)
        for spec in specs:
            try:
                register_persona(spec)
                total += 1
            except Exception as exc:
                logger.warning("Skipped %s: %s", spec.get("id", "?"), exc)
    return total


def get_library_persona(persona_id: str) -> np.ndarray:
    """Return the HPEP-100 vector for a library persona."""
    spec = PERSONA_LIBRARY.get(persona_id)
    if spec is None:
        raise KeyError(f"Persona '{persona_id}' not in library. "
                       f"Call load_all_personas() first or check the ID.")
    return _build_factory(spec)()


def search_personas(
    query: str = "",
    domain: Optional[str] = None,
    tags: Optional[list] = None,
    min_price: float = 0,
    max_price: float = 999,
) -> list[dict]:
    """
    Search all personas — library + original PERSONA_CATALOG entries.

    Parameters
    ----------
    query    : substring match against id, name, label, tagline
    domain   : exact domain filter (Philosophy, Science, Fiction, ...)
    tags     : list of required tags (all must match)
    min/max_price : price range filter

    Returns
    -------
    List of catalog-style dicts with id + metadata.
    """
    # Build unified source: PERSONA_LIBRARY spec dicts + PERSONA_CATALOG-only entries
    unified: dict[str, dict] = {}

    # 1. All library specs
    for pid, spec in PERSONA_LIBRARY.items():
        unified[pid] = spec

    # 2. PERSONA_CATALOG entries not already in library
    for pid, meta in PERSONA_CATALOG.items():
        if pid not in unified:
            unified[pid] = {
                "id":              pid,
                "name":            meta.get("name", pid),
                "label":           meta.get("label", ""),
                "era":             meta.get("era", ""),
                "tagline":         meta.get("tagline", ""),
                "domain":          meta.get("domain", "Philosophy"),
                "tags":            meta.get("tags", []),
                "price_usd":       meta.get("price_usd", 19.99),
                "style":           meta.get("style", ""),
                "voice":           meta.get("voice", ""),
                "incompatibilities": meta.get("incompatibilities", ""),
            }

    results = []
    q = query.lower()

    for pid, spec in unified.items():
        price = float(spec.get("price_usd", 19.99))
        if not (min_price <= price <= max_price):
            continue
        if domain and spec.get("domain", "").lower() != domain.lower():
            continue
        if tags:
            spec_tags = [t.lower() for t in spec.get("tags", [])]
            if not all(t.lower() in spec_tags for t in tags):
                continue
        if q:
            haystack = " ".join([
                pid,
                spec.get("name", ""),
                spec.get("label", ""),
                spec.get("tagline", ""),
                " ".join(spec.get("tags", [])),
            ]).lower()
            if q not in haystack:
                continue

        results.append({
            "id":        pid,
            "name":      spec.get("name", pid),
            "label":     spec.get("label", ""),
            "era":       spec.get("era", ""),
            "tagline":   spec.get("tagline", ""),
            "domain":    spec.get("domain", ""),
            "tags":      spec.get("tags", []),
            "price_usd": price,
        })

    return sorted(results, key=lambda x: x["name"])


def library_stats() -> dict:
    """Return summary statistics of the loaded library."""
    domains: dict[str, int] = {}
    price_total = 0.0
    for spec in PERSONA_LIBRARY.values():
        d = spec.get("domain", "Unknown")
        domains[d] = domains.get(d, 0) + 1
        price_total += float(spec.get("price_usd", 19.99))

    return {
        "total_personas":  len(PERSONA_LIBRARY),
        "domains":         dict(sorted(domains.items(), key=lambda x: -x[1])),
        "avg_price":       round(price_total / max(len(PERSONA_LIBRARY), 1), 2),
        "categories_loaded": len(_CATEGORY_MODULES),
    }


# ── Auto-load at import time ───────────────────────────────────────────────────
_n = load_all_personas()
logger.info("Persona library loaded: %d personas", _n)
