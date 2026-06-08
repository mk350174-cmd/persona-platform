"""LoRA subpackage. ``LoRAConfig`` + the analytic estimator are torch-free (eager); the
torch-backed ``LoRALinear`` / ``LoRAAdapter`` load lazily (PEP 562)."""

from .config import LoRAConfig, estimate_lora_trainable_params, n_attention_blocks

__all__ = ["LoRAConfig", "estimate_lora_trainable_params", "n_attention_blocks",
           "LoRALinear", "LoRAAdapter"]


def __getattr__(name):
    if name in ("LoRALinear", "LoRAAdapter"):
        from . import adapter
        return getattr(adapter, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
