"""PersonaNeedle architecture package.

Config + distillation + quantizer are import-safe without torch. The torch-backed
``SAN`` / ``PersonaNeedle`` are imported lazily (PEP 562) so the package can be imported
in environments where torch is not installed.
"""

from .config import (
    PersonaNeedleConfig,
    estimate_param_count,
    estimate_int4_size_mb,
    estimate_fp32_size_mb,
)
from .distillation import (
    Teacher, ClaudeTeacher, GeminiTeacher, LlamaTeacher,
    TEACHER_WEIGHTS, merge_soft_labels, kl_distillation_loss,
    build_training_data, DistillationTrainer,
)
from .quantizer import size_report, quantize_int4, export_gguf

__all__ = [
    "PersonaNeedleConfig", "estimate_param_count", "estimate_int4_size_mb",
    "estimate_fp32_size_mb", "Teacher", "ClaudeTeacher", "GeminiTeacher",
    "LlamaTeacher", "TEACHER_WEIGHTS", "merge_soft_labels", "kl_distillation_loss",
    "build_training_data", "DistillationTrainer", "size_report", "quantize_int4",
    "export_gguf", "SAN", "PersonaNeedle",
]


def __getattr__(name):  # lazy torch-backed imports
    if name == "SAN":
        from .san import SAN
        return SAN
    if name == "PersonaNeedle":
        from .persona_needle import PersonaNeedle
        return PersonaNeedle
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
