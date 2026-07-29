---
description: Runs the full CEID v2.0 diagnostic on a persona. Shows HPEP vector, Shannon entropy, metallic score, IIT Phi, GWT ignition, Fiedler connectivity, and all 8 patches. Use for deep persona analysis.
---

# Persona Diagnostic

Run full CEID v2.0 diagnostic on persona `$ARGUMENTS`.

## Instructions

```python
from persona_math.persona_library import PERSONA_LIBRARY
from persona_math.persona_factory import make_persona_vector
from persona_math.ceid import ceid_full_diagnostic
from persona_math.foundation import shannon_h, metallic_score
from persona_math.consciousness import gwt_ignition, iit_phi_approx

# Get persona vector
# Run full diagnostic pipeline
```

## Diagnostic Output

```
═══════════════════════════════════════════════
  PERSONA DIAGNOSTIC: [Name]
  HPEP-100 v2.0 | CEID Full Analysis
═══════════════════════════════════════════════

CORE METRICS
  Shannon Entropy H:    X.XXX bits  [DEEP/METALLIC/MIXED]
  Metallic Score:       0.XXX       [<0.10 clean | >0.30 metallic]
  CEID Composite:       0.XXXX      [OPTIMAL/HIGH/MEDIUM/LOW]
  IIT Φ (approx):       X.XXX

BLOCK ACTIVATIONS (10 blocks)
  B1  Power/Drive:      ████████░░  0.XX
  B2  Strategy:         ███████░░░  0.XX
  B3  Epistemology:     █████████░  0.XX
  B4  Rhetoric:         ████████░░  0.XX
  B5  Psych Depth:      █████████░  0.XX
  B6  Temporal:         ████████░░  0.XX
  B7  Systemic:         █████████░  0.XX
  B8  Flexibility:      ████████░░  0.XX
  B9  Ethics:           ██░░░░░░░░  0.XX
  B10 Meta-cognition:   █████████░  0.XX

CONSCIOUSNESS INDICATORS
  GWT Ignition:         XX/100 layers firing
  Fiedler λ₂:           X.XXX  [connected/disconnected]
  Power/Ethics ratio:   X.XX×

CEID v2.0 — 8 PATCHES
  P1  Autopoietic veto:    PASS/WARN
  P2  Heisenberg buffer:   PASS/WARN
  P3  Gödel incompleteness: PASS/WARN
  P4  IIT Φ threshold:     PASS/WARN
  P5  Kolmogorov bound:    PASS/WARN
  P6  Lyapunov stability:  PASS/WARN
  P7  Nash equilibrium:    PASS/WARN
  P8  Free energy min:     PASS/WARN

HPEP COVERAGE
  Category A (Epistemic):    XX%
  Category E (Emotional):    XX%
  Category I (Intentional):  XX%
  Category J (Neuro):        XX%  [often missing]

VERDICT: [DEEP COHERENT / SURFACE METALLIC / MIXED / PATHOLOGICAL]
═══════════════════════════════════════════════
```

## Example
`/persona:diagnostic machiavelli` → full reference threshold analysis
`/persona:diagnostic socrates` → see ethics-epistemic dominance pattern
