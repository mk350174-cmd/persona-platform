"""
Persona catalog — loads the 11 product-facing personas from ``agents/*.md``
(YAML frontmatter + AI Simulation Disclosure + HPEP-100 profile) and maps
each to its underlying K-layer library key in ``persona_math.persona_library``.

**Real finding (T2-013, 2026-07-30):** the product-facing persona IDs
(``agents/*.md`` filenames, e.g. ``mandela``) do NOT match the 495-persona
K-layer library's keys (e.g. ``nelson_mandela``) for 7 of 11 personas, and
**``machiavelli`` does not exist in the K-layer library under any name** —
confirmed by exhaustive substring search, not just exact-match lookup. This
module makes that explicit via ``k_layer_key`` (``None`` when absent) rather
than silently failing or guessing. Endpoints must check ``k_layer_available``
before calling CEID/drift tools for a persona.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import yaml

_AGENTS_DIR = Path(__file__).resolve().parent.parent / "agents"

# agents/*.md id -> persona_math.persona_library key (None = confirmed absent,
# not merely unmapped; see module docstring).
K_LAYER_KEY_MAP: dict[str, str | None] = {
    "mandela": "nelson_mandela",
    "einstein": "albert_einstein",
    "machiavelli": None,  # confirmed absent from the 495-persona library
    "marie-curie": "marie_curie",
    "napoleon": "napoleon_bonaparte",
    "nietzsche": "friedrich_nietzsche_classic",
    "sherlock-holmes": "sherlock_holmes_char",
    "socrates": "socrates",
    "sun-tzu": "sun_wu",
    "tesla": "nikola_tesla",
    "athena": "athena",
}

_HISTORICAL_DISCLOSURE_MARKER = "documented voice, values, and"
_FICTIONAL_DISCLOSURE_MARKER = "drawn from\nmyth/fiction"


@dataclass(frozen=True)
class PersonaCatalogEntry:
    persona_id: str
    name: str
    description: str
    model: str
    is_historical: bool  # False = mythological/fictional (lighter disclosure)
    has_disclosure: bool
    k_layer_key: str | None
    k_layer_available: bool
    hpep100_blocks: dict[str, str]
    file: str


def _parse_frontmatter(text: str) -> tuple[dict, str]:
    parts = text.split("---", 2)
    if len(parts) < 3:
        return {}, text
    meta = yaml.safe_load(parts[1]) or {}
    body = parts[2]
    return meta, body


def _extract_hpep100_blocks(body: str) -> dict[str, str]:
    blocks = {}
    for m in re.finditer(r"\*\*(Block \d+ \([^)]+\))\*\*\s*([\d.]+)\s*—\s*(.+)", body):
        blocks[m.group(1)] = f"{m.group(2)} — {m.group(3).strip()}"
    return blocks


def _load_entry(path: Path) -> PersonaCatalogEntry:
    text = path.read_text(encoding="utf-8")
    meta, body = _parse_frontmatter(text)
    persona_id = meta.get("name", path.stem)
    has_disclosure = "AI Simulation Disclosure" in body
    is_historical = _FICTIONAL_DISCLOSURE_MARKER not in body.replace(" ", " ")
    k_key = K_LAYER_KEY_MAP.get(persona_id)
    return PersonaCatalogEntry(
        persona_id=persona_id,
        name=meta.get("name", path.stem),
        description=meta.get("description", ""),
        model=meta.get("model", "unknown"),
        is_historical=is_historical,
        has_disclosure=has_disclosure,
        k_layer_key=k_key,
        k_layer_available=k_key is not None,
        hpep100_blocks=_extract_hpep100_blocks(body),
        file=path.name,
    )


def load_catalog() -> dict[str, PersonaCatalogEntry]:
    """Load all agents/*.md into a persona_id -> PersonaCatalogEntry map."""
    catalog = {}
    for path in sorted(_AGENTS_DIR.glob("*.md")):
        entry = _load_entry(path)
        catalog[entry.persona_id] = entry
    return catalog


CATALOG: dict[str, PersonaCatalogEntry] = load_catalog()
