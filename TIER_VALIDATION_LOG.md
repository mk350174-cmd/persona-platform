# Tier Validation Log — M1-M60 Papers

**Purpose**: Track all paper tier validation attempts, evidence collected, and tier changes  
**Format**: One entry per validation attempt (append-only log)  
**Status**: TEMPLATE — No validations completed yet (2026-06-15)

---

## Log Entry Template

```
### Validation: M[#] — [Paper Title]

**Date**: YYYY-MM-DD  
**Validator**: [Name]  
**Status**: [NOT_STARTED | IN_PROGRESS | COMPLETED | BLOCKED]

#### Summary
[1-2 sentence description of validation attempt]

#### Original Tier
- Claimed: [Hesaplanan | Simülasyon | Tahmini | Ölçülmüş]
- Evidence: [Brief description of current evidence]

#### Validation Approach
- **Method**: [Experiment type]
- **Hypothesis**: [What we're testing]
- **Success Criteria**: [Quantitative threshold for tier promotion]

#### Results
- **Outcome**: [PASS | FAIL | PARTIAL]
- **Key Metric**: [e.g., "Fleiss' kappa = 0.72"]
- **Confidence**: [HIGH | MEDIUM | LOW]

#### Evidence Artifacts
- **Code**: [Link to experiment code or notebook]
- **Data**: [Location of results data]
- **Analysis**: [Link to analysis scripts/results]
- **Reproducibility**: [Steps to re-run validation]

#### Recommendation
- **New Tier**: [Hesaplanan | Simülasyon | Tahmini | Ölçülmüş | NO CHANGE]
- **Rationale**: [Why this tier is justified by evidence]

#### Reviewer Sign-Off
- **Reviewed By**: [Peer reviewer name]
- **Approval**: [APPROVED | CHANGES_REQUESTED | REJECTED]
- **Comments**: [Reviewer feedback]

#### Changes Made
- [ ] manifest.json updated
- [ ] Paper .tex file updated with new tier
- [ ] Results published or documented
- [ ] GitHub issue created (if applicable)

#### Notes
[Any blockers, interesting findings, or follow-up needed]

---
```

---

## Completed Validations (In Order of Completion)

*No validations completed yet. Entries will be appended as validations complete.*

---

## In-Progress Validations

### Status Board

| Paper | Validator | Status | Est. Completion |
|-------|-----------|--------|-----------------|
| (none yet) | — | — | — |

---

## Blocked Validations

*Will track papers where validation is blocked due to missing data, unclear requirements, etc.*

| Paper | Blocker | Status | Resolution |
|-------|---------|--------|-----------|
| (none yet) | — | — | — |

---

## Validation Statistics (Live)

```
Total validations planned: 60 (M1-M60)
Validations completed: 0
Papers with tier changes: 0
Papers promoted to Ölçülmüş: 0
Papers promoted to Tahmini: 0
Average time per validation: — (not yet tracked)
Approval rate (APPROVED / total): — (0%)
```

---

## Quick Reference: Tier Definitions

**For validators**: Use these definitions when assessing evidence quality.

| Tier | Definition | Evidence Examples | Promotion Threshold |
|------|-----------|------------------|-------------------|
| **Ölçülmüş** (Measured) | Real-world measurement on human/system data | Peer-reviewed user study, production metrics, empirical dataset | p < 0.05, n > 30, independent replication |
| **Tahmini** (Predicted) | Model-derived prediction with supporting theory | Derivation from first principles, calibrated to empirical anchors | Theory validated, predictions ±20% of measured |
| **Simülasyon** (Simulation) | Computational model matching hypothesis | Simulation code, parameter justification, sensitivity analysis | Code reproducible, ablation studies pass |
| **Hesaplanan** (Computed) | Direct mathematical calculation | Derivation, symbolic proof, numerical verification | Formula correct, no computational errors |

---

## Validation Schedule (Proposed)

### Week 1 (June 15-21)
- [ ] M8 (HPEP-100) — High priority, existing data
- [ ] M3 (CEID) — High priority, inter-rater validation
- Target: 2 promotions

### Week 2 (June 22-28)
- [ ] M1 (Collapse) — Foundational test
- [ ] M5 (Tensor) — Theory verification
- [ ] M6 (Arkhe) — Identity measurement
- Target: 3 promotions

### Week 3 (June 29-July 5)
- [ ] M10 (Atlas) — Taxonomy validation
- [ ] M17 (Polymathy) — Knowledge synthesis
- [ ] M19 (Rock/River) — Stability testing
- Target: 3 promotions

### Week 4 (July 6-12)
- [ ] M11-M20 remaining papers (batch validation)
- [ ] Philosophy/ethics papers (may have lower promotion rate)
- Target: 4-6 promotions

---

## Governance Rules

### Who Can Promote Tiers?
1. **Validator** runs experiment + documents evidence
2. **Peer Reviewer** (≠ validator) reviews evidence quality
3. **Approval Gate**: Both validator + reviewer must sign off
4. **Exception**: Hesaplanan tier (math proofs) can be self-reviewed if formula check is thorough

### Evidence Standards by Tier

**Promoting to Ölçülmüş**:
- [ ] Real data (not simulation)
- [ ] n > 30 or sufficient statistical power
- [ ] Documented measurement protocol
- [ ] Independent reviewer confirms measurement quality
- [ ] Effect size reported (not just p-value)

**Promoting to Tahmini**:
- [ ] Theory clearly stated
- [ ] Parameters justified from literature or empirical anchors
- [ ] Predictions testable and specific
- [ ] Sensitivity analysis showing robustness

**Promoting to Simülasyon** (usually not a promotion):
- Usually papers start here; demotion unlikely
- If promoting from lower tier, show simulation code is robust

### Reverting Tiers (Rare)
- Only if evidence found to be invalid
- Document the error and reason for reversion
- Notify paper author
- Keep old tier in git history for audit trail

---

## Validation Workflow (Step-by-Step)

1. **Pick Paper** (from VALIDATION_EXPERIMENTS.md priority list)
   - Start with highest impact + lowest effort
   
2. **Design Experiment** (reference VALIDATION_EXPERIMENTS.md)
   - Define hypothesis, success criteria, data needs
   - Check for blockers (missing data, code not available)
   
3. **Execute Experiment** (torch-free where possible)
   - Run code, collect results, log outputs
   - Document any deviations from plan
   
4. **Analyze Results** (statistical rigor required)
   - Compare to success criteria
   - Calculate effect sizes, confidence intervals
   - Generate plots/tables
   
5. **Document Evidence** (this log)
   - Fill in all fields in "Log Entry Template" above
   - Include links to code/data
   - Be specific about metrics and thresholds
   
6. **Submit for Review** (peer review required)
   - Share evidence with independent reviewer
   - Ask specific question: "Is this evidence sufficient for [NEW_TIER]?"
   - Document reviewer comments
   
7. **Update if Approved**
   - [ ] `papers/manifest.json`: Update `value_tiers_present` for paper
   - [ ] `papers/M[#]_*.tex`: Update tier claim in paper file
   - [ ] Create GitHub issue: `docs: promote M[#] to [TIER] tier`
   - [ ] Commit message: "docs: promote M[#] to [TIER] tier per validation evidence"
   
8. **Track in Statistics** (update table at top of log)
   - Increment "Validations completed"
   - Update "Papers with tier changes"
   - Log average time

---

## Reusable Analysis Templates

### For Ölçülmüş Validation

```python
# Template: Statistical validation check
import scipy.stats as stats
import numpy as np

# Compare extracted features to ground truth
extracted = np.array([...])  # From experiment
ground_truth = np.array([...])  # Expert labels

# Correlation
corr, p_value = stats.spearmanr(extracted, ground_truth)
print(f"Spearman r = {corr:.3f}, p = {p_value:.4f}")

# Success criteria
assert corr > 0.6, f"Correlation too low: {corr}"
assert p_value < 0.05, f"Not significant: {p_value}"
print("✓ Evidence sufficient for Ölçülmüş promotion")
```

### For Tahmini Validation

```python
# Template: Theory vs. experiment comparison
import numpy as np
from sklearn.metrics import mean_absolute_percentage_error

# Theoretical predictions
theory_predictions = np.array([...])

# Observed simulation results
observed = np.array([...])

# MAPE: mean absolute percentage error
mape = mean_absolute_percentage_error(observed, theory_predictions)
print(f"MAPE = {mape:.1%}")

# Success criteria: within 20%
assert mape < 0.20, f"Predictions too far off: {mape}"
print("✓ Theory validated, promote to Tahmini")
```

### For Hesaplanan Validation

```python
# Template: Mathematical verification
from sympy import *

# Define symbols
x, y, z = symbols('x y z')

# Verify formula from paper
formula_from_paper = x**2 + y**2 + z**2
my_derivation = expand((x + y + z)**2 - 2*x*y - 2*y*z - 2*z*x)

# Check equivalence
assert simplify(formula_from_paper - my_derivation) == 0
print("✓ Formula verified, Hesaplanan tier confirmed")
```

---

## Contact & Questions

For questions about this validation log:
- Check TIER_VALIDATION_STRATEGY.md for overall approach
- Check VALIDATION_EXPERIMENTS.md for specific experiment designs
- Check TIER_PROMOTION_WORKFLOW.md for approval process

---

## Revision History

| Date | Change | Version |
|------|--------|---------|
| 2026-06-15 | Template created | 1.0 |
| TBD | First validations logged | 1.1+ |

