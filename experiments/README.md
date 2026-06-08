# `experiments/` — Empirical-Validation Harness (M1–M60)

A reproducible **simulation** harness that runs the existing `persona_math` / `integrations`
mathematics on the existing ~500-persona library to produce real, tier-stamped numbers for every
paper of the Persona Engineering Research Series, embeds them into the LaTeX sources, and builds
self-contained submission bundles.

> **Why "simulation"?** This environment has no LLM API keys and no outbound network, so real
> GPT-4/Claude/Llama experiments cannot be run here. The harness is built around a swappable data
> source so that a real-LLM backend slots in later (see *Plug-in path* below). Numbers produced here
> are computed/simulated — never presented as real measurements.

## Quick start

```bash
pip install -r requirements.txt        # numpy, scipy, networkx, scikit-learn
make experiments                       # run all 60 exp_m* → results/M1..M60/
make check-provenance                  # audit: no 'Ölçülmüş' tier emitted
make validate-tex                      # lint generated LaTeX (balanced, data-only, paths resolve)
make manifest                          # papers/manifest.json + papers/INDEX.md
make embed-papers                      # insert \input snippets + finalize headers (idempotent)
make submissions                       # self-contained per-paper bundles → submissions/M{n}/
pytest tests/ -q                       # 356 tests (harness + library)
```

`python -m experiments.run_all [--only M1 M4] [--seed N] [--check-provenance]` runs a subset or audits.

## Architecture

| Module | Role |
|---|---|
| `provenance.py` | `Tier` enum + `stamp()` / `run_metadata()`; `MASTER_SEED`. Refuses to emit `Ölçülmüş`. |
| `providers/base.py` | `SeriesProvider` ABC + `ResponseSeries` dataclass. |
| `providers/simulated.py` | `SimulatedProvider` (default) — deterministic persona-conditioned series from the library. |
| `providers/llm_stub.py` | `LLMProvider` — the real-LLM **plug-in point** (reads env keys; `NotImplementedError` here). |
| `series_builders.py` | control / adversarial (SET-9 core-erosion) / peaking (entropy) turn schedules. |
| `_common.py` | persona selection, synthetic population, `lossy_transfer`, `partial_reconstruction`, `expectation_pull`, `individuation_recovery`, `k_layer`/`k_block`. |
| `io_utils.py` | `results.json` / `.csv` / pgfplots `.dat` writers, `latex_escape`, and a `--lint` gate. |
| `figtex.py` | `\input`-able pgfplots figure / booktabs table snippets (data-only; never `\includegraphics`). |
| `exp_m1_*.py … exp_m60_*.py` | one `run(provider, seed, outdir) -> dict` per paper. |
| `run_all.py` | ordered registry + run loop + provenance audit. Meta-scanners (M7, M17, M26) run last. |
| `build_manifest.py` | parses paper headers → `papers/manifest.json` + `papers/INDEX.md`. |
| `embed_into_papers.py` | inserts the `\section*{Computational Validation (Simulation)}` block + finalizes headers (v0.1→v1.0, strip TASLAK/Draft). Idempotent. |
| `make_submission_bundles.py` | per-paper self-contained `submissions/M{n}/` (paths rewritten local). |

Each `exp_m*` reuses the implemented math (`d1_protocol`, `ceid`, `dynamics`, `tensor_spectral`,
`network_game`, `consciousness`, `incharacter_ceid`, `autogen_court`) — it does not reimplement it.

## Integrity model (non-negotiable)

Value tiers from `docs/PM_Sistem_Promptu_v4.md`:

| Tier | Meaning | Used by harness? |
|---|---|---|
| **Ölçülmüş** | real measured data (e.g. the Holmes/Court experiments) | **never emitted** (enforced by test + `make check-provenance`) |
| **Tahmini** | estimated / not yet run (real-LLM, fMRI, human, GPU, legal/historical scholarship) | yes — for documented future work |
| **Hesaplanan** | mathematically derived (non-experimental) | yes |
| **Simülasyon** | a simulated run of the framework | yes — the default |

Rules followed throughout: papers with **measured** data (M1 `tab:results`, M3 Holmes, M4 151/99)
are **augmented, not overwritten**; real-data-dependent cores are labelled `Tahmini`.

**CEID-saturation note.** `CEID` is near-ceiling for any structurally-valid vector (the generic mean
scores ≈1.0 against every persona). So for any *fidelity / continuity / recovery / prediction* measure
the harness uses **individuation-recovery** (deviation from the population mean), drift, or cosine —
**not** raw CEID. Where a claim genuinely cannot be shown on synthetic vectors (e.g. M43 D-axis
maturation), it is reported honestly as a null/limitation with the real study flagged `Tahmini`.

## Reproducibility

Library vectors are seed-fixed; the harness uses a single `MASTER_SEED` (per-experiment offset);
`run_d5_atlas`/KMeans use `random_state=42`. Two runs are byte-identical except the `generated_utc`
timestamp. Determinism, provenance, LaTeX-lint and pytest are all green.

## Outputs

- `results/M{n}/` — `results.json` (tier-stamped), `*.csv`, `figdata/*.dat`, `tex/*.tex` snippets.
- `papers/M{n}_*.tex` — finalized, with the embedded validation block (`\input{../results/...}`).
- `submissions/M{n}/` — self-contained, uploadable copies (paths rewritten local).
- `papers/manifest.json`, `papers/INDEX.md`, `papers/CHANGELOG.md`.

## Plug-in path: real-LLM runs

Implement `providers/llm_stub.LLMProvider.build_series` / `embed` (prompt the persona, collect N
turns, embed each to a 100-dim K-layer vector) and pass it to any `exp_m*.run(provider=…)`. The
downstream math is identical; numbers produced from real model output would then be **Ölçülmüş** —
emitted by *that* class, run where API keys + egress exist (not here).

## Out of scope (here)

PDF building (no LaTeX toolchain; `pdflatex`/`tectonic` unavailable), arXiv/journal submission
(no egress; human process), and real-LLM/fMRI/human-subject/GPU experiments. The harness leaves
documented hooks for all of these.
