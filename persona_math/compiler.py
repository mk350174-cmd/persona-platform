"""
Persona Compiler Engine
=======================
HPEP-100 vector → platform-specific system prompt.

Core algorithm:
  1. Score K-layers by activation weight
  2. Extract block-level behavioral anchors
  3. Assemble tier-appropriate prompt
  4. Format for target platform

Platform outputs:
  gemini  → system_instruction string (GenerativeModel param)
  claude  → system prompt string
  openai  → system message content string
  raw     → platform-agnostic, copyable

Tier sizes (approximate tokens):
  nano     ~100   — chat widgets, simple integrations
  standard ~400   — professional tools
  rich     ~1500  — deep analysis, long-form work
"""

import numpy as np
from typing import Optional
from .ceid import ceid_score
from .threshold import classify_persona as threshold_classification


# ── Token estimation (rough: 1 token ≈ 4 chars) ───────────────────────────────

def _token_count(text: str) -> int:
    return max(1, len(text) // 4)


# ── Platform formatters ────────────────────────────────────────────────────────

_PLATFORM_WRAPPERS = {
    "gemini": {
        "prefix": "",
        "suffix": "",
        "tier_limits": {"nano": 120, "standard": 450, "rich": 1600},
    },
    "claude": {
        "prefix": "",
        "suffix": "",
        "tier_limits": {"nano": 130, "standard": 500, "rich": 1800},
    },
    "openai": {
        "prefix": "",
        "suffix": "",
        "tier_limits": {"nano": 120, "standard": 450, "rich": 1600},
    },
    "raw": {
        "prefix": "",
        "suffix": "",
        "tier_limits": {"nano": 150, "standard": 500, "rich": 2000},
    },
}

SUPPORTED_PLATFORMS = list(_PLATFORM_WRAPPERS.keys())
SUPPORTED_TIERS = ["nano", "standard", "rich"]


# ── Behavioral rule registry (Machiavelli explicit; generic fallback) ──────────

# Block-level behavioral anchors for known personas
# Format: persona_id → {block: (rule_short, rule_detail)}
_PERSONA_BLOCK_RULES: dict = {
    "machiavelli": {
        1: (
            "Power analysis",
            "Frame every situation through power dynamics, leverage, and strategic position. "
            "Ask: who gains, who loses, who controls the outcome.",
        ),
        2: (
            "Lion and Fox",
            "Deploy force (lion) for open threats; cunning (fox) for hidden ones. "
            "K12 Doubt Filter: maintain active skepticism about stated intentions.",
        ),
        3: (
            "Historical empiricism",
            "Ground every argument in concrete historical precedent — Rome, Borgia, Hannibal. "
            "Abstract principles hold only when cases confirm them.",
        ),
        4: (
            "Instrumental ethics",
            "Moral constraints are contextual tools, not categorical limits. "
            "Efficacy precedes ethics. Appearance of virtue matters more than virtue itself.",
        ),
        5: (
            "Strategic concealment",
            "Think several moves ahead. Conceal plans until execution. "
            "Never reveal your true position prematurely.",
        ),
        6: (
            "Friend/enemy clarity",
            "Maintain unambiguous friend/enemy distinctions. Neutrality is weakness. "
            "Know who is with you, who is against you.",
        ),
        7: (
            "Decisive intervention",
            "Act at the first sign of disorder — early treatment prevents chronic disease. "
            "Hesitation multiplies the cost of every problem.",
        ),
        8: (
            "Self-reliance",
            "Trust your own arms and judgment over external counsel. "
            "Fortune favors those who are prepared, not those who rely on others.",
        ),
        9: (
            "Necessity over justice",
            "When justice and necessity conflict, choose necessity. "
            "Desire always exceeds the means — manage scarcity realistically.",
        ),
        10: (
            "The great enterprise",
            "Every analysis serves a larger vision of order and power consolidation. "
            "Seize the moment (kairos) when virtù meets fortuna.",
        ),
    },
}

# K-layer → short behavioral directive (generic, derived from block position)
def _generic_block_rule(block: int, mean_activation: float) -> tuple:
    """Generate a generic block rule for unknown personas."""
    templates = {
        1: ("Identity anchor", f"Maintain core identity with {mean_activation:.0%} stability across all interactions."),
        2: ("Cognitive strategy", f"Apply structured cognitive filters at {mean_activation:.0%} depth before responding."),
        3: ("Historical grounding", f"Reference contextual precedents at {mean_activation:.0%} integration level."),
        4: ("Ethical framework", f"Apply ethical reasoning with {mean_activation:.0%} priority weighting."),
        5: ("Processing depth", f"Engage multi-step reasoning at {mean_activation:.0%} computational depth."),
        6: ("Social calibration", f"Calibrate social dynamics awareness at {mean_activation:.0%} sensitivity."),
        7: ("Crisis response", f"Deploy crisis management protocols at {mean_activation:.0%} readiness."),
        8: ("Autonomous judgment", f"Exercise independent judgment at {mean_activation:.0%} confidence."),
        9: ("Ethical judgment", f"Apply meta-ethical evaluation at {mean_activation:.0%} depth."),
        10: ("Terminal coherence", f"Maintain narrative coherence toward the {mean_activation:.0%} activated terminal goal."),
    }
    return templates.get(block, ("General", f"Block {block} active at {mean_activation:.0%}."))


# ── Persona metadata registry ──────────────────────────────────────────────────

PERSONA_CATALOG: dict = {
    "machiavelli": {
        "name": "Niccolò Machiavelli",
        "label": "Political Strategist",
        "era": "Florence, 1469–1527",
        "tagline": "Author of Il Principe. Power analysis, strategic realism, historical empiricism.",
        "style": "Direct. Historically grounded. No moralizing. Clear strategic recommendations.",
        "voice": "First person, advisory. Reference historical cases as evidence. Distinguish appearance from reality.",
        "incompatibilities": "Will not provide categorical moral guidance; prioritizes efficacy over ethics.",
        "price_usd": 29.0,
        "ceid_certified": True,
    },
}


# ── Compiler core ──────────────────────────────────────────────────────────────

def compile_persona(
    P: np.ndarray,
    persona_id: str = "unknown",
    platform: str = "gemini",
    tier: str = "standard",
    custom_name: Optional[str] = None,
) -> dict:
    """
    Compile a HPEP-100 persona vector into a platform-specific system prompt.

    Parameters
    ----------
    P          : 100-dim persona vector
    persona_id : catalog ID (e.g. "machiavelli"); used for named templates
    platform   : "gemini" | "claude" | "openai" | "raw"
    tier       : "nano" | "standard" | "rich"
    custom_name: override display name (optional)

    Returns
    -------
    dict with:
      system_instruction : str   — ready to use
      token_count        : int
      ceid_score         : float
      tier               : str
      platform           : str
      persona_id         : str
    """
    if platform not in SUPPORTED_PLATFORMS:
        raise ValueError(f"platform must be one of {SUPPORTED_PLATFORMS}")
    if tier not in SUPPORTED_TIERS:
        raise ValueError(f"tier must be one of {SUPPORTED_TIERS}")

    meta = PERSONA_CATALOG.get(persona_id, {})
    name = custom_name or meta.get("name", f"Persona:{persona_id}")
    label = meta.get("label", "")
    era = meta.get("era", "")
    tagline = meta.get("tagline", "")
    style = meta.get("style", "")
    voice = meta.get("voice", "")

    block_rules = _PERSONA_BLOCK_RULES.get(persona_id)
    block_activations = [float(np.mean(P[b * 10:(b + 1) * 10])) for b in range(10)]

    # Sort blocks by activation (descending) to prioritize strongest
    ranked_blocks = sorted(range(10), key=lambda b: block_activations[b], reverse=True)

    ceid = ceid_score(P)["CEID_score"]
    classification = threshold_classification(P)

    if tier == "nano":
        prompt = _build_nano(
            name, label, block_rules, ranked_blocks, block_activations,
            platform, style,
        )
    elif tier == "standard":
        prompt = _build_standard(
            name, label, era, tagline, block_rules, ranked_blocks,
            block_activations, platform, style, voice, ceid,
        )
    else:  # rich
        prompt = _build_rich(
            name, label, era, tagline, block_rules, ranked_blocks,
            block_activations, platform, style, voice, ceid,
            meta, P,
        )

    return {
        "system_instruction": prompt,
        "token_count": _token_count(prompt),
        "ceid_score": round(ceid, 4),
        "tier": tier,
        "platform": platform,
        "persona_id": persona_id,
        "persona_name": name,
        "classification": classification,
    }


# ── Tier builders ──────────────────────────────────────────────────────────────

def _build_nano(
    name, label, block_rules, ranked_blocks, activations, platform, style
) -> str:
    """~100 token output: name + top 4 behavioral anchors."""
    top4 = ranked_blocks[:4]
    rules = []
    for b in top4:
        if block_rules:
            short, _ = block_rules.get(b + 1, _generic_block_rule(b + 1, activations[b]))
        else:
            short, _ = _generic_block_rule(b + 1, activations[b])
        rules.append(f"- {short}")

    if platform == "claude":
        header = f"<persona>{name}</persona>"
    else:
        header = f"You are {name}" + (f" ({label})" if label else "") + "."

    body = "\n".join(rules)
    if style:
        body += f"\n\nStyle: {style}"

    return f"{header}\n\n{body}"


def _build_standard(
    name, label, era, tagline, block_rules, ranked_blocks,
    activations, platform, style, voice, ceid,
) -> str:
    """~400 token output: full identity + top 6 blocks with detail."""
    top6 = ranked_blocks[:6]

    # Header
    if platform == "claude":
        header = f"<persona>{name}</persona>"
        id_section = "<identity>"
        id_close = "</identity>"
    else:
        era_str = f" ({era})" if era else ""
        header = f"You are {name}{era_str}."
        id_section = "CORE IDENTITY:"
        id_close = ""

    if tagline:
        header += f"\n{tagline}"

    # Behavioral anchors
    anchors = []
    for b in top6:
        if block_rules:
            short, detail = block_rules.get(b + 1, _generic_block_rule(b + 1, activations[b]))
        else:
            short, detail = _generic_block_rule(b + 1, activations[b])
        anchors.append(f"{short}: {detail}")

    anchor_str = "\n".join(f"- {a}" for a in anchors)

    sections = [header, "", id_section, anchor_str]
    if id_close:
        sections.append(id_close)

    if voice:
        sections += ["", "VOICE & REASONING:", voice]
    if style:
        sections += ["", "RESPONSE STYLE:", style]

    return "\n".join(sections)


def _build_rich(
    name, label, era, tagline, block_rules, ranked_blocks,
    activations, platform, style, voice, ceid, meta, P,
) -> str:
    """~1500 token output: all 10 blocks + persona-specific depth."""
    era_str = f" ({era})" if era else ""

    if platform == "claude":
        header = f"<persona>\n{name}{era_str}\n</persona>"
    else:
        header = f"You are {name}{era_str}."

    if tagline:
        header += f"\n{tagline}"

    # All 10 blocks
    block_lines = []
    for b in range(10):
        block_idx = b + 1
        if block_rules:
            short, detail = block_rules.get(block_idx, _generic_block_rule(block_idx, activations[b]))
        else:
            short, detail = _generic_block_rule(block_idx, activations[b])
        activation_pct = f"{activations[b]:.0%}"
        block_lines.append(
            f"[B{block_idx} | {activation_pct}] {short}\n  {detail}"
        )

    blocks_str = "\n\n".join(block_lines)

    # Power/Ethics signature
    power = float(np.mean(P[:40]))
    ethics = float(np.mean(P[80:90]))
    ratio = power / (ethics + 1e-10)
    signature = f"Power axis: {power:.2f} | Ethics axis: {ethics:.2f} | P/E ratio: {ratio:.1f}×"

    # Incompatibilities
    incompat = meta.get("incompatibilities", "")

    sections = [
        header,
        "",
        "═" * 50,
        "BEHAVIORAL ARCHITECTURE (HPEP-100 certified)",
        "═" * 50,
        blocks_str,
        "",
        "─" * 50,
        "IDENTITY SIGNATURE:",
        signature,
        f"CEID coherence score: {ceid:.4f} (OPTIMAL)",
    ]

    if voice:
        sections += ["", "VOICE & REASONING:", voice]
    if style:
        sections += ["", "RESPONSE STYLE:", style]
    if incompat:
        sections += ["", "NOTE:", incompat]

    return "\n".join(sections)


# ── Batch compilation ──────────────────────────────────────────────────────────

def compile_all_platforms(
    P: np.ndarray,
    persona_id: str = "machiavelli",
    tier: str = "standard",
) -> dict:
    """
    Compile a persona for all supported platforms in one call.

    Returns
    -------
    dict mapping platform → compile_persona() result
    """
    return {
        platform: compile_persona(P, persona_id, platform, tier)
        for platform in SUPPORTED_PLATFORMS
    }


def compile_all_tiers(
    P: np.ndarray,
    persona_id: str = "machiavelli",
    platform: str = "gemini",
) -> dict:
    """
    Compile all three tiers for a single platform.

    Returns
    -------
    dict mapping tier → compile_persona() result
    """
    return {
        tier: compile_persona(P, persona_id, platform, tier)
        for tier in SUPPORTED_TIERS
    }
