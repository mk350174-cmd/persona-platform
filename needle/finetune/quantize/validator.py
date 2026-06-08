"""
Quantization quality control (requires torch for real inference).

Compares the FP32 model against its quantized counterpart on a small test set and flags
regressions: CEID mean-absolute-error delta and drift-accuracy delta must stay within
tolerance, otherwise the quantization is reported as failing.
"""

from __future__ import annotations

CEID_MAE_TOLERANCE = 0.05      # mean |ΔCEID| must stay below this
DRIFT_ACC_TOLERANCE = 0.02     # drift accuracy may drop by at most 2%


class QuantizationValidator:
    def __init__(self, ceid_mae_tolerance: float = CEID_MAE_TOLERANCE,
                 drift_acc_tolerance: float = DRIFT_ACC_TOLERANCE):
        self.ceid_tol = ceid_mae_tolerance
        self.drift_tol = drift_acc_tolerance

    def validate(self, original, quantized, test_data: list) -> dict:
        """``original`` / ``quantized`` expose ``measure_ceid``/``detect_drift`` (PersonaNeedle-like);
        ``test_data`` is a list of conversation strings (or dicts with a ``conversation`` key)."""
        import numpy as np

        def _conv(x):
            return x["conversation"] if isinstance(x, dict) else x

        ceid_deltas, drift_agree = [], []
        for sample in test_data:
            conv = _conv(sample)
            o_ceid = original.measure_ceid(conv)
            q_ceid = self._q_measure_ceid(quantized, conv)
            ceid_deltas.append(np.mean([abs(o_ceid[a] - q_ceid[a]) for a in ("C", "E", "I", "D")]))
            drift_agree.append(bool(original.detect_drift(conv)["drift"]) ==
                               bool(self._q_detect_drift(quantized, conv)["drift"]))

        ceid_mae = float(np.mean(ceid_deltas)) if ceid_deltas else 0.0
        drift_acc_delta = 1.0 - (float(np.mean(drift_agree)) if drift_agree else 1.0)
        warnings = []
        if ceid_mae >= self.ceid_tol:
            warnings.append(f"CEID MAE {ceid_mae:.4f} ≥ tolerance {self.ceid_tol}")
        if drift_acc_delta >= self.drift_tol:
            warnings.append(f"drift accuracy drop {drift_acc_delta:.4f} ≥ tolerance {self.drift_tol}")
        return {"ceid_mae": round(ceid_mae, 4), "drift_acc_delta": round(drift_acc_delta, 4),
                "passed": not warnings, "warnings": warnings}

    # The quantized container is a QuantizedModel; in a full implementation a dequantizing
    # forward (or an INT4 kernel) backs these. Kept as documented hooks for the GPU path.
    def _q_measure_ceid(self, quantized, conversation):
        if hasattr(quantized, "measure_ceid"):
            return quantized.measure_ceid(conversation)
        raise NotImplementedError("wrap the QuantizedModel in a dequantizing forward to score CEID")

    def _q_detect_drift(self, quantized, conversation):
        if hasattr(quantized, "detect_drift"):
            return quantized.detect_drift(conversation)
        raise NotImplementedError("wrap the QuantizedModel in a dequantizing forward to detect drift")
