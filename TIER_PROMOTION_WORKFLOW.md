# Tier Promotion Workflow — Process & Governance

**Date**: 2026-06-15  
**Status**: READY FOR IMPLEMENTATION  
**Applies To**: M1-M60 papers  
**Principle**: "Honest tier" — only promote tiers with real evidence per CLAUDE.md

---

## Overview

Tier promotion is a **formal process** that ensures papers claim only tiers they've earned through validation. This document defines:
1. Who can promote tiers
2. What evidence is required
3. How to update manifest + paper files
4. How to create GitHub issues + PRs
5. How to handle approval/rejection

---

## Authority & Roles

### Roles

| Role | Responsibility | Who? |
|------|-----------------|------|
| **Validator** | Runs experiment, documents evidence | Developer (self-selected) |
| **Peer Reviewer** | Confirms evidence quality, approves promotion | Another developer (not validator) |
| **Maintainer** | Merges approved PRs, updates papers | Senior dev or repo maintainer |

### Decision Rules

- **Tier promotion requires**: Validator + Peer Reviewer both approve
- **Self-review exception**: Hesaplanan tier (pure math) — can be self-reviewed if formula check is exhaustive
- **Blocking**: Any disagreement → discussion, revision, or rejection
- **Escalation**: Unresolved disagreements → ask Maintainer for tiebreaker

---

## Promotion Process

### Step 1: Validate Paper (Validator)

**Owner**: Developer running the validation

**Checklist**:
- [ ] Pick paper from VALIDATION_EXPERIMENTS.md priority list
- [ ] Read paper thoroughly (understand claims)
- [ ] Design validation experiment (reference VALIDATION_EXPERIMENTS.md)
- [ ] Check for blockers (data missing? code unavailable?)
- [ ] Run experiment, collect results
- [ ] Document evidence in TIER_VALIDATION_LOG.md (use template)
- [ ] Calculate metrics (effect sizes, p-values, agreement, etc.)
- [ ] Compare results to success criteria
- [ ] Determine promotion recommendation (NEW_TIER or NO_CHANGE)

**Output**: Entry in TIER_VALIDATION_LOG.md with:
- Hypothesis, method, results
- Links to code/data
- Success criteria assessment
- Confidence level (HIGH/MEDIUM/LOW)
- Promotion recommendation (e.g., "Simülasyon → Tahmini")

**Time Investment**: 2-4 hours per paper (varies)

---

### Step 2: Peer Review (Reviewer)

**Owner**: Independent developer (not validator)

**Checklist**:
- [ ] Read validator's evidence in TIER_VALIDATION_LOG.md
- [ ] Review experiment design (is it sound?)
- [ ] Check success criteria (are they objective?)
- [ ] Verify metrics calculation (math correct?)
- [ ] Assess confidence level (does validator's HIGH match yours?)
- [ ] Consider alternative explanations (is this the only interpretation?)
- [ ] Check for bias or selective reporting (is evidence presented fairly?)
- [ ] Compare to tier definition (does NEW_TIER match evidence quality?)

**Possible Outcomes**:

1. **APPROVED** ✓
   - Evidence sufficient for proposed tier
   - Reviewer comments optional but encouraged
   - Proceed to Step 3

2. **CHANGES_REQUESTED** ⚠️
   - Evidence incomplete or method flawed
   - Reviewer suggests specific improvements
   - Validator revises experiment/analysis
   - Loop back to peer review

3. **REJECTED** ✗
   - Evidence does not support promotion
   - Reviewer explains why tier not yet justified
   - Validator can:
     - Accept rejection (document in log)
     - Request escalation to Maintainer
     - Re-design experiment and resubmit

**Time Investment**: 1-2 hours per paper

**Example Approval Comments**:
```
APPROVED

This HPEP-100 validation is solid. Key points:
- Ground truth personas are well-defined (n=100)
- NMI = 0.74 exceeds success threshold (0.7)
- Extraction reproducible across 3 runs (κ > 0.9)
- Statistics properly calculated (Spearman, not just correlation)

Ready for manifest update. Suggest highlighting the "extraction 
stability" finding in M8 paper update.
```

**Example CHANGES_REQUESTED Comments**:
```
CHANGES_REQUESTED

Good start, but a few concerns:

1. Sample size: Only 20 personas tested. VALIDATION_EXPERIMENTS.md 
   specified n ≥ 30. Please expand to 30 minimum.

2. Inter-rater agreement: Fleiss' κ = 0.58 is borderline (threshold 
   was 0.60). Could you clarify the protocol? Were raters well-trained?

3. Automated comparison: You compared to CEID module, but M3 itself 
   hasn't been promoted yet. Circular reasoning? Suggest comparing to 
   baseline (e.g., random scoring).

Rerun with these adjustments and resubmit.
```

---

### Step 3: Update Files (Validator + Reviewer Together)

**Owner**: Validator (Reviewer confirms changes are correct)

**Checklist**:
- [ ] Update `papers/manifest.json`
- [ ] Update paper `.tex` file
- [ ] Create GitHub issue + PR
- [ ] Run audit script to verify changes
- [ ] Commit with evidence link

#### 3a. Update manifest.json

**File**: `/home/user/persona-platform/papers/manifest.json`

**Change**: `value_tiers_present` array

**Before**:
```json
{
  "id": "M8",
  "title": "The Human Persona Extraction Protocol (HPEP-100)",
  ...
  "value_tiers_present": ["Simülasyon", "Tahmini"],
  ...
}
```

**After** (if promoting Simülasyon → Ölçülmüş):
```json
{
  "id": "M8",
  "title": "The Human Persona Extraction Protocol (HPEP-100)",
  ...
  "value_tiers_present": ["Simülasyon", "Tahmini", "Ölçülmüş"],
  ...
}
```

**Rules**:
- Append NEW_TIER to array (don't remove old tiers)
- Keep tiers sorted by hierarchy: Hesaplanan → Simülasyon → Tahmini → Ölçülmüş
- Use exact Turkish spelling: Ölçülmüş, Simülasyon, Tahmini, Hesaplanan

#### 3b. Update Paper .tex File

**File**: `papers/M[#]_*.tex`

**Change**: Add or update `\tier{}` command in paper

**Markdown Example** (if paper uses comments):
```latex
% TIER CLAIMS:
% - Hesaplanan: Mathematical tensor derivation verified (2026-06-15)
% - Simülasyon: Computational verification of tensor operations
% - Tahmini: Predictions match simulation ±15% (NEW as of 2026-06-15)
% - Ölçülmüş: Empirical validation of tensor stability (NEW as of 2026-06-15)
%
% Last tier update: 2026-06-15 (validator: @alice, reviewer: @bob)
% Evidence: TIER_VALIDATION_LOG.md, commit abc123
```

**LaTeX Example** (if paper has tier section):
```latex
\section*{Evidence Tiers}

\noindent\textbf{Tier Claims:}
\begin{itemize}
    \item \textit{Hesaplanan} (Computed): Mathematical derivation of tensor operations
    \item \textit{Simülasyon} (Simulation): Code verification in Section 4.2
    \item \textit{Tahmini} (Predicted): Theory-simulation comparison, Fig. 5 \textbf{[NEW 2026-06-15]}
    \item \textit{Ölçülmüş} (Measured): Empirical tensor stability test, Table 3 \textbf{[NEW 2026-06-15]}
\end{itemize}

\noindent Last updated: 2026-06-15 | Validator: @alice | Reviewer: @bob
```

**Notes**:
- Include date of promotion
- Reference validation evidence (log entry or commit hash)
- If paper uses \tier{} command, update that
- Otherwise add comment section at top of file

#### 3c. Create GitHub Issue

**Title Format**: `[TIER-VALIDATION] M[#]: [PAPER_TITLE]`

**Labels**: `tier-validation`, `papers`

**Body Template**:
```markdown
## Tier Promotion Request: M[#]

**Paper**: [Title]
**Current Tiers**: [e.g., Simülasyon, Tahmini]
**Proposed Tier**: [e.g., Ölçülmüş]
**Validator**: @[username]
**Reviewer**: @[username]
**Status**: APPROVED (ready for merge)

### Evidence Summary
[1-2 paragraph summary of validation evidence]

### Key Metrics
- Metric 1: [Value] (threshold: [Threshold])
- Metric 2: [Value] (threshold: [Threshold])

### Links
- **Validation Log**: [Link to TIER_VALIDATION_LOG.md#M8]
- **Experiment Code**: [Link to script or notebook]
- **Results Data**: [Link to data/results directory]
- **Paper Update Commit**: [Link to commit with manifest + .tex changes]

### Promotion Criteria Checklist
- [x] Evidence collected in TIER_VALIDATION_LOG.md
- [x] Success criteria defined before experiment
- [x] Results meet or exceed thresholds
- [x] Peer reviewer approves
- [x] manifest.json updated
- [x] Paper .tex file updated
- [x] Commit message includes evidence link

### Reviewer Sign-Off
> APPROVED — Evidence is sufficient for proposed tier.
> Key strengths: [...]
> Comments: [...]
>
> @[reviewer_name]
```

#### 3d. Create PR with Evidence Link

**Branch**: `feat/tier-promote-m[#]-[short-title]`

**Commit Message Format**:
```
docs: promote M[#] to [TIER] tier

Promotion evidence:
- Validation method: [experiment type]
- Key metric: [value] (threshold: [threshold])
- Confidence: [HIGH/MEDIUM/LOW]
- Validator: @[username]
- Reviewer: @[username]

Evidence tracked in: TIER_VALIDATION_LOG.md#M[#]
Related issue: #[issue-number]

https://claude.ai/code/session_01X67Kg9NBPNYDProZ7cnw5H
```

**PR Body**:
```markdown
## Tier Promotion: M[#]

Promotes [PAPER_TITLE] from [OLD_TIERS] to [NEW_TIER].

**Validation evidence**: See TIER_VALIDATION_LOG.md#M[#]
**Issue**: #[issue-number]

### Changes
- [x] papers/manifest.json: Added [TIER] to M[#]
- [x] papers/M[#]_*.tex: Updated tier claims
- [x] TIER_VALIDATION_LOG.md: Added validation entry

### Validation Summary
[Copy key results from log entry]

### Approval Status
- **Validator**: @[username] ✓
- **Reviewer**: @[username] ✓
- **Ready for merge**: YES
```

**PR Checks**:
- [ ] Audit script passes: `python3 scripts/audit_paper_tiers.py`
- [ ] manifest.json is valid JSON
- [ ] No other papers modified (only M[#])
- [ ] Validation log entry complete

---

### Step 4: Merge & Archive (Maintainer)

**Owner**: Repo maintainer

**Checklist**:
- [ ] PR approved by both validator + reviewer
- [ ] CI/CD checks pass
- [ ] Audit script confirms tier change
- [ ] No unintended changes in diff
- [ ] Merge to main
- [ ] Tag issue as closed
- [ ] Update TIER_VALIDATION_LOG.md statistics section

**Example Merge Commit**:
```
Merge #123: Promote M8 (HPEP-100) to Ölçülmüş tier

Tier promotion approved based on HPEP-100 validation:
- HPEP extraction validated against 100 ground-truth personas
- NMI = 0.74 (target: ≥0.70) ✓
- Reproducible across 3 independent runs
- Validator: @alice, Reviewer: @bob

Closes #122

https://claude.ai/code/session_01X67Kg9NBPNYDProZ7cnw5H
```

---

## Handling Rejections

### If Peer Reviewer Rejects

**Validator Options**:

1. **Accept Rejection**
   - Mark in TIER_VALIDATION_LOG.md: `Status: REJECTED`
   - Document why evidence insufficient
   - Close GitHub issue
   - Wait for future work

2. **Request Changes & Resubmit**
   - Revise experiment per reviewer feedback
   - Document changes in TIER_VALIDATION_LOG.md
   - Resubmit for peer review

3. **Request Escalation**
   - Ask Maintainer to review disagreement
   - Maintainer decides: promote, ask for more evidence, or reject
   - Document decision in log

### If Validator Disagrees with Reviewer

**Process**:
1. Validator explains why they believe evidence is sufficient
2. Reviewer clarifies their concerns
3. If unresolved after 1-2 rounds: escalate to Maintainer
4. Maintainer makes final decision
5. Document decision in TIER_VALIDATION_LOG.md

**Example Escalation**:
```markdown
### Validation: M15 — The Experimental Test of the Soul

Status: ESCALATION (validator-reviewer disagreement)

**Validator Assessment**: Evidence sufficient for Ölçülmüş (confidence: HIGH)
- Personality stability measured across 50 personas
- Effect size d = 1.2 (large)
- p < 0.001
- Replicable: κ = 0.91 across runs

**Reviewer Concern**: Sample size (n=50) may be too small for generalization
- Reviewer asks: How representative are these 50 personas?
- Reviewer suggests: Need n ≥ 100 for population claim

**Validator Response**: Success criteria pre-specified n ≥ 30; n=50 exceeds threshold.
- 50 personas span full diversity of persona_math library
- Power analysis confirms n=50 sufficient (α=0.05, β=0.20)

**Escalation**: Maintainer (@bob) requested to decide whether n=50 is 
sufficient for Ölçülmüş claim or if n=100 should be required.
```

---

## Tier Demotion (Rare)

### When Demotion Occurs

Only if evidence found to be **invalid**, not merely weak:
- Experimental error discovered
- Statistical mistake found
- Data fabrication detected
- Methodology fundamentally flawed

### Demotion Process

1. Raise GitHub issue: `[URGENT] Tier demotion request: M[#]`
2. Explain error with evidence
3. Propose new tier
4. Peer review (extra scrutiny)
5. Merge demotion PR
6. Document in TIER_VALIDATION_LOG.md
7. Notify paper author

**Example Demotion PR**:
```
URGENT: Demote M[X] from Ölçülmüş to Tahmini

**Reason**: Experimental error in N calculation discovered
- Previously claimed n=500, actually n=50 (misread data)
- Statistical significance no longer valid with correct N
- Effect size still present, but requires revalidation

**New Tier**: Tahmini (predicted, not measured)
**Action Required**: Rerun with correct N before re-promoting

**Related Issues**: #999 (original validation)
```

---

## Timeline & Batch Processing

### Recommended Batch Schedule

**Week 1** (June 15-21):
- M8, M3: 2 promotions planned
- Parallel work: M1, M5, M6 design

**Week 2** (June 22-28):
- Merge M8, M3 PRs
- M1, M5, M6: 3 promotions
- Parallel: M10, M17, M19 design

**Week 3-4** (June 29-July 12):
- Batch remaining papers (M11-M20)
- Expected: 6-8 additional promotions

### PR Merge SLA

- **APPROVED PRs**: Merge within 48 hours
- **CHANGES_REQUESTED**: Resubmit within 1 week
- **REJECTED**: Document and close within 1 week

---

## Quality Gates

### Mandatory Checks Before Merge

```bash
# 1. Audit script must pass
python3 scripts/audit_paper_tiers.py --output audit_report.json

# 2. Manifest must be valid JSON
python3 -m json.tool papers/manifest.json > /dev/null

# 3. Tier hierarchy preserved (no regressions)
# Use audit report to check
```

### Code Review Checklist

- [ ] manifest.json tiers in correct order (per hierarchy)
- [ ] No tiers removed, only added
- [ ] Paper .tex file updated with new tier + date
- [ ] TIER_VALIDATION_LOG.md entry complete
- [ ] Evidence links point to correct locations
- [ ] Success criteria were pre-defined (not post-hoc)
- [ ] Peer reviewer is different person from validator
- [ ] No unrelated changes in diff

---

## Documentation & Audit Trail

### What to Keep

✓ All validation code + results (in `experiments/` or `results/`)  
✓ Statistical output and plots  
✓ TIER_VALIDATION_LOG.md entries (permanent record)  
✓ GitHub issues + PR discussions  
✓ Manifest/paper edits (in git history)  

### What NOT to Keep

✗ Intermediate data files (too large)  
✗ API keys or credentials  
✗ Personal notes (put in log instead)  

---

## Approval Authority

### By Tier

| Tier | Approval Required | Can Self-Review? |
|------|------------------|-----------------|
| Hesaplanan | Peer reviewer (can be lenient for pure math) | YES (if formula check thorough) |
| Simülasyon | Peer reviewer | NO (need external validation) |
| Tahmini | Peer reviewer | NO (need theory check) |
| Ölçülmüş | Peer reviewer (strict) | NO (NEVER — empirical claims need skepticism) |

---

## Example: Complete M8 Promotion

### Step 1: Validation (3 hours)
```
Validator: @alice
- Ran HPEP-100 on 100 ground-truth personas
- Compared extracted traits to expert definitions
- Results: NMI = 0.74, Spearman r = 0.68
- Log entry created: TIER_VALIDATION_LOG.md#M8
- Recommendation: Promote to Ölçülmüş
```

### Step 2: Peer Review (1.5 hours)
```
Reviewer: @bob
- Read experiment design: Sound methodology
- Checked success criteria: n=100 met, NMI > 0.7 met
- Verified statistics: Correct calculations
- Assessment: APPROVED
- Comment: "Extraction stability across runs is impressive (κ=0.91)"
```

### Step 3: Update Files (30 minutes)
```bash
# Edit papers/manifest.json
# - Add "Ölçülmüş" to M8 value_tiers_present

# Edit papers/M8_HPEP100_v2.tex
# - Add comment: "TIER: Ölçülmüş (validated 2026-06-15)"

# Create GitHub issue #122: "Tier Promotion: M8 HPEP-100"

# Create PR #123 with commit message:
# "docs: promote M8 (HPEP-100) to Ölçülmüş tier"
```

### Step 4: Merge (15 minutes)
```
Maintainer: @carol
- Verify audit script passes ✓
- Confirm both signatures (validator + reviewer) ✓
- Merge PR #123 to main
- Close issue #122
- Update TIER_VALIDATION_LOG.md statistics: +1 Ölçülmüş promotion
```

### Total Time: ~5 hours (parallelizable)

---

## Integration with GitHub Milestones

### Milestone: "Tier Validation Phase 1"
- Goal: Promote M1-M10 papers (or similar subset)
- Due: End of June 2026
- Issues: Link all M1-M10 tier promotion PRs
- Success: ≥5 papers promoted to higher tiers

### Milestone: "Tier Validation Complete"
- Goal: All M1-M60 papers validated + tiers updated
- Due: Mid-July 2026
- Success: >20 papers promoted to Ölçülmüş

---

## FAQ

**Q: Can I promote my own paper's tier (self-review)?**  
A: No, except for pure math (Hesaplanan). All empirical tiers require peer review.

**Q: What if the reviewer is biased?**  
A: Escalate to Maintainer. They can request a second reviewer or override decision.

**Q: Can we promote multiple tiers at once (e.g., Simülasyon → Tahmini + Ölçülmüş)?**  
A: Only if evidence supports both jumps. Normally promote one tier at a time.

**Q: How do we handle papers where evidence is partially available?**  
A: Document in log (what's available, what's missing). Promote to highest supported tier only.

**Q: Can reviewers comment anonymously?**  
A: For neutrality, yes. But signature (approval/rejection) must be public in PR.

**Q: What if we want to revise a promoted tier later?**  
A: Demotion is rare. If needed, treat as new validation (same process).

---

## Contacts & Escalation

- **Validator Questions**: Check VALIDATION_EXPERIMENTS.md
- **Tier Definition Questions**: Check TIER_VALIDATION_STRATEGY.md
- **Process Questions**: Ask Maintainer (@carol)
- **Disputes**: Escalate to Maintainer

---

## Document Control

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-06-15 | Initial workflow document |

