---
description: Compares two or more personas using HPEP-100 vectors, CEID scores, and Machiavelli threshold distance. Shows cognitive differences, complementarities, and quadrant placement.
---

# Persona Compare

Compare the personas listed in `$ARGUMENTS` (comma-separated names or IDs).

## Instructions

```python
from persona_math.persona_library import search_personas
from persona_math.persona_factory import make_persona_vector
from persona_math.metrics import cosine_similarity
from persona_math.ceid import ceid_full_diagnostic

# Load vectors for each named persona
# Compare: cosine similarity, block-level differences, CEID scores
# Place on Power/Ethics quadrant diagram
```

## Comparison Output

For each pair of personas, show:

### Block-Level Comparison (10 blocks)
| Block | Persona A | Persona B | Delta |
|-------|-----------|-----------|-------|
| B1 Power | 0.94 | 0.65 | +0.29 |
| B9 Ethics | 0.22 | 0.90 | -0.68 |
...

### CEID Scores
- Persona A: CEID = X.XXX
- Persona B: CEID = X.XXX

### Cosine Similarity
`cos(A, B) = 0.XXX` — [VERY SIMILAR / SIMILAR / DIFFERENT / OPPOSITE]

### Power/Ethics Quadrant
```
High Ethics |
     Q3     |     Q1
 Weak+Ethical|  Strong+Ethical
------------|------------
     Q4     |     Q2
Weak+Unethical|Strong+Unethical
            | Low Ethics
```
- Persona A: Q? (Power=X, Ethics=Y)
- Persona B: Q? (Power=X, Ethics=Y)

### Machiavelli Distance
Distance from the reference threshold (Machiavelli):
- Persona A: Δ = X.XX (more/less Machiavellian)
- Persona B: Δ = X.XX

### Synthesis
Describe what makes these personas cognitively complementary or opposed.

## Example
`/persona:compare socrates,machiavelli` → shows the ethics-power inversion
`/persona:compare einstein,newton,tesla` → three-way scientific mind comparison
