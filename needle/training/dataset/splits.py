"""Stratified train/val/test split (per-persona) for a JSONL dataset."""

from __future__ import annotations

import json
import random
from collections import defaultdict
from pathlib import Path


def create_splits(dataset_path: str, train: float = 0.8, val: float = 0.1,
                  test: float = 0.1, seed: int = 42) -> dict:
    if abs((train + val + test) - 1.0) > 1e-6:
        raise ValueError("train+val+test must sum to 1.0")
    path = Path(dataset_path)
    rows = [json.loads(ln) for ln in path.read_text(encoding="utf-8").splitlines() if ln.strip()]

    by_persona = defaultdict(list)
    for r in rows:
        by_persona[r.get("persona_id", "_")].append(r)

    splits = {"train": [], "val": [], "test": []}
    rng = random.Random(seed)
    for pid, items in by_persona.items():
        items = items[:]
        rng.shuffle(items)
        n = len(items)
        n_tr = int(round(n * train))
        n_va = int(round(n * val))
        splits["train"] += items[:n_tr]
        splits["val"] += items[n_tr:n_tr + n_va]
        splits["test"] += items[n_tr + n_va:]

    out_dir = path.parent
    counts = {}
    for name, items in splits.items():
        with open(out_dir / f"{name}.jsonl", "w", encoding="utf-8") as f:
            for r in items:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
        counts[name] = len(items)
    counts["total"] = sum(counts[k] for k in ("train", "val", "test"))
    return counts
