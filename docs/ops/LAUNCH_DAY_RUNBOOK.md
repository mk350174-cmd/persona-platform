# Launch Day Runbook — persona-platform API

**Status: template, not an executed runbook.** No launch date has been set
(T2-057 — blocked-business, that's the user's call). Every bracketed field
below is genuinely `TBD` — this file does not pretend a launch has
happened or that contact info exists yet. Fill in the brackets once a real
launch date and team are set, then this stops being a template.

## Pre-launch checklist

- [ ] Launch date confirmed: `[TBD]`
- [ ] Deploy target chosen and provisioned (T2-044/048/049 — blocked-business)
- [ ] `DATABASE_URL` points at the real production Postgres, not the SQLite dev default
- [ ] `JWT_SECRET_KEY` set to a real random secret (not the `dev-only-insecure-secret-change-me` default in `api/security.py`)
- [ ] `STRIPE_SECRET_KEY` / `STRIPE_WEBHOOK_SECRET` set to real live keys, with `STRIPE_ALLOW_LIVE=1` explicitly set (see `api/routers/payments_router.py::_guard_live_key`)
- [ ] Backup schedule running (`scripts/db_backup.sh` — see `docs/ops/DISASTER_RECOVERY.md`; no schedule exists yet, needs a real host/cron)
- [ ] Rollback command configured for the real deploy target (`scripts/post_deploy_health_check.sh` — see `docs/ops/ROLLBACK.md`; `$ROLLBACK_CMD` is a placeholder until then)
- [ ] Load test re-run against the real deploy target, not just this sandbox's baseline (`docs/ops/LOAD_TEST_NOTES.md`)
- [ ] Legal review complete: ToS/Privacy Policy signed off by a real lawyer (T2-051 — blocked-business)
- [ ] Security audit complete (T2-060 — blocked-business)

## Contacts

| Role | Name | Phone | Notes |
|---|---|---|---|
| Deploy owner | `[TBD]` | `[TBD]` | |
| On-call engineer | `[TBD]` | `[TBD]` | |
| Business/legal sign-off | `[TBD]` | `[TBD]` | |

Incident channel: `[TBD — Slack/Discord/etc. link]`
Video bridge: `[TBD — Zoom/Meet URL, do not fabricate one]`

## Launch sequence

1. Freeze deploys to `main` an hour before the window.
2. Deploy to the real environment (target: `[TBD]`).
3. Run `scripts/post_deploy_health_check.sh` against the real health URL
   with the real `$ROLLBACK_CMD` for that target.
4. Smoke test manually: register, login, list personas, one CEID
   measurement, one test-mode checkout.
5. Monitor error rate for the first hour (once T2-028/029/030 monitoring
   is wired up — currently blocked-business, so this step is manual
   log-watching until then).
6. Announce launch in `[TBD channel]`.

## Rollback trigger

If step 3 or 4 fails: follow `docs/ops/ROLLBACK.md`. Do not attempt manual
hotfixes under launch-day time pressure — roll back first, fix calmly
afterward.

## Post-launch

- [ ] Sign-off checklist completed — see `docs/ops/LAUNCH_SIGN_OFF_CHECKLIST.md` (currently 0/N, honestly, since no launch has happened)
- [ ] This runbook updated with what actually happened, including anything that didn't go as planned
