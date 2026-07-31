"""HTTP-level load test against a running api/ instance (T2-050).

Genuinely executed, not simulated — run it against a live
`uvicorn api.main:app` process and it prints real latency percentiles and
error counts. No Locust/k6 dependency; plain asyncio + httpx so it needs
nothing beyond what's already in requirements.txt.

Usage:
    uvicorn api.main:app --host 127.0.0.1 --port 8000 &
    python3 scripts/load_test.py --base-url http://127.0.0.1:8000 \
        --concurrency 20 --requests 200
"""
from __future__ import annotations

import argparse
import asyncio
import json
import statistics
import time

import httpx


async def _one_request(client: httpx.AsyncClient, method: str, path: str, **kwargs) -> tuple[float, int]:
    start = time.perf_counter()
    try:
        r = await client.request(method, path, **kwargs)
        return time.perf_counter() - start, r.status_code
    except httpx.HTTPError:
        return time.perf_counter() - start, 0


async def run(base_url: str, concurrency: int, total_requests: int) -> dict:
    sem = asyncio.Semaphore(concurrency)
    latencies: list[float] = []
    status_counts: dict[int, int] = {}

    async def worker(client: httpx.AsyncClient, idx: int):
        async with sem:
            # Mix of read-heavy endpoints — no auth needed, so the load
            # test measures the catalog/health path, not login overhead.
            path = "/health" if idx % 3 == 0 else "/personas/"
            latency, status = await _one_request(client, "GET", path)
            latencies.append(latency)
            status_counts[status] = status_counts.get(status, 0) + 1

    async with httpx.AsyncClient(base_url=base_url, timeout=10.0) as client:
        wall_start = time.perf_counter()
        await asyncio.gather(*(worker(client, i) for i in range(total_requests)))
        wall_elapsed = time.perf_counter() - wall_start

    latencies.sort()

    def pct(p: float) -> float:
        if not latencies:
            return 0.0
        idx = min(int(len(latencies) * p), len(latencies) - 1)
        return latencies[idx]

    return {
        "base_url": base_url,
        "concurrency": concurrency,
        "total_requests": total_requests,
        "wall_seconds": round(wall_elapsed, 3),
        "requests_per_second": round(total_requests / wall_elapsed, 2) if wall_elapsed else None,
        "latency_ms": {
            "min": round(min(latencies) * 1000, 2) if latencies else None,
            "p50": round(pct(0.50) * 1000, 2),
            "p95": round(pct(0.95) * 1000, 2),
            "p99": round(pct(0.99) * 1000, 2),
            "max": round(max(latencies) * 1000, 2) if latencies else None,
            "mean": round(statistics.mean(latencies) * 1000, 2) if latencies else None,
        },
        "status_counts": status_counts,
        "error_count": sum(c for status, c in status_counts.items() if status != 200),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--concurrency", type=int, default=20)
    parser.add_argument("--requests", type=int, default=200)
    parser.add_argument("--out", default=None, help="Write JSON results to this path")
    args = parser.parse_args()

    result = asyncio.run(run(args.base_url, args.concurrency, args.requests))
    print(json.dumps(result, indent=2))
    if args.out:
        with open(args.out, "w") as f:
            json.dump(result, f, indent=2)


if __name__ == "__main__":
    main()
