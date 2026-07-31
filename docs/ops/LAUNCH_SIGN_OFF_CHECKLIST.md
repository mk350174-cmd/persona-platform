# Launch Sign-Off Checklist — persona-platform API

**Status: 0/10 signed off.** This is not a completed checklist dressed up
as one — nobody has signed anything yet, because there is no launch date
and most items below depend on decisions/accounts that don't exist yet
(see the `blocked-business` rows in `GELISTIRME_GOREV_TAKIP.md`, T2-057/
059-061). Update the status column with a real name and date when an item
is actually signed off — never mark `✅` speculatively.

| # | Item | Owner role | Status | Signed by | Date |
|---|---|---|---|---|---|
| 1 | Backend test suite green (`pytest tests/`) | Engineering | ✅ done (55/55, 2026-07-31) | — | 2026-07-31 |
| 2 | CI pipeline green on `main` | Engineering | ⬜ not verified against `main` yet | | |
| 3 | ToS / Privacy Policy reviewed by a real lawyer | Legal | ⬜ blocked (T2-051) | | |
| 4 | Security audit complete | Security | ⬜ blocked (T2-060) | | |
| 5 | Real Stripe live keys configured + `STRIPE_ALLOW_LIVE=1` set deliberately | Engineering | ⬜ blocked (T2-021/023 — no live account) | | |
| 6 | Backup schedule running against real infra | Engineering | ⬜ blocked (no real deploy target, T2-044/048/049) | | |
| 7 | Rollback mechanism tested against real deploy target | Engineering | ⬜ tested locally only (`docs/ops/ROLLBACK.md`), not against real infra | | |
| 8 | Load test run against real deploy target | Engineering | ⬜ sandbox baseline only (`docs/ops/load_test_baseline_2026-07-31.json`), not representative of production | | |
| 9 | Launch date + contacts filled into `LAUNCH_DAY_RUNBOOK.md` | Business | ⬜ blocked (T2-057) | | |
| 10 | Final go/no-go call | Business owner | ⬜ blocked (depends on 1-9) | | |

**Do not backfill this table with fabricated approvals.** If a future
session finds most of this still unchecked, that's the honest state —
report it as such rather than marking items done to make progress look
further along than it is.
