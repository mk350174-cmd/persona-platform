# Persona Paper Tier Validation Strategy

**Date**: 2026-06-15  
**Status**: Preparatory Phase  
**Target**: M1-M60 papers (60 published papers)  
**Honest Tier Principle**: "Ölçülmüş" (Measured) tiers only after real measurement, not simulation.

---

## 1. Current Tier Distribution Analysis

### Summary (M1-M60)
```
Simülasyon (Simulation):   54 papers (90%)
Hesaplanan (Computed):     9 papers (15%)
Tahmini (Predicted):       46 papers (77%)
```

### Papers by Category

**Only Hesaplanan (Computed)**: M7, M17  
- M7: Mathematical Framework (pure calculation, no empirical test)
- M17: AI-Augmented Polymathy (theoretical framework)

**Simülasyon Only**: M1, M3, M4, M12, M29  
- Foundational papers with simulation-only results
- No "Tahmini" or "Hesaplanan" tiers present

**Mixed (Simülasyon + Others)**: 49 papers  
- Most papers combine multiple evidence types
- Suggests layered validation approach

### Insight
- **Zero papers claim "Ölçülmüş" (Measured)** — current state is honest
- Hesaplanan tiers are rare (9/60) — indicates computational validation is selective
- Heavy reliance on Simülasyon + Tahmini suggests simulation-based extrapolation pattern
- No papers use "Ölçülmüş" tier → all papers are below measured evidence threshold

---

## 2. Evidence Collection Methodology

### Tier Definitions (Honest Scale)

| Tier | Definition | Evidence Required | Risk Level |
|------|-----------|-------------------|-----------|
| **Ölçülmüş** (Measured) | Real-world measurement on human or system data | Peer review + reproducible data + statistical validation | HIGH - only promote with definitive proof |
| **Tahmini** (Predicted) | Model-derived prediction with supporting theory | Derivation from first principles or calibrated model | MEDIUM - extrapolation from limited measurements |
| **Simülasyon** (Simulation) | Computational model matching hypothesis | Code + parameter justification + sensitivity analysis | LOW - controlled environment only |
| **Hesaplanan** (Computed) | Direct mathematical calculation | Derivation + verification | LOW - proof-of-concept level |

### Evidence Hierarchy (Strong → Weak)

1. **Empirical Data** (Ölçülmüş tier only)
   - Real user submissions or system metrics
   - Large N (>30 subjects or >100 instances)
   - Statistical significance (p < 0.05 or Bayesian equivalent)
   - Reproducible in independent lab

2. **Derived Predictions** (Tahmini tier)
   - Mathematical model with validated parameters
   - Extrapolation from empirical anchor points
   - Sensitivity analysis showing robustness

3. **Simulation Results** (Simülasyon tier)
   - Computational reproduction of theory
   - Parameter justification from literature
   - Ablation studies showing mechanism

4. **Calculated Proofs** (Hesaplanan tier)
   - Direct mathematical derivation
   - No empirical validation needed
   - Code verification sufficient

### Validation Workflow

```
Paper Claims X Tier
  ↓
Locate Evidence (results_dir, experiment_module)
  ↓
Assess Evidence Quality
  ├─→ Real measurement? → Ölçülmüş candidate
  ├─→ Derived model? → Tahmini candidate
  ├─→ Simulation? → Simülasyon (current)
  └─→ Pure math? → Hesaplanan (current)
  ↓
Assign Confidence Level (HIGH/MEDIUM/LOW)
  ↓
Document in TIER_VALIDATION_LOG.md
  ↓
Schedule Upgrade (if confidence HIGH)
```

---

## 3. Validation Experiment Design

### What Proves "Ölçülmüş"?

For each candidate paper, we need:

1. **Data Source Validation**
   - Real user submissions, system logs, or published datasets
   - Not synthetic/simulated data
   - Timestamp, provenance, reproducibility

2. **Measurement Robustness**
   - Primary measurement (e.g., HPEP-100 assessment scores)
   - Secondary validation (e.g., inter-rater reliability, test-retest)
   - Effect size + statistical significance

3. **Population Generalizability**
   - Sample size adequate for claimed inference
   - Demographic diversity (if applicable)
   - Comparison group or baseline

4. **Publication Readiness**
   - Findings align with journal standards
   - Methods section reproducible
   - No significant confounds

### Validation Test Examples

#### M1: Persona Collapse Measurement
- **Claim**: Collapse rate measurable in multi-persona systems
- **Evidence Needed**: Real persona consistency scores from production or controlled experiment
- **Test Design**: 
  - Measure consistency of persona responses across 10+ prompts
  - Compare against baseline (LLM without persona framework)
  - N ≥ 50 personas, 100+ prompts
- **Time Estimate**: 2-3 hours (includes prompt generation + scoring)

#### M3: CEID Protocol Validation
- **Claim**: CEID framework reliably measures coherence
- **Evidence Needed**: CEID scores from human evaluators + inter-rater agreement
- **Test Design**:
  - Generate 30 persona outputs
  - 3 independent evaluators rate on CEID axes
  - Calculate Fleiss' kappa (target ≥ 0.6)
- **Time Estimate**: 1-2 hours (includes rater training + scoring)

#### M8: HPEP-100 Validation
- **Claim**: HPEP-100 effectively extracts personas from 100 prompts
- **Evidence Needed**: User submission data (already collected in repo)
- **Test Design**:
  - Validate HPEP-100 against 495 persona bundle
  - Measure extraction accuracy (clustering similarity)
  - Statistical comparison: HPEP-100 vs. full persona
- **Time Estimate**: 1-2 hours (data already available)

#### M19: K-Layer Architecture Validation
- **Claim**: K-layer architecture enables persona coherence
- **Evidence Needed**: Computational verification + empirical performance data
- **Test Design**:
  - Verify K-layer derivation from first principles
  - Benchmark against baseline architectures
  - Measure coherence improvement
- **Time Estimate**: 2-3 hours (includes architecture reimplementation)

---

## 4. Timeline Estimate for Full Validation

### Phase 1: Setup & Audit (Week 1)
- Run audit script on all M1-M60 papers
- Identify candidate papers for Ölçülmüş promotion
- Establish validation test templates
- **Estimate**: 2-3 hours

### Phase 2: High-Impact Tier Promotions (Weeks 2-3)
- M1 (Persona Collapse) → validation experiment
- M3 (CEID Protocol) → inter-rater validation
- M8 (HPEP-100) → user data validation
- M19 (K-Layer Architecture) → computational verification
- **Estimate**: 8-12 hours (2-3 hours each)

### Phase 3: Medium-Impact Validations (Weeks 4-5)
- M2, M5, M7, M10 → supporting evidence review
- Create Tahmini → Ölçülmüş upgrade proposals
- **Estimate**: 6-8 hours

### Phase 4: Low-Hanging Fruit (Week 6)
- Papers with existing empirical data
- Quick confidence checks on Tahmini tier papers
- **Estimate**: 4-6 hours

### Phase 5: Approval & Promotion (Ongoing)
- Peer review of validation evidence
- Update manifest.json + paper files
- Create GitHub issues for promotion tracking
- **Estimate**: 1-2 hours per promotion

### Total Estimate: 6-8 weeks for full validation of all 60 papers

---

## 5. Risk Assessment

### Risk: Tier Over-Promotion
**What breaks**: Credibility loss if papers claim "Ölçülmüş" without real evidence  
**Mitigation**: 
- Require 2 independent reviewers for any promotion
- Document evidence chain in TIER_VALIDATION_LOG.md
- Keep all measurements/scripts in version control
- Revert any tier if evidence questioned

### Risk: Biased Evidence Interpretation
**What breaks**: Unconscious selective reporting of validation results  
**Mitigation**:
- Pre-register validation hypothesis before running experiment
- Report both positive and negative findings
- Use objective metrics (p-values, effect sizes)
- Independent validation (ask colleague to verify result)

### Risk: Incomplete Evidence Recovery
**What breaks**: Some papers may lack original data or experiment code  
**Mitigation**:
- Check `results_dir` and `experiment_module` paths first
- If missing, validate from scratch (re-run experiment)
- Document what evidence exists vs. what's reconstructed
- Flag papers with gaps in traceability

### Risk: Timeline Slippage
**What breaks**: Validations take longer than expected due to missing data  
**Mitigation**:
- Batch validations by paper type (e.g., all HPEP-based first)
- Parallelize independent validations
- Document blockers in TIER_VALIDATION_LOG.md
- Adjust scope if evidence unavailable

### Risk: Tier Regression
**What breaks**: Some papers downgraded from Tahmini → Simülasyon if evidence weak  
**Mitigation**:
- Tier promotion only (no demotion without evidence of error)
- Document reasons for any tier changes
- Notify paper authors of changes
- Keep old tiers in git history

---

## 6. Success Criteria

### For Each Paper Validation
- [ ] Evidence collected and verified
- [ ] At least 1 independent reviewer confirms finding
- [ ] TIER_VALIDATION_LOG.md entry complete
- [ ] No unresolved conflicts between reviewers
- [ ] Tier change (if any) reflected in manifest.json and .tex file

### For Phase Completion
- [ ] Phase audit script runs without errors
- [ ] JSON audit report generated
- [ ] No papers regressed to lower tiers
- [ ] All tier changes traceable to evidence
- [ ] PR reviewable and mergeable

### For Full Validation Cycle
- [ ] M1-M60 fully audited
- [ ] Ölçülmüş papers > Simülasyon papers (goal: >20 Ölçülmüş)
- [ ] Honest tier principle preserved (no unsupported "Ölçülmüş" claims)
- [ ] All validations documented for journal submission
- [ ] Ready for MDPI/Frontiers submission as evidence of peer validation

---

## 7. Related Artifacts

- **TIER_VALIDATION_LOG.md** — Detailed evidence tracking (populated as validations run)
- **scripts/audit_paper_tiers.py** — Automated audit tool
- **VALIDATION_EXPERIMENTS.md** — Specific experiment designs per paper
- **TIER_PROMOTION_WORKFLOW.md** — Approval process and sign-off requirements
- **papers/manifest.json** — Single source of truth for tiers (updated by audit tool)

---

## 8. Integration with CLAUDE.md

Per CLAUDE.md section "MEVCUT DURUM (Haziran 2026)":

> 5. M1-M60 tier güncelleme (Simülasyon → Ölçülmüş)

This strategy implements that priority item. Success means:
- Moving papers from unvalidated tiers to evidence-based tiers
- Honest tier assignments per principle: "Measured/Ölçülmüş sadece gerçek ölçüm sonrası"
- Preparation for MDPI submission (M2 PDF + supporting validation evidence)

---

## Document Control

| Version | Date | Author | Notes |
|---------|------|--------|-------|
| 1.0 | 2026-06-15 | Claude | Initial strategy document |
| TBD | TBD | Reviewer | Post-audit version with data |

