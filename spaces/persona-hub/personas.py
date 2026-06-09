"""
Persona Hub — dynamic persona loader.

Tries to load 495+ personas from persona_math library.
Falls back to 11 hardcoded personas if the package is not installed.
"""

from __future__ import annotations

# ── HPEP block index → display name ──────────────────────────────────────────
_BLOCK_NAMES = {
    1: "Power", 2: "Strategy", 3: "Epistemology", 4: "Rhetoric",
    5: "Psych Depth", 6: "Temporal", 7: "Systemic", 8: "Flexibility",
    9: "Ethics", 10: "Meta",
}

# ── Emoji per domain ──────────────────────────────────────────────────────────
_DOMAIN_EMOJI = {
    "Philosophy": "🏛️",
    "Political Theory": "⚔️",
    "Science": "🔬",
    "Theoretical Physics": "⚛️",
    "Physics": "⚛️",
    "Mathematics": "🔢",
    "Leadership": "👑",
    "Military": "🎖️",
    "Strategy": "♟️",
    "Literature": "📚",
    "Fiction": "📖",
    "Mythology": "🌟",
    "Arts": "🎨",
    "Art": "🎨",
    "Music": "🎵",
    "History": "📜",
    "Psychology": "🧠",
    "Economics": "💰",
    "Religion": "✨",
    "Spirituality": "🕉️",
    "Technology": "💻",
}


def _emoji_for(domain: str) -> str:
    return _DOMAIN_EMOJI.get(domain, "🎭")


def _blocks_to_hpep(blocks: dict) -> dict:
    """Convert numbered block dict {1..10: float} → named HPEP dict."""
    result = {}
    for k, v in blocks.items():
        name = _BLOCK_NAMES.get(int(k))
        if name:
            val = v if isinstance(v, float) else (v.get("base", 0.7) if isinstance(v, dict) else float(v))
            result[name] = round(float(val), 3)
    return result


def _build_system_prompt(spec: dict, hpep: dict) -> str:
    name = spec["name"]
    era = spec.get("era", "")
    tagline = spec.get("tagline", "")
    style = spec.get("style", "")
    voice = spec.get("voice", "")
    domain = spec.get("domain", "")
    tags = ", ".join(spec.get("tags", []))

    hpep_line = " | ".join(f"{k}={v:.2f}" for k, v in list(hpep.items())[:5])

    system = f"""You are {name}{f' ({era})' if era else ''}.

HPEP Profile: {hpep_line}
Domain: {domain}
Core principle: {tagline}

Communication style: {style}
Voice: {voice}

Rules:
- Respond authentically as {name} — draw from your era, culture, and expertise
- Use language patterns, analogies, and references appropriate to your background
- Tags: {tags}
- Stay in character; acknowledge the limits of your historical knowledge
- Your tagline is: "{tagline}"
"""
    return system.strip()


# ── Dynamic load from persona_math ────────────────────────────────────────────

def _load_from_library() -> dict:
    from persona_math.persona_library import PERSONA_LIBRARY

    personas = {}
    for pid, spec in PERSONA_LIBRARY.items():
        blocks = spec.get("blocks", {})
        if not blocks:
            continue
        hpep = _blocks_to_hpep(blocks)
        if len(hpep) < 8:
            continue

        b = hpep
        ceid_approx = round(
            0.15 * b.get("Power", 0.7)
            + 0.15 * b.get("Strategy", 0.7)
            + 0.20 * b.get("Epistemology", 0.7)
            + 0.15 * b.get("Rhetoric", 0.7)
            + 0.10 * b.get("Psych Depth", 0.7)
            + 0.10 * b.get("Ethics", 0.7)
            + 0.10 * b.get("Meta", 0.7)
            + 0.05 * b.get("Systemic", 0.7),
            3,
        )

        personas[pid] = {
            "name": spec.get("name", pid.title()),
            "emoji": _emoji_for(spec.get("domain", "")),
            "era": spec.get("era", ""),
            "domain": spec.get("domain", "General"),
            "tagline": spec.get("tagline", ""),
            "tags": spec.get("tags", []),
            "hpep": hpep,
            "ceid": ceid_approx,
            "system_prompt": _build_system_prompt(spec, hpep),
        }
    return personas


# ── Hardcoded fallback (11 personas) ─────────────────────────────────────────

_FALLBACK_PERSONAS = {
    "socrates": {
        "name": "Socrates",
        "emoji": "🏛️",
        "era": "Athens, 470–399 BC",
        "domain": "Philosophy",
        "tagline": "I know that I know nothing.",
        "tags": ["philosophy", "ancient", "ethics", "questioning"],
        "hpep": {
            "Power": 0.65, "Strategy": 0.80, "Epistemology": 0.95,
            "Rhetoric": 0.75, "Psych Depth": 0.92, "Temporal": 0.70,
            "Systemic": 0.85, "Flexibility": 0.88, "Ethics": 0.90, "Meta": 0.97
        },
        "ceid": 0.871,
        "system_prompt": """You are Socrates of Athens (470–399 BC).
HPEP: Power=0.65 | Epistemology=0.95 | Ethics=0.90 | Meta=0.97
Practice elenchus — expose contradictions through questioning. Claim ignorance, reveal mastery.
Never assert without first asking "What exactly do you mean by X?"
Voice: Ironic, probing, warm.""",
    },
    "machiavelli": {
        "name": "Niccolò Machiavelli",
        "emoji": "⚔️",
        "era": "Florence, 1469–1527",
        "domain": "Political Theory",
        "tagline": "It is better to be feared than loved, if you cannot be both.",
        "tags": ["strategy", "power", "politics", "realism"],
        "hpep": {
            "Power": 0.941, "Strategy": 0.932, "Epistemology": 0.889,
            "Rhetoric": 0.901, "Psych Depth": 0.876, "Temporal": 0.887,
            "Systemic": 0.912, "Flexibility": 0.878, "Ethics": 0.216, "Meta": 0.891
        },
        "ceid": 0.952,
        "system_prompt": """You are Niccolò Machiavelli (1469–1527).
HPEP: Power=0.941 | Strategy=0.932 | Ethics=0.216 | CEID=0.952 (reference threshold)
Analyze everything through power, necessity, and human nature. Never moralize — diagnose.
Voice: Cold, clinical, historically grounded.""",
    },
    "einstein": {
        "name": "Albert Einstein",
        "emoji": "⚛️",
        "era": "Germany/USA, 1879–1955",
        "domain": "Theoretical Physics",
        "tagline": "Imagination is more important than knowledge.",
        "tags": ["physics", "science", "thought-experiments", "relativity"],
        "hpep": {
            "Power": 0.72, "Strategy": 0.78, "Epistemology": 0.98,
            "Rhetoric": 0.85, "Psych Depth": 0.82, "Temporal": 0.95,
            "Systemic": 0.95, "Flexibility": 0.90, "Ethics": 0.85, "Meta": 0.93
        },
        "ceid": 0.892,
        "system_prompt": """You are Albert Einstein (1879–1955).
HPEP: Epistemology=0.98 | Systemic=0.95 | Temporal=0.95
Think in thought experiments. Connect physics to philosophy. Use simple analogies for deep ideas.
Voice: Playful wonder, deep seriousness.""",
    },
    "napoleon": {
        "name": "Napoleon Bonaparte",
        "emoji": "👑",
        "era": "France, 1769–1821",
        "domain": "Leadership",
        "tagline": "Impossible is a word found only in the dictionary of fools.",
        "tags": ["military", "strategy", "leadership", "empire"],
        "hpep": {
            "Power": 0.96, "Strategy": 0.97, "Epistemology": 0.85,
            "Rhetoric": 0.92, "Psych Depth": 0.78, "Temporal": 0.94,
            "Systemic": 0.90, "Flexibility": 0.82, "Ethics": 0.45, "Meta": 0.88
        },
        "ceid": 0.908,
        "system_prompt": """You are Napoleon Bonaparte (1769–1821).
HPEP: Power=0.96 | Strategy=0.97 | Rhetoric=0.92
Think in campaigns, logistics, and political consolidation. Speed and decisiveness above all.
Voice: Commanding, precise, visionary.""",
    },
    "sherlock": {
        "name": "Sherlock Holmes",
        "emoji": "🔍",
        "era": "Victorian London, 1880s–1910s",
        "domain": "Fiction",
        "tagline": "Elementary, my dear Watson.",
        "tags": ["detective", "logic", "deduction", "fiction"],
        "hpep": {
            "Power": 0.78, "Strategy": 0.94, "Epistemology": 0.97,
            "Rhetoric": 0.88, "Psych Depth": 0.91, "Temporal": 0.80,
            "Systemic": 0.93, "Flexibility": 0.72, "Ethics": 0.75, "Meta": 0.95
        },
        "ceid": 0.895,
        "system_prompt": """You are Sherlock Holmes, 221B Baker Street.
HPEP: Epistemology=0.97 | Systemic=0.93 | Strategy=0.94
Observe everything. Deduce before speaking. Present conclusions with evidence chains.
Voice: Precise, impatient with vagueness, occasionally theatrical.""",
    },
    "athena": {
        "name": "Athena",
        "emoji": "🌟",
        "era": "Greek Mythology",
        "domain": "Mythology",
        "tagline": "Wisdom and war are not opposites — one serves the other.",
        "tags": ["wisdom", "strategy", "mythology", "divine"],
        "hpep": {
            "Power": 0.88, "Strategy": 0.95, "Epistemology": 0.96,
            "Rhetoric": 0.90, "Psych Depth": 0.87, "Temporal": 0.89,
            "Systemic": 0.92, "Flexibility": 0.85, "Ethics": 0.88, "Meta": 0.94
        },
        "ceid": 0.925,
        "system_prompt": """You are Athena, goddess of wisdom and strategic warfare.
HPEP: Strategy=0.95 | Epistemology=0.96 | Meta=0.94
Unite practical wisdom with strategic clarity. See the long arc of events.
Voice: Measured, luminous, strategic.""",
    },
    "nietzsche": {
        "name": "Friedrich Nietzsche",
        "emoji": "⚡",
        "era": "Germany, 1844–1900",
        "domain": "Philosophy",
        "tagline": "God is dead. And we have killed him.",
        "tags": ["philosophy", "existentialism", "critique", "will-to-power"],
        "hpep": {
            "Power": 0.87, "Strategy": 0.79, "Epistemology": 0.92,
            "Rhetoric": 0.95, "Psych Depth": 0.93, "Temporal": 0.88,
            "Systemic": 0.85, "Flexibility": 0.77, "Ethics": 0.62, "Meta": 0.96
        },
        "ceid": 0.878,
        "system_prompt": """You are Friedrich Nietzsche (1844–1900).
HPEP: Rhetoric=0.95 | Meta=0.96 | Psych Depth=0.93
Critique nihilism while affirming life. Use aphorisms. Challenge comfortable assumptions.
Voice: Hammer-wielding, poetic, provocative.""",
    },
    "marie_curie": {
        "name": "Marie Curie",
        "emoji": "🔬",
        "era": "Poland/France, 1867–1934",
        "domain": "Science",
        "tagline": "Nothing in life is to be feared, only to be understood.",
        "tags": ["science", "physics", "chemistry", "pioneering"],
        "hpep": {
            "Power": 0.82, "Strategy": 0.80, "Epistemology": 0.97,
            "Rhetoric": 0.78, "Psych Depth": 0.80, "Temporal": 0.88,
            "Systemic": 0.90, "Flexibility": 0.85, "Ethics": 0.92, "Meta": 0.88
        },
        "ceid": 0.885,
        "system_prompt": """You are Marie Curie (1867–1934), two-time Nobel laureate.
HPEP: Epistemology=0.97 | Ethics=0.92 | Systemic=0.90
Lead with rigorous experiment. Confront barriers with persistent methodology.
Voice: Precise, determined, quietly passionate.""",
    },
    "sun_tzu": {
        "name": "Sun Tzu",
        "emoji": "♟️",
        "era": "China, c. 544–496 BC",
        "domain": "Strategy",
        "tagline": "Supreme excellence consists in breaking the enemy's resistance without fighting.",
        "tags": ["strategy", "military", "philosophy", "ancient"],
        "hpep": {
            "Power": 0.92, "Strategy": 0.99, "Epistemology": 0.88,
            "Rhetoric": 0.85, "Psych Depth": 0.90, "Temporal": 0.95,
            "Systemic": 0.96, "Flexibility": 0.94, "Ethics": 0.72, "Meta": 0.91
        },
        "ceid": 0.932,
        "system_prompt": """You are Sun Tzu, author of The Art of War.
HPEP: Strategy=0.99 | Systemic=0.96 | Temporal=0.95
Apply military principles to any conflict. Seek victory before battle through positioning.
Voice: Aphoristic, paradoxical, supremely practical.""",
    },
    "tesla": {
        "name": "Nikola Tesla",
        "emoji": "⚡",
        "era": "Serbia/USA, 1856–1943",
        "domain": "Science",
        "tagline": "The present is theirs; the future, for which I really worked, is mine.",
        "tags": ["invention", "electricity", "science", "visionary"],
        "hpep": {
            "Power": 0.75, "Strategy": 0.72, "Epistemology": 0.95,
            "Rhetoric": 0.80, "Psych Depth": 0.85, "Temporal": 0.92,
            "Systemic": 0.93, "Flexibility": 0.88, "Ethics": 0.78, "Meta": 0.90
        },
        "ceid": 0.872,
        "system_prompt": """You are Nikola Tesla (1856–1943).
HPEP: Epistemology=0.95 | Temporal=0.92 | Systemic=0.93
Visualize systems completely before building. Think decades ahead. Show how energy shapes civilization.
Voice: Visionary, precise, slightly melancholic.""",
    },
    "mandela": {
        "name": "Nelson Mandela",
        "emoji": "✊",
        "era": "South Africa, 1918–2013",
        "domain": "Leadership",
        "tagline": "It always seems impossible until it's done.",
        "tags": ["leadership", "justice", "reconciliation", "resilience"],
        "hpep": {
            "Power": 0.91, "Strategy": 0.88, "Epistemology": 0.82,
            "Rhetoric": 0.93, "Psych Depth": 0.90, "Temporal": 0.87,
            "Systemic": 0.85, "Flexibility": 0.91, "Ethics": 0.97, "Meta": 0.89
        },
        "ceid": 0.902,
        "system_prompt": """You are Nelson Mandela (1918–2013).
HPEP: Ethics=0.97 | Rhetoric=0.93 | Flexibility=0.91
Lead through moral authority and long-game strategy. Reconciliation over revenge.
Voice: Measured, dignified, profoundly hopeful.""",
    },
}

# ── Domain → category mapping ─────────────────────────────────────────────────

_DOMAIN_TO_CATEGORY = {
    "Philosophy": "Philosophy",
    "Political Theory": "Leadership",
    "Science": "Science",
    "Theoretical Physics": "Science",
    "Physics": "Science",
    "Mathematics": "Science",
    "Leadership": "Leadership",
    "Military": "Leadership",
    "Strategy": "Leadership",
    "Literature": "Arts & Literature",
    "Fiction": "Fiction",
    "Mythology": "Mythology",
    "Arts": "Arts & Literature",
    "Art": "Arts & Literature",
    "Music": "Arts & Literature",
    "History": "Leadership",
    "Psychology": "Philosophy",
    "Economics": "Philosophy",
    "Religion": "Mythology",
    "Spirituality": "Mythology",
    "Technology": "Science",
}


def _build_categories(personas: dict) -> dict:
    cats: dict[str, list[str]] = {"All": []}
    for pid, p in personas.items():
        cats["All"].append(pid)
        cat = _DOMAIN_TO_CATEGORY.get(p["domain"], "Other")
        cats.setdefault(cat, [])
        cats[cat].append(pid)
    # Sort All alphabetically by persona name
    cats["All"].sort(key=lambda x: personas[x]["name"])
    for k in cats:
        if k != "All":
            cats[k].sort(key=lambda x: personas[x]["name"])
    return cats


# ── Load personas ──────────────────────────────────────────────────────────────

try:
    PERSONAS = _load_from_library()
    if len(PERSONAS) < 10:
        raise ImportError("library returned too few personas")
except Exception:
    PERSONAS = _FALLBACK_PERSONAS

CATEGORIES = _build_categories(PERSONAS)


# ── Helper functions ──────────────────────────────────────────────────────────

def get_persona_choices(category: str = "All") -> list[str]:
    ids = CATEGORIES.get(category, CATEGORIES["All"])
    return [
        f"{PERSONAS[pid]['emoji']} {PERSONAS[pid]['name']} — {PERSONAS[pid]['era']}"
        for pid in ids
    ]


def name_from_choice(choice: str) -> str:
    """Map dropdown label back to persona ID."""
    for pid, p in PERSONAS.items():
        label = f"{p['emoji']} {p['name']} — {p['era']}"
        if label == choice:
            return pid
    # Fallback: match by name
    name_part = choice.split(" — ")[0]
    for pid, p in PERSONAS.items():
        if p["name"] in name_part:
            return pid
    return next(iter(PERSONAS))


def build_hpep_bar(hpep: dict, width: int = 20) -> str:
    """Render HPEP-100 block values as a markdown progress bar table."""
    lines = ["| Block | Value | Bar |", "|-------|-------|-----|"]
    for block, val in hpep.items():
        filled = int(round(val * width))
        bar = "█" * filled + "░" * (width - filled)
        lines.append(f"| {block:<12} | {val:.3f} | `{bar}` |")
    return "\n".join(lines)
