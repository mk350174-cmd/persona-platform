"""
PersonaNeedle — a small SAN (Simple Attention Network) for on-device persona
evaluation (CEID + drift + voice), distilled from Claude/Gemini/Llama teachers and
quantized to INT4/GGUF. See ``needle/README.md``.

``import needle`` is safe without torch: config / distillation / quantizer load eagerly;
the torch-backed ``SAN`` / ``PersonaNeedle`` load lazily on first access.
"""

from .architecture.config import (
    PersonaNeedleConfig,
    estimate_param_count,
    estimate_int4_size_mb,
    estimate_fp32_size_mb,
)
from .architecture import (
    Teacher, ClaudeTeacher, GeminiTeacher, LlamaTeacher,
    TEACHER_WEIGHTS, merge_soft_labels, kl_distillation_loss,
    build_training_data, DistillationTrainer,
    size_report, quantize_int4, export_gguf,
)

__version__ = "0.1.0"
__all__ = [
    "PersonaNeedleConfig", "estimate_param_count", "estimate_int4_size_mb",
    "estimate_fp32_size_mb", "Teacher", "ClaudeTeacher", "GeminiTeacher",
    "LlamaTeacher", "TEACHER_WEIGHTS", "merge_soft_labels", "kl_distillation_loss",
    "build_training_data", "DistillationTrainer", "size_report", "quantize_int4",
    "export_gguf", "SAN", "PersonaNeedle",
]


def __getattr__(name):  # lazy torch-backed imports
    if name in ("SAN", "PersonaNeedle"):
        import importlib
        return getattr(importlib.import_module(".architecture", __name__), name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
