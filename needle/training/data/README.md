# Training data (generated — not committed)

`*.jsonl` and `build.ckpt.json` here are produced by the pipeline and are **gitignored**
(only this README and `.gitkeep` are tracked). Regenerate with:

    python -m needle.training.pipeline --claude-key $ANTHROPIC_API_KEY   # or --limit N (offline)

## Files
- `ceid_dataset.jsonl` — one sample per (persona, conversation):
  `{persona_id, conversation, k_layer_vector, ceid_labels{C,E,I,D,composite}, teacher_scores, confidence, source}`
- `drift_dataset.jsonl` — `{persona_id, conversation_after, drift, drift_score, expected_drift, teacher_scores, source}`
- `voice_dataset.jsonl` — `{persona_id, prompt, voice, teacher, source}` (Claude-weighted gold)
- `train.jsonl` / `val.jsonl` / `test.jsonl` — stratified 0.8 / 0.1 / 0.1 split of the CEID set.
