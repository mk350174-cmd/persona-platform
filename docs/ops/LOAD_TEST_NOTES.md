# Load Testing (T2-050)

**Tier: Ölçülmüş (measured)** — `scripts/load_test.py` is a real, runnable
HTTP load generator (asyncio + httpx, no Locust/k6 dependency). It has been
genuinely executed against a real local `uvicorn api.main:app` process,
not simulated.

`docs/ops/load_test_baseline_2026-07-31.json` is the actual output of that
run: 200 requests, concurrency 20, against `/health` and `/personas/` on
this sandbox's single CPU core with SQLite. 0 errors, p50 ≈ 63ms,
p95 ≈ 181ms, p99 ≈ 266ms, ~228 req/s.

## What this number does and doesn't mean

- It reflects **this sandbox's hardware and SQLite**, single uvicorn
  worker, no reverse proxy, no real network — not a production capacity
  estimate. Once a real deploy target exists (PostgreSQL, multiple
  workers, real network path), re-run this and replace the baseline file;
  don't reuse this number as a production SLA.
- It only exercises unauthenticated GET endpoints. Auth (`/auth/login`,
  Argon2 hashing) and the WebSocket chat path are deliberately excluded —
  Argon2 is intentionally slow (that's the point of a password hash), so
  mixing it into a raw-throughput number would be misleading without
  separating the two costs. A follow-up run should measure them
  separately if login throughput becomes a real concern.
- No previous "load_test_results.json" in this repo should be trusted —
  the one that existed before this pass (June 2026, referencing branch
  `claude/bold-bell-u0tvn5`, `tests/load_test_payments.py`, and Locust
  scenarios) referenced files and a branch that no longer exist in this
  repo. It was a leftover from a deleted subsystem and has been removed
  along with the other fabricated-status files from that era
  (`INTEGRATION_READY.txt`, `MERGE_HANDOFF_SUMMARY.txt`,
  `.INFRASTRUCTURE_MANIFEST.json`, and related validation-results JSON
  files) — see `AUDIT_FINDINGS.md` (AF-102, Persona repo) for the record.

## Reproducing

```bash
uvicorn api.main:app --host 127.0.0.1 --port 8000 &
python3 scripts/load_test.py --base-url http://127.0.0.1:8000 \
    --concurrency 20 --requests 200 --out docs/ops/load_test_baseline_<date>.json
```
