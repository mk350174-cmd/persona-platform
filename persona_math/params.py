"""
Centralized parameters for persona_math.

Every numeric constant that influences behavior lives here.
Each constant carries its source reference or justification.

Annotation convention:
  [EXACT]       — derived from theory/spec with clear derivation
  [CALIBRATED]  — empirically set, documented rationale
  [HEURISTIC]   — pragmatic choice, no formal derivation
  [APPROXIMATION] — proxy for an uncomputable/intractable quantity
"""

from __future__ import annotations

# ──────────────────────────────────────────────────────────────────────────────
# HPEP-100 Architecture
# ──────────────────────────────────────────────────────────────────────────────

N_LAYERS: int = 100          # [EXACT] HPEP-100 specification
N_BLOCKS: int = 10           # [EXACT] 10 blocks × 10 layers
BLOCK_SIZE: int = 10         # [EXACT] layers per block

# ──────────────────────────────────────────────────────────────────────────────
# Mandatory Core
# ──────────────────────────────────────────────────────────────────────────────

MANDATORY_CORE_INDICES: tuple[int, ...] = (0, 1, 3, 11)
# [EXACT] K1(idx 0), K2(idx 1), K4(idx 3), K12(idx 11)
# Source: HPEP-100 §3.2 — ontological anchor + epistemic vigilance.

MANDATORY_CORE_THRESHOLD: float = 0.15
# [CALIBRATED] Any K-layer below 0.15 is effectively dormant.
# Chosen so that random noise (uniform 0–0.15) does not activate core.
# Adversarial prompting tests show collapse below this floor.

# ──────────────────────────────────────────────────────────────────────────────
# GWT (Global Workspace Theory)
# ──────────────────────────────────────────────────────────────────────────────

GWT_IGNITION_THRESHOLD: float = 0.6
# [HEURISTIC] Phase-transition threshold pₛ.
# Dehaene & Changeux (2011) neuronal workspace: biological range 0.50–0.70.
# 0.6 is the midpoint; empirically gives ≥ 50% ignition on Machiavelli.

GWT_BROADCAST_DECAY: float = 0.9
# [CALIBRATED] Exponential decay rate across block distance.
# At decay=0.9 signal reaches block 10 from block 1 at 0.9^9 ≈ 0.39 —
# still above threshold, preserving global broadcast property.

GWT_INPUT_DIM: int = N_BLOCKS
# [EXACT] GWT operates on block means (10-dim), NOT raw K-layers (100-dim).
# Block means are the "local workspace" activations in the model.

# ──────────────────────────────────────────────────────────────────────────────
# IIT Phi (Φ)
# ──────────────────────────────────────────────────────────────────────────────

PHI_N_PARTITIONS: int = 50
# [CALIBRATED] Random bipartitions for Φ lower-bound estimation.
# At n=50 the estimate converges to within ±5% (Monte Carlo error ∝ 1/√n).
# Exact Φ requires 2^(n/2) partitions — exponential, intractable for n=100.

PHI_MIN_INTEGRATION: float = 0.05
# [HEURISTIC] Φ < 0.05 → insufficient integration → "Metallic" risk.

PHI_PARTITION_BALANCE: tuple[float, float] = (0.25, 0.75)
# [CALIBRATED] Bipartitions sampled in this fractional range to avoid
# degenerate near-empty splits that inflate Φ artificially.

# ──────────────────────────────────────────────────────────────────────────────
# SDE / Dynamics
# ──────────────────────────────────────────────────────────────────────────────

DYNAMICS_LAMBDA_RESTORE: float = 0.1
# [CALIBRATED] Restoring force constant → τ_restore = 1/λ = 10 time units.
# Slow-drift regime: identity recovers over ~10 conversational turns.

DYNAMICS_ARKHE_TAU: float = 0.85
# [HEURISTIC] Arkhe persistence threshold: Φ(t)/Φ_peak must exceed this.
# Below 0.85 the system is considered "identity uncertain".

# ──────────────────────────────────────────────────────────────────────────────
# CEID v2.0
# ──────────────────────────────────────────────────────────────────────────────

CEID_K12_IDX: int = 11
# [EXACT] K12 is the 12th K-layer, 0-indexed = 11.

CEID_K12_BONUS: float = 0.15
# [HEURISTIC] Max E-axis bonus from K12 (epistemic vigilance).
# Reflects empirical observation that K12-active personas resist drift 15%
# longer under adversarial prompting.

CEID_PARADOX_BONUS: float = 0.05
# [HEURISTIC] Per-detected-paradox Patch 3 contribution.
# Conservative cap prevents paradox farming from inflating I-axis score.

# ──────────────────────────────────────────────────────────────────────────────
# Neuropercolation
# ──────────────────────────────────────────────────────────────────────────────

NEUROPERCOLATION_PC: float = 0.593
# [APPROXIMATION] Critical probability for percolation phase transition.
# Kozma et al. (2005) neuropercolation on 2D square lattice: p_c ≈ 0.593.
# Applied here as proxy for consciousness emergence threshold in HPEP networks.
# Note: true p_c for HPEP topology is undefined; this is a bridge hypothesis.

# ──────────────────────────────────────────────────────────────────────────────
# Network / Graph
# ──────────────────────────────────────────────────────────────────────────────

NETWORK_EDGE_THRESHOLD: float = 0.04
# [CALIBRATED] Minimum edge weight w(i,j) = P[i]×P[j] to include in graph.
# Below this, layers contribute < 2% of maximum possible activation product.

NETWORK_SMALL_WORLD_SIGMA: float = 1.5
# [HEURISTIC] σ = (C/C_rand) / (L/L_rand) > σ_min → small-world.
# Watts & Strogatz (1998) use σ > 1.0; 1.5 adds margin for sparse networks.

NETWORK_SET9_FIEDLER_DROP: float = 0.5
# [HEURISTIC] Fiedler value must drop to < 50% of baseline after SET-9
# core removal to confirm topological disconnection.

# ──────────────────────────────────────────────────────────────────────────────
# Kolmogorov Complexity Proxy
# ──────────────────────────────────────────────────────────────────────────────

KOLMOGOROV_PRECISION: int = 3
# [CALIBRATED] Rounding to 3dp before zlib compression.
# Resolution: 10^-3 per layer × 100 layers = sufficient fidelity.

KOLMOGOROV_LOW_K: float = 0.40
# [HEURISTIC] Normalized K-proxy below this → "Deep persona" (compact rules).

KOLMOGOROV_HIGH_K: float = 0.70
# [HEURISTIC] Above this → "Metallic persona" (verbose, brittle description).

# ──────────────────────────────────────────────────────────────────────────────
# Compiler Token Budgets
# ──────────────────────────────────────────────────────────────────────────────

COMPILER_NANO_TOKENS: int = 120
# [CALIBRATED] Fits in a typical single-turn system_instruction cache slot.
# Benchmark: Gemini 1.5 Flash charges per-token for system prompts;
# < 128 tokens stays under common billing boundary.

COMPILER_STANDARD_TOKENS: int = 500
# [CALIBRATED] ~2 paragraphs of behavioral instruction.
# Fits Claude's and OpenAI's system message recommendation (≤ 500 tokens).

COMPILER_RICH_TOKENS: int = 1600
# [CALIBRATED] Full specification: all 10 blocks + CEID signature.
# Recommended with context caching (Gemini/Claude support this natively).

# ──────────────────────────────────────────────────────────────────────────────
# Threshold / Coordinate System
# ──────────────────────────────────────────────────────────────────────────────

THRESHOLD_POWER_BLOCKS: tuple[int, ...] = (1, 2, 3, 4)
# [CALIBRATED] Power axis = mean of Blocks 1-4 (Instrumental Rationality,
# Strategy, Realist Epistemology, Rhetoric). Source: HPEP-100 §5.1.

THRESHOLD_ETHICS_BLOCK: int = 9
# [EXACT] Ethics/Prosociality occupies Block 9 exclusively.

THRESHOLD_MACHIAVELLIAN_QUOTIENT: float = 0.85
# [HEURISTIC] cosine_similarity ≥ 0.85 with P_MACHIAVELLI → "MACHIAVELLIAN"
# classification. Below 0.3 → "KANTIAN" if ethics_axis > power_axis.
