# PersonaNeedle

A tiny **SAN (Simple Attention Network)** that runs *on-device* persona evaluation —
CEID measurement, identity-drift detection, and persona-voice generation — from a single
~26M-parameter model distilled from large teacher models and quantized to INT4/GGUF.

> **Status: architecture + scaffolds.** This environment has no `torch`, no GPU, and no
> teacher-model egress, so nothing here is trained, quantized, or run. The code is a
> correct, runnable-elsewhere implementation; the parameter/size budget is verified
> analytically (torch-free) and by the tests where torch is installed. Train via
> `distillation.py`, export via `quantizer.py`, on a machine with `needle/requirements.txt`.

## Why a SAN architecture?

Needle-style **attention-only** layers (no feed-forward blocks) keep the model tiny and
edge-friendly: removing FFNs is exactly what lets a 12-encoder / 8-decoder / 512-hidden
model land at **~26M parameters** (with an FFN it would be 3–4× larger). Grouped-query
attention (8 query / 4 KV heads) + RoPE further shrink the KV footprint for long context
(2048 tokens) on phones/tablets.

## Differences from Needle

| | Needle | PersonaNeedle |
|---|---|---|
| Layers | attention-only | attention-only (kept) |
| Shape | encoder | **encoder (12) + decoder (8)** for voice generation |
| Conditioning | — | **K-layer persona vector** (HPEP-100) projected to a persona-prefix token |
| Outputs | task-specific | **three heads**: CEID / drift / voice |
| Heads tying | — | voice head **tied** to the token embedding (→ ~26M) |

## Three output heads

1. **`ceid_head`** → 4 values in `[0,1]` (sigmoid): the C/E/I/D axes of CEID.
2. **`drift_head`** → 2 logits: binary identity-drift (0 = stable, 1 = drift) + score.
3. **`voice_head`** → vocabulary logits (tied to the embedding): persona-voice decoding.

The encoder's persona-prefix token is pooled for the CEID/drift heads; the decoder does
masked self-attention + cross-attention to the encoder memory for voice.

## Hybrid distillation

Three teachers produce soft labels that are merged and distilled with KL divergence:

| Teacher | Role | Weight |
|---|---|---|
| **Claude** | persona depth + CEID measurement | 0.5 |
| **Gemini** | function-calling / structured output | 0.3 |
| **Llama** | open-weights zero-cost baseline | 0.2 |

Training data is assembled from existing assets: persona vectors and **reference CEID
labels** from `persona_math/` (`ceid_score`), and simulated conversations / CEID from
`experiments/` + `results/`. See `architecture/distillation.py`.

## Integration with `persona_math`

- K-layer vectors are read via `persona_math.persona_library.get_library_persona`.
- `PersonaNeedle.reference_ceid()` returns `persona_math.ceid.ceid_score` on the persona's
  K-layer vector — the **labeled target** the SAN's `ceid_head` is distilled toward (the
  SAN's own `measure_ceid` is meaningless until trained; outputs carry an `untrained` flag).

## Size target (honest)

At ~26M parameters, **INT4 ≈ 13MB** of weights (4-bit ⇒ 0.5 byte/param; compression ratio
≈0.125 vs FP32). On-device **total target is 15–20MB** = model (~13MB) + K-layer vector +
persona visual + persona audio. (The ~8MB figure is only reachable below ~16M params; we
keep the specified ~26M architecture and report the real size — see `quantizer.size_report`.)

## Usage (where torch is installed)

```python
from needle import PersonaNeedle, PersonaNeedleConfig, size_report
cfg = PersonaNeedleConfig(persona_id="aristotle")
needle = PersonaNeedle(cfg)                 # untrained until distilled
print(needle.reference_ceid())              # persona_math target (works now)
print(size_report(cfg))                     # {'int4_mb': 13.15, 'fp32_mb': 105.2, ...}
# needle.measure_ceid(text) / detect_drift(text) / generate_voice(prompt) / full_pipeline(...)
```

`make`-free: install `needle/requirements.txt`, then `pytest needle/tests` (torch tests
skip automatically if torch is absent; the param/size estimator tests always run).
