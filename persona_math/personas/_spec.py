"""
Persona Spec Format — reference for all category files.

Each category file exposes a `PERSONAS` list of dicts with this schema:

{
    "id":               str,   # snake_case unique identifier
    "name":             str,   # Full display name
    "label":            str,   # Short descriptor (≤6 words)
    "era":              str,   # "Country/Region, dates"
    "tagline":          str,   # One-line essence (≤20 words)
    "style":            str,   # Communication style
    "voice":            str,   # How they speak / write
    "incompatibilities":str,   # What they reject or refuse
    "price_usd":        float, # 9.99 / 14.99 / 19.99 / 24.99 / 29.99
    "domain":           str,   # Philosophy / Science / Art / Fiction / Myth / Archetype / ...
    "tags":             list,  # searchable keywords
    "seed":             int,   # deterministic vector seed
    "blocks": {                # Block values 1–10, float or dict
        1: float,              #   Power / Instrumental Rationality
        2: float,              #   Strategic Planning
        3: float,              #   Realist Epistemology
        4: float,              #   Rhetoric / Persuasion
        5: float,              #   Psychological Depth
        6: float,              #   Temporal Reasoning
        7: float,              #   Systemic Analysis
        8: float,              #   Cognitive Flexibility
        9: float,              #   Ethics / Prosociality
        10: float,             #   Meta-cognition / Self-model
    },
    "mandatory_core": {        # Mandatory core K-layer overrides (optional)
        0: float,              # K1 — Will / Agency (idx 0, Block 1)
        1: float,              # K2 — Epistemic foundation (idx 1, Block 1)
        3: float,              # K4 — Strategic core (idx 3, Block 1)
        11: float,             # K12 — Social/Rational bond (idx 11, Block 2)
    },
    "block_rules": {           # Behavioral anchors used by the compiler
        1:  ("short_name", "~50-word description of how this block drives behavior"),
        2:  (...),
        ...
        10: (...),
    }
}

Block semantics:
  1  Power / Instrumental Rationality — will, agency, drive, control, ambition
  2  Strategic Planning              — foresight, tactics, planning, intelligence
  3  Realist Epistemology            — how they acquire / evaluate knowledge
  4  Rhetoric / Persuasion           — communication style, argumentation, language
  5  Psychological Depth             — emotional intelligence, self-awareness, motivation
  6  Temporal Reasoning              — relationship to time, history, future, patience
  7  Systemic Analysis               — systems thinking, structure, theory-building
  8  Cognitive Flexibility           — adaptability, creativity, openness
  9  Ethics / Prosociality           — moral stance, empathy, justice, duty
  10 Meta-cognition / Self-model     — self-reflection, identity, consciousness

Pricing guide:
  9.99  — archetype / mythological
  14.99 — fictional character
  19.99 — historical figure (accessible)
  24.99 — philosopher / scientist (moderate demand)
  29.99 — prominent / high-complexity persona
  34.99 — iconic (Shakespeare, Einstein tier)
"""
