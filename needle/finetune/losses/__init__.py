"""Loss subpackage. All losses require torch, so they load lazily (PEP 562) — the package
imports cleanly without torch."""

__all__ = ["CEIDLoss", "DriftLoss", "VoiceLoss"]

_LAZY = {"CEIDLoss": "ceid_loss", "DriftLoss": "drift_loss", "VoiceLoss": "voice_loss"}


def __getattr__(name):
    if name in _LAZY:
        import importlib
        mod = importlib.import_module(f".{_LAZY[name]}", __name__)
        return getattr(mod, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
