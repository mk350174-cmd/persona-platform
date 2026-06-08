# PersonaNeedle fine-tune + quantization pipeline

Turns the **untrained** ~26M SAN (`needle/architecture/`) into a deployable, INT4-quantized,
15–20 MB per-persona bundle, trained on the hybrid-teacher dataset from `needle/training/`.

```
needle/finetune/
├── trainer.py              # PersonaNeedleTrainer — fine-tune orchestrator
├── lora/{config,adapter}   # LoRAConfig (+ analytic estimator) · LoRALinear / LoRAAdapter
├── losses/{ceid,drift,voice}_loss.py   # CEID KL · drift BCE (pos_weight=2) · voice CE (+perplexity)
├── quantize/{int4,gguf_writer,validator}.py   # INT4 · GGUF · accuracy QC
├── export/{persona_bundler,android_export}.py # 15–20 MB bundle · Android assets
├── checkpoints/            # training output (gitignored, .gitkeep'd)
└── tests/test_finetune.py
```

## Pipeline

```bash
pip install -r needle/finetune/requirements.txt

# 1. Fine-tune (data from needle/training/ — see PATCH-03)
python -m needle.finetune.trainer \
    --train needle/training/data/train.jsonl \
    --val   needle/training/data/val.jsonl \
    --lora --epochs 3 --device cuda           # or mps (Apple Silicon)

# 2. INT4 quantization
python -m needle.finetune.quantize.int4 \
    --model needle/finetune/checkpoints/best_model --output needle/finetune/quantize/output

# 3. GGUF export (llama.cpp container)
python -m needle.finetune.quantize.gguf_writer \
    --quantized needle/finetune/quantize/output \
    --config needle/finetune/checkpoints/best_model/config.json --persona-id machiavelli

# 4. Persona bundle (model + K-layer + visual + audio → manifest.json)
python -m needle.finetune.export.persona_bundler \
    --persona-id machiavelli --gguf needle/finetune/export/output/machiavelli.gguf

# 5. Android assets
python -m needle.finetune.export.android_export \
    --bundle needle/finetune/export/output/machiavelli --out android/app/src/main/assets
```

> **Module paths:** the spec's folder tree nests `quantize/` and `export/` under
> `needle/finetune/`, so the commands are `needle.finetune.quantize.*` /
> `needle.finetune.export.*` (a couple of the spec's inline headers wrote the shorter
> `needle.quantize.*` — the tree is authoritative).

## Training objective

`total = 0.4·CEID + 0.3·drift + 0.3·voice` (terms re-normalise if a dataset is absent).
Per epoch: val loss, **CEID MAE**, **drift F1** (scikit-learn), **perplexity**; checkpoint +
**early stopping** (patience 3). `evaluate()` sets the model's `untrained` flag to `False`;
`save()` merges the LoRA delta into full weights and writes `config.json`.

**LoRA budget:** r=8 over `q/k/v/o_proj` across 28 attention blocks (12 enc + 8 dec×2) ≈
**0.80M trainable** (~3% of the ~26M frozen backbone) — verify torch-free with
`estimate_lora_trainable_params(cfg, lora_cfg)`. (The spec's "~500K" was an estimate.)

## Estimated training time

| Hardware | Time |
|---|---|
| GPU (A100) | ~2 h |
| GPU (T4 / Colab) | ~6 h |
| CPU | impractical |

## Sizes (honest)

INT4 model ≈ **13.15 MB** (`estimate_int4_size_mb` of the default 26M SAN); a full persona
bundle = model + K-layer (~0.8 MB) + visual (~3.9 MB) + audio (~2.1 MB) ≈ **19 MB**, inside
the 15–20 MB target (`PersonaBundler.validate_size`).

## Integration

- `needle/architecture/` → the `PersonaNeedle` / `SAN` model + torch-free size estimators;
  `quantizer.quantize_int4` / `export_gguf` are reused by the quantize stage.
- `needle/training/data/` → `train/val/test.jsonl` (CEID) + sibling `drift_dataset.jsonl` /
  `voice_dataset.jsonl` (joined by `persona_id`).
- `needle/architecture/persona_needle.py` → the `untrained` flag is flipped to `False` after
  training.
- `persona_mcp/` → can serve CEID measurements from the trained model.

## Environment note

**Nothing is trained / quantized / exported in this repo environment** (no torch, no gguf,
no GPU, no trained weights). The torch/gguf-backed files are written correct and byte-compiled;
their tests are `@requires_torch` and skip here. The **torch-free** parts — `LoRAConfig`
validation, the LoRA-param estimator, `PersonaBundler` manifest + 15–20 MB size check,
`AndroidExporter` asset layout — run and are tested here.
