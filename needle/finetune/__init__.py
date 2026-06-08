"""
PersonaNeedle fine-tune + quantization pipeline.

``import needle.finetune`` is safe without torch: the LoRA config + analytic estimator and
the export (bundler / Android) modules load eagerly; the torch-backed pieces — LoRA layers,
losses, the trainer, and the quantizers — load lazily on first access (PEP 562).

Stages: LoRA fine-tune (``trainer``) → INT4 quantization (``quantize``) → GGUF export →
15–20 MB persona bundle (``export``). See ``needle/finetune/README.md``.
"""

from .lora.config import LoRAConfig, estimate_lora_trainable_params
from .export.persona_bundler import PersonaBundler, validate_size
from .export.android_export import AndroidExporter

__all__ = [
    "LoRAConfig", "estimate_lora_trainable_params", "PersonaBundler", "validate_size",
    "AndroidExporter", "LoRALinear", "LoRAAdapter", "CEIDLoss", "DriftLoss", "VoiceLoss",
    "PersonaNeedleTrainer", "INT4Quantizer", "QuantizedModel", "GGUFWriter",
    "QuantizationValidator",
]

_LAZY = {
    "LoRALinear": ".lora.adapter",
    "LoRAAdapter": ".lora.adapter",
    "CEIDLoss": ".losses.ceid_loss",
    "DriftLoss": ".losses.drift_loss",
    "VoiceLoss": ".losses.voice_loss",
    "PersonaNeedleTrainer": ".trainer",
    "INT4Quantizer": ".quantize.int4",
    "QuantizedModel": ".quantize.int4",
    "GGUFWriter": ".quantize.gguf_writer",
    "QuantizationValidator": ".quantize.validator",
}


def __getattr__(name):  # lazy torch-/gguf-backed imports
    if name in _LAZY:
        import importlib
        mod = importlib.import_module(_LAZY[name], __name__)
        return getattr(mod, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
