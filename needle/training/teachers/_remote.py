"""Shared helpers for remote (API) teachers: cache, rate-limit, retry, JSON parse."""

from __future__ import annotations

import hashlib
import json
import re
import threading
import time
from pathlib import Path
from typing import Callable

import numpy as np

_CACHE_DIR = Path(__file__).resolve().parent.parent / ".teacher_cache"


class RateLimiter:
    """Spaces requests ``min_interval = 60/rpm`` apart. Thread-safe: concurrent workers
    (e.g. the builder's ThreadPoolExecutor) serialize through the lock, so N threads still
    respect the per-teacher rate limit."""

    def __init__(self, rpm: int):
        self.min_interval = 60.0 / max(1, rpm)
        self._last = 0.0
        self._lock = threading.Lock()

    def wait(self):
        with self._lock:
            dt = time.monotonic() - self._last
            if dt < self.min_interval:
                time.sleep(self.min_interval - dt)
            self._last = time.monotonic()


class JsonCache:
    """On-disk response cache so a teacher is never asked the same thing twice."""

    def __init__(self, namespace: str, cache_dir: Path = _CACHE_DIR):
        self.dir = Path(cache_dir) / namespace
        self.dir.mkdir(parents=True, exist_ok=True)

    def _path(self, key: str) -> Path:
        return self.dir / (hashlib.sha256(key.encode("utf-8")).hexdigest()[:32] + ".json")

    def get(self, key: str):
        p = self._path(key)
        return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None

    def set(self, key: str, value) -> None:
        self._path(key).write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")


def retry(fn: Callable, tries: int = 3, base: float = 2.0):
    last = None
    for i in range(tries):
        try:
            return fn()
        except Exception as exc:  # noqa: BLE001
            last = exc
            if i < tries - 1:
                time.sleep(base ** (i + 1))   # 2s, 4s, 8s
    raise last


def extract_json(text: str) -> dict:
    """Pull the first {...} JSON object out of a model's text response."""
    m = re.search(r"\{.*\}", text, re.DOTALL)
    if not m:
        raise ValueError(f"no JSON object in response: {text[:120]!r}")
    return json.loads(m.group(0))


def clip01(x) -> float:
    return float(min(1.0, max(0.0, float(x))))


def k_layer_summary(persona_vector) -> str:
    """A short textual summary of a K-layer vector for the teacher prompts."""
    from persona_math.params import MANDATORY_CORE_INDICES
    if isinstance(persona_vector, dict):
        persona_vector = persona_vector.get("values", list(persona_vector.values()))
    P = np.asarray(persona_vector, dtype=float)
    core = list(MANDATORY_CORE_INDICES)
    top = np.argsort(P)[::-1][:5]
    return (f"mandatory-core(K1/K2/K4/K12) mean={P[core].mean():.2f}; "
            f"top layers={[f'K{int(i)+1}={P[i]:.2f}' for i in top]}")
