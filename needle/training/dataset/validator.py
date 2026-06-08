"""DatasetValidator — quality control for the generated CEID dataset."""

from __future__ import annotations

import json
import math
from pathlib import Path

_CEID_AXES = ("C", "E", "I", "D")


class DatasetValidator:
    def __init__(self, confidence_threshold: float = 0.7):
        self.confidence_threshold = confidence_threshold

    def validate_ceid_sample(self, sample: dict) -> bool:
        labels = sample.get("ceid_labels", {})
        if not all(a in labels and 0.0 <= labels[a] <= 1.0 for a in _CEID_AXES):
            return False
        if sample.get("confidence", 0.0) < self.confidence_threshold:
            return False
        kv = sample.get("k_layer_vector")
        if kv is None or len(kv) == 0 or any(v is None or math.isnan(float(v)) for v in kv):
            return False
        return True

    def validate_dataset(self, path: str) -> dict:
        total = valid = 0
        confs = []
        for line in Path(path).read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            total += 1
            s = json.loads(line)
            confs.append(s.get("confidence", 0.0))
            if self.validate_ceid_sample(s):
                valid += 1
        buckets = {"<0.7": sum(c < 0.7 for c in confs),
                   "0.7-0.9": sum(0.7 <= c < 0.9 for c in confs),
                   ">=0.9": sum(c >= 0.9 for c in confs)}
        return {"total": total, "valid": valid, "rejected": total - valid,
                "confidence_distribution": buckets}

    def filter_low_confidence(self, dataset: list[dict], threshold: float = None) -> list[dict]:
        th = self.confidence_threshold if threshold is None else threshold
        return [s for s in dataset if s.get("confidence", 0.0) >= th]
