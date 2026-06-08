# PersonaNeedle training-data pipeline

Generates the distillation dataset for `needle/` PersonaNeedle: synthetic conversations
per persona → CEID / drift / voice labels from a hybrid of teachers → validated,
stratified-split JSONL.

## Teachers (hybrid)

| Teacher | Weight | Role |
|---|---|---|
| Claude (`claude-sonnet-4-20250514`) | 0.5 | persona depth + CEID gold standard |
| Gemini (`gemini-2.0-flash`) | 0.3 | structured second opinion |
| Llama (Ollama `llama3.2:3b`) | 0.2 | open-weights baseline |
| **PersonaMath (offline)** | fallback | `persona_math.ceid` — used when no API/Ollama is reachable |

Final label = `Σ(weight·label) / Σ(weight)`; `confidence` = inter-teacher agreement.

## Usage

```bash
pip install -r needle/training/requirements.txt

# Claude only (simplest):
python -m needle.training.pipeline --claude-key $ANTHROPIC_API_KEY --n-conversations 20

# Hybrid (full quality):
python -m needle.training.pipeline --claude-key $ANTHROPIC_API_KEY \
  --gemini-key $GEMINI_API_KEY --llama-endpoint http://localhost:11434

# Resume from checkpoint:
python -m needle.training.pipeline --claude-key $ANTHROPIC_API_KEY --resume

# Offline demo (no keys → PersonaMathTeacher fallback):
python -m needle.training.pipeline --limit 3 --n-conversations 4
```

Outputs to `needle/training/data/`: `ceid_dataset.jsonl`, `drift_dataset.jsonl`,
`voice_dataset.jsonl`, then `train/val/test.jsonl` (0.8/0.1/0.1, stratified per persona).
The run is checkpointed (`build.ckpt.json`) and resumable.

## Estimated cost (Claude Sonnet, full run)

534 personas × 20 conversations × 3 label types ≈ **32,040 API calls ≈ $45–65**. Gemini
(free tier, 15 rpm) and a local Llama reduce/offset the Claude share.

## Notes

- **Graceful degradation:** if all teachers are unreachable, the pipeline uses the offline
  `PersonaMathTeacher` (derives labels from `persona_math.ceid` + the conversation's pressure
  level) so it always produces a dataset — that is the path exercised in this repo's CI
  (no API egress / no Ollama here). Real Claude/Gemini/Llama labels require keys + network on
  your machine.
- This dataset feeds `needle/architecture/distillation.py` (KL distillation into PersonaNeedle);
  the model stays `untrained` until trained on it.
- Generated data is gitignored (`data/.gitkeep` keeps the empty dir).
