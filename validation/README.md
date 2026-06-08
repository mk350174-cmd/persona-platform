# Academic Validation Pipeline

## Why
The series starts at **Ölçülmüş: 0** — every M1–M60 result is simulation. Once PersonaNeedle
is trained, this pipeline re-measures each paper with the real model, upgrades its tier
`Simulated → Measured`, and emits the M61 validation table.

## Run

```bash
# Single paper (dry run):
python -m validation.validator --paper M1 --dry-run

# Whole series (PersonaNeedle must be trained for a real Measured upgrade):
python -m validation.validator --all --workers 2

# Report + M61 LaTeX table:
python -m validation.report_generator --output validation/REPORT.md
```

## Dependency / honesty
PersonaNeedle must be **trained** (`untrained=False`) for a `Measured` upgrade. If it is
untrained (as in this repo environment — no torch/GPU/checkpoint), the pipeline falls back to
`persona_math.ceid`: the "measured" values equal the reference, agreement is 1.0, and the
tier **stays `Simulated`** — it does **not** become `Measured`. `TierUpdater` enforces this
mechanically (Measured requires `evidence["untrained"] is False`), so no simulated value is
ever presented as `Ölçülmüş`.

## Tier hierarchy
`Estimated < Simulated < Computed < Measured` (↔ `Tahmini / Simülasyon / Hesaplanan /
Ölçülmüş`). Upgrades are monotonic (no downgrades).

## Outputs
- `validation/REPORT.md` (tracked) — human-readable tier report.
- `validation/tiers.json` (tracked once upgrades exist) — source of truth for Measured upgrades.
- `validation/progress.json`, `validation/measured/` (gitignored) — per-paper run state.
- `papers/M61_experiments/validation_table.tex` — the 60-row table embedded by M61.
