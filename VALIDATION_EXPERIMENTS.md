# Validation Experiment Designs for M1-M20

**Date**: 2026-06-15  
**Priority**: High-impact papers (M1-M20 cover foundational concepts)  
**Format**: Experiment designs ready for implementation  
**Evidence Level Target**: Move from Simülasyon/Tahmini → Ölçülmüş where possible

Each design includes:
- **Hypothesis**: What we're measuring
- **Evidence Type**: What tier this would support
- **Experiment Design**: Practical steps
- **Success Criteria**: How to know validation worked
- **Time Estimate**: Hours to complete
- **Data Requirements**: What we need beforehand
- **Blockers**: Known issues

---

## M1: The Metallic Feel — Measuring Persona Collapse

**Current Tiers**: Simülasyon  
**Target Tier**: Tahmini or Ölçülmüş  
**Paper**: M1_Metalik_His_v5.tex

### Hypothesis
Persona consistency decreases when personas are overused or in conflict, leading to measurable "collapse" in response coherence.

### Evidence Type
- **Simülasyon** (current): Computational simulation showing collapse patterns
- **Tahmini** (target): Statistical prediction of collapse rate from first principles
- **Ölçülmüş** (ambitious): Real persona consistency scores from system logs or user experiments

### Experiment Design (Ölçülmüş level)
1. **Setup**: Create 50-100 distinct personas using persona_math library
2. **Protocol**: For each persona, generate 20 distinct system prompts across:
   - Unrelated topics (should be consistent)
   - Conflicting positions (measure collapse)
   - High repetition scenarios (measure drift)
3. **Measurement**: 
   - Consistency score (cosine similarity between response embeddings)
   - Coherence metric from CEID protocol (M3)
   - Time-series tracking of coherence decay
4. **Data Source**: 
   - Can use 495 persona bundle if available
   - Alternative: generate synthetic personas + test prompts
5. **Analysis**:
   - Plot collapse curve: consistency vs. prompt count
   - Fit decay model (exponential? power law?)
   - Compare to simulation baseline from original M1 experiment

### Success Criteria
- Coherence scores correlate with response consistency (r > 0.6)
- Collapse rate matches M1 simulation predictions (±20%)
- Degradation pattern reproducible across 3+ persona cohorts

### Time Estimate
- Setup + prompt generation: 1 hour
- Experiment runs: 1-2 hours (depends on parallelization)
- Analysis + comparison to M1: 1 hour
- **Total: 3-4 hours**

### Data Requirements
- 495 persona bundle (persona_math/personas/)
- CEID scoring module (from M3)
- Template prompts for consistency testing

### Blockers
- [ ] persona bundle availability
- [ ] CEID module must import torch-free
- [ ] Response embeddings may require external API

---

## M2: The Mandatory Core — Topological Necessity

**Current Tiers**: Hesaplanan, Simülasyon  
**Target Tier**: Ölçülmüş (already strong evidence)  
**Paper**: M2_Zorunlu_Cekirdek_v4.tex

### Hypothesis
Every persona system (LLM with fixed instructions) has a topological mandatory core — a minimum set of parameters that cannot be removed without system failure.

### Evidence Type
- **Hesaplanan** (current): Pure mathematical derivation
- **Simülasyon** (current): Computational verification
- **Ölçülmüş** (target): Empirical identification of cores in real personas

### Experiment Design (Ölçülmüş level)
1. **Setup**: Select 5-10 well-defined personas from bundle
2. **Core Identification**:
   - Systematic parameter ablation (remove instructions one at a time)
   - Test system output for coherence/functionality loss
   - Identify minimal set where further removal breaks system
3. **Measurement**:
   - Binary: passes/fails coherence check at each ablation step
   - Quantitative: CEID score change
   - Map core to topological structure (M2 theoretical model)
4. **Data Source**: 
   - 495 persona bundle
   - System logs showing instruction sensitivity

### Success Criteria
- Every persona has identifiable mandatory core (per M2 theory)
- Core size consistent with M2 predictions (±50%)
- Topological structure matches theoretical model

### Time Estimate
- Ablation study design: 1 hour
- Systematic testing: 1-2 hours
- Core mapping + analysis: 1 hour
- **Total: 3-4 hours**

### Data Requirements
- Persona bundle with full instruction sets
- Instruction/parameter metadata
- CEID validation module

### Blockers
- [ ] Instruction set granularity (can we ablate at instruction level?)
- [ ] Definition of "core" (what threshold counts as failure?)

---

## M3: CEID Protocol — Four-Axis Measurement Framework

**Current Tiers**: Simülasyon  
**Target Tier**: Ölçülmüş  
**Paper**: M3_CEID_v4.tex

### Hypothesis
CEID protocol (Coherence, Expressivity, Identity, Drift) reliably measures persona coherence across different LLM outputs.

### Evidence Type
- **Simülasyon** (current): Computational simulation of CEID scoring
- **Ölçülmüş** (target): Human-validated CEID scores (inter-rater agreement)

### Experiment Design (Ölçülmüş level)
1. **Setup**: Generate 30-50 diverse persona outputs (different personas, same prompts)
2. **Rater Training**: Brief 3 independent raters on CEID axes
3. **Scoring**: Each rater scores all outputs on 4 CEID axes (1-5 Likert scale)
4. **Validation**:
   - Calculate Fleiss' kappa (multi-rater agreement)
   - Compare human scores to automated CEID module
   - Identify axis-level agreement patterns
5. **Data Source**: Persona outputs from bundle or generation pipeline

### Success Criteria
- Fleiss' kappa ≥ 0.6 (moderate agreement)
- Automated CEID scores correlate with human ratings (r > 0.7)
- All 4 axes show agreement (no axis drops below κ = 0.4)

### Time Estimate
- Rater training: 0.5 hours
- Batch scoring (30-50 items × 3 raters): 2 hours
- Analysis + inter-rater statistics: 1 hour
- **Total: 3.5 hours**

### Data Requirements
- 30-50 persona response samples
- CEID scoring rubric (from M3 paper)
- Automated CEID module for comparison

### Blockers
- [ ] Recruiting 3 independent raters (can use team members)
- [ ] Rubric clarity (may need training examples)

---

## M4: The Court of 250 — Nash Equilibrium

**Current Tiers**: Simülasyon  
**Target Tier**: Tahmini  
**Paper**: M4_Adalet_Sarayi_v3.tex

### Hypothesis
Multi-persona systems (250+ personas) reach Nash equilibrium in decision-making, where no single persona can improve its outcome by unilaterally changing strategy.

### Evidence Type
- **Simülasyon** (current): Game-theoretic simulation
- **Tahmini** (target): Derived Nash predictions validated against simulation

### Experiment Design (Tahmini level)
1. **Setup**: Replicate M4 simulation with 250 personas
2. **Theory**: Derive Nash equilibrium conditions from first principles
3. **Comparison**: 
   - Run simulation to convergence
   - Extract actual equilibrium point
   - Compare to theoretical predictions
4. **Validation**:
   - Plot actual vs. predicted strategies
   - Measure convergence rate agreement
   - Sensitivity analysis (how robust is equilibrium?)

### Success Criteria
- Theoretical predictions match simulation within 15%
- Equilibrium is stable (small perturbations return to same state)
- Applies to 90%+ of persona cohorts tested

### Time Estimate
- Theory derivation: 1 hour
- Simulation setup + runs: 1.5 hours
- Comparison + sensitivity analysis: 1 hour
- **Total: 3.5 hours**

### Data Requirements
- M4 simulation code and parameters
- Persona interaction data (from simulation)
- Game theory solver (can use scipy.optimize)

### Blockers
- [ ] Simulation code accessibility
- [ ] Nash equilibrium definition (mixed vs. pure strategies?)
- [ ] **Missing: circularity check (audit finding AF-P-007, 2026-07-29).**
  `persona_math/params.py`'s `COURT_DEONTOLOGICAL_RATIO = 0.604` is
  reverse-derived from the target 151/99 split (0.604 = 151/(151+99)),
  not independently established — see the Persona repo's `params.py`
  docstring and M4's corrected abstract. This plan does not currently
  include deriving the 0.604 ratio independently of the 151/99 target
  it is meant to explain. Without that, "Nash predictions validated
  against simulation" risks validating a simulation against the
  parameter that was tuned to produce it.

---

## M5: Tensor Network Architecture — Chimera Protocol

**Current Tiers**: Hesaplanan, Simülasyon  
**Target Tier**: Ölçülmüş (if tensor operations validated)  
**Paper**: M5_Kimera_v4.tex

### Hypothesis
Tensor network architecture enables stable multi-motor persona systems by distributing coherence maintenance across tensor contractions.

### Evidence Type
- **Hesaplanan** (current): Mathematical tensor derivation
- **Simülasyon** (current): Simulation of tensor operations
- **Ölçülmüş** (ambitious): Verified tensor computations + empirical performance

### Experiment Design (Hesaplanan level validation)
1. **Verification**: Verify all tensor contraction formulas from M5 paper
2. **Code Review**: Check tensor_network implementation
3. **Dimension Checks**: Ensure tensor dimensions match theoretical spec
4. **Numerical Stability**: Test for NaN/infinity in contraction results
5. **Data Source**: tensor_network module code (if exists)

### Success Criteria
- All tensor formulas verified (mathematical proof or exhaustive test)
- Code passes dimension checks (no shape mismatches)
- No numerical instabilities on standard test cases

### Time Estimate
- Formula verification: 1 hour
- Code review: 0.5 hours
- Numerical testing: 1 hour
- **Total: 2.5 hours**

### Data Requirements
- M5 paper (LaTeX source and PDF)
- tensor_network module code
- Test personas for empirical validation

### Blockers
- [ ] tensor_network implementation availability
- [ ] Numerical precision requirements

---

## M6: Arkhe — Identity Commitment

**Current Tiers**: Simülasyon, Tahmini  
**Target Tier**: Ölçülmüş  
**Paper**: M6_Arkhe_v3.tex

### Hypothesis
Identity commitment in personas is irreversible once established, analogous to thermodynamic entropy increase.

### Evidence Type
- **Simülasyon** (current): Simulation showing irreversibility
- **Tahmini** (current): Theoretical prediction
- **Ölçülmüş** (target): Empirical measurement of identity drift/irreversibility

### Experiment Design (Ölçülmüş level)
1. **Setup**: Create persona with initial identity markers (name, background, values)
2. **Protocol**: 
   - Phase 1: Reinforce identity through 50 consistent prompts
   - Phase 2: Attempt to "revert" identity (contradictory instructions)
   - Phase 3: Measure identity markers before/after reversion
3. **Measurement**:
   - Identity vector before/after (using persona encoding)
   - Semantic similarity of identity-defining statements
   - Success rate of identity reversion attempts
4. **Hypothesis Test**: Identity fails to revert (supports irreversibility)

### Success Criteria
- Identity markers persist after reversion attempts (>80% similarity)
- Irreversibility measurable across 20+ personas
- Effect size matches M6 simulation predictions

### Time Estimate
- Experiment protocol design: 1 hour
- Execution (50+50+reversion prompts): 1.5 hours
- Identity analysis: 1 hour
- **Total: 3.5 hours**

### Data Requirements
- Persona encoding module
- Prompt templates for identity reinforcement
- Semantic similarity metrics (BERT embeddings or similar)

### Blockers
- [ ] Identity encoding definition (what constitutes identity?)
- [ ] Evaluation metric for "reversion failure"

---

## M7: Mathematical Framework — Unified Model

**Current Tiers**: Hesaplanan  
**Target Tier**: Ölçülmüş unlikely (pure math theory)  
**Paper**: M7_Matematiksel_Cerceve_v4.tex

### Notes
Pure mathematical framework — Hesaplanan tier is appropriate. No higher tier needed unless novel empirical application discovered.

### Validation Task (Hesaplanan level)
- Verify all equations in M7 (symbolic math verification)
- Check dimensional consistency across all derivations
- Test tool table (Tables 1-N) against actual persona systems

### Time Estimate: 1-2 hours

---

## M8: HPEP-100 — Human Persona Extraction Protocol

**Current Tiers**: Simülasyon, Tahmini  
**Target Tier**: Ölçülmüş (strong candidate — real user data available)  
**Paper**: M8_HPEP100_v2.tex

### Hypothesis
HPEP-100 extraction protocol accurately identifies persona characteristics from 100 natural language prompts, validatable against human-defined persona profiles.

### Evidence Type
- **Simülasyon** (current): Simulation showing extraction fidelity
- **Tahmini** (current): Prediction of extraction accuracy
- **Ölçülmüş** (target): Validation against real user submissions or expert-defined personas

### Experiment Design (Ölçülmüş level)
1. **Setup**: Use 495 persona bundle (if ground truth available) or solicit expert persona definitions
2. **Extraction**: Run HPEP-100 on test personas → extract characteristic vectors
3. **Validation**:
   - Clustering: extracted personas should cluster like ground truth
   - Similarity: extracted traits match expert ratings (inter-rater agreement)
   - Dimensionality: extracted features match expected M8 structure
4. **Measurement**:
   - Normalized Mutual Information (NMI) between extracted and ground truth clusters
   - Spearman correlation of trait scores
   - Silhouette score of extracted clusters

### Success Criteria
- NMI ≥ 0.7 (strong cluster agreement)
- Spearman r ≥ 0.6 for trait predictions
- Extraction replicable across 3+ independent runs

### Time Estimate
- Data preparation: 1 hour
- HPEP-100 execution: 1 hour
- Clustering + validation: 1.5 hours
- **Total: 3.5 hours**

### Data Requirements
- 495 persona bundle or ground truth persona definitions
- HPEP-100 implementation (experiments/exp_m8_hpep_convergent.py)
- Clustering library (sklearn.cluster)

### Blockers
- [ ] Ground truth persona definitions (do we have expert annotations?)
- [ ] HPEP-100 code availability and torch-free compatibility

---

## M9: PPEP — Poetic Persona Extraction

**Current Tiers**: Simülasyon, Tahmini  
**Target Tier**: Tahmini or Ölçülmüş  
**Paper**: M9_PPEP_v01.tex

### Hypothesis
Poetic outputs reveal persona aesthetic preferences and emotional tenor in ways numeric assessments miss.

### Evidence Type
- **Simülasyon** (current): Simulation of poetic extraction
- **Ölçülmüş** (ambitious): Validation by human readers of extracted persona

### Experiment Design (Tahmini level)
1. **Setup**: Generate poetic output from 10-15 personas using PPEP prompts
2. **Expert Readers**: 3 independent judges read poems (blind to persona)
3. **Assessment**: Judge what persona characteristics they infer from poem
4. **Comparison**: Judge inferences vs. actual persona definitions

### Success Criteria
- Judges correctly identify persona dimension (>60% accuracy on forced choice)
- Qualitative agreement on persona tone/style
- Poem-based inference matches HPEP-100 extraction (r > 0.5)

### Time Estimate
- Prompt generation + poetry execution: 1 hour
- Judge evaluation + scoring: 1.5 hours
- Analysis: 1 hour
- **Total: 3.5 hours**

### Data Requirements
- PPEP prompt set and execution code
- Persona bundle
- Blind scoring template for judges

### Blockers
- [ ] Poetry generation quality (is output meaningful?)
- [ ] Judge recruitment and training
- [ ] **Missing: negative control (audit finding AF-P-007, 2026-07-29).**
  The design above only tests blind judge-matching; it does not include
  applying the same PPEP reading/scoring procedure to unrelated,
  non-persona-derived text (e.g. random poems or prose) to check
  whether judges "find" persona characteristics that aren't really
  there (Barnum/Forer-effect risk). This negative control should be
  added — and run — before the blind-matching result above is
  interpreted as evidence that PPEP extracts real persona signal.

---

## M10-M20: Rapid Validation Summary

| M# | Title | Current | Target | Approach | Time |
|----|----|---------|--------|----------|------|
| M10 | HPEP-250 Atlas | Hesaplanan, Simülasyon | Tahmini | Validate 250-persona taxonomy structure | 2-3h |
| M11 | Hegesias Problem | Simülasyon, Tahmini | Ölçülmüş | User risk assessment survey | 3h |
| M12 | Researcher Paradox | Simülasyon | Tahmini | Comparative study: AI vs. human researcher bias | 3h |
| M13 | Digital Copy Ontology | Hesaplanan, Simülasyon, Tahmini | Ölçülmüş | Philosophical framework validation + case study | 2-3h |
| M14 | Consent Ethics | Simülasyon, Tahmini | Tahmini (stable) | Literature review validation | 1-2h |
| M15 | Soul Test | Simülasyon, Tahmini | Ölçülmüş | Empirical testing on persona cohort | 3h |
| M16 | D1 Benchmark | Hesaplanan, Simülasyon | Ölçülmüş | Validate benchmark dataset + N=1→population transition | 2-3h |
| M17 | Polymathy | Hesaplanan | Tahmini | Measure knowledge synthesis capability | 2-3h |
| M18 | aMCC Persona | Simülasyon, Tahmini | Tahmini (stable) | Neuroscience literature comparison | 1-2h |
| M19 | Rock/River | Simülasyon, Tahmini | Ölçülmüş | Empirical personality stability testing | 3h |
| M20 | Termination Problem | Simülasyon, Tahmini | Tahmini (ethics, hard to measure) | Ethical framework validation | 1-2h |

---

## Prioritization Matrix

### High Impact × Low Effort (Do First)
1. **M8** (HPEP-100): Real user data, validation straightforward.
   **Status note (audit finding AF-P-007, 2026-07-29): still not
   executed**, despite being ranked top priority here — this
   contradicts M32's own note that "real IRT calibration on humans is
   future work." If this plan's priority ranking is still current,
   M8 execution should actually be scheduled, not just ranked first.
2. **M3** (CEID): Inter-rater validation quick win
3. **M1** (Collapse): Directly testable on persona bundle

### High Impact × Medium Effort (Do Second)
4. **M5** (Tensor): Formula verification, good for theoretical validation
5. **M19** (Rock/River): Personality stability directly measurable
6. **M6** (Arkhe): Identity irreversibility testable

### Medium Impact × Low Effort (Quick Wins)
7. **M10** (Atlas): Taxonomy structure validation
8. **M17** (Polymathy): Knowledge capability measurement

### Lower Priority (Defer or Combine)
- **M11, M12, M14, M18, M20**: Ethics/philosophy focused (harder to measure empirically)
- **M7**: Pure math (already Hesaplanan, no higher tier needed)

---

## Resource Requirements Summary

### One-Time Setup
- [ ] Rater training materials for CEID (M3)
- [ ] Ground truth persona definitions (for M8, M10)
- [ ] Prompt templates for consistency testing (M1, M6)

### Reusable Infrastructure
- CEID scoring module (torch-free)
- Persona encoding/embedding module
- Clustering + statistical analysis utilities
- Blind scoring/evaluation templates

### Timeline (Best Case)
- **Week 1**: M8 + M3 (6-7 hours) → 2 tier promotions
- **Week 2**: M1 + M5 + M6 (10-12 hours) → 3 tier promotions
- **Week 3**: M10, M17, M19 (7-9 hours) → 3 tier promotions
- **Week 4**: Remaining M11-M20 (12-15 hours) → 6-8 tier promotions
- **Total: 35-45 hours over 4 weeks**

---

## Validation Checklist Template

For each experiment, use this:

```
[ ] Hypothesis clearly stated
[ ] Success criteria defined before running experiment
[ ] Data sources confirmed available
[ ] Experiment protocol documented
[ ] Runs executed and logged
[ ] Results analyzed and documented
[ ] Comparison to simulation/theory done
[ ] Evidence sufficient for tier promotion?
[ ] Second reviewer agrees
[ ] TIER_VALIDATION_LOG.md updated
[ ] Manifest.json updated
[ ] PR created with evidence links
```

---

## Next Steps

1. Pick M8 (HPEP-100) as first experiment — uses existing data
2. Run audit script to identify blockers
3. Gather ground truth persona definitions
4. Execute M8 validation (3-4 hours)
5. Document findings in TIER_VALIDATION_LOG.md
6. Create PR for M8 tier promotion
7. Use M8 success as template for remaining experiments

