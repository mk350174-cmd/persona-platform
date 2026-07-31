# Deploy Rollback — persona-platform API

**Status: mechanism designed and tested against a local process; not yet
exercised against any real deploy target**, because none exists yet
(T2-044/048/049 — staging/canary/production infra are the user's business
decisions to make, not something to fabricate here).

## What exists

`scripts/post_deploy_health_check.sh` — polls a health endpoint (default
`/health`) after a deploy for `MAX_RETRIES` attempts; if it never returns
healthy, runs `$ROLLBACK_CMD` and exits non-zero. Verified in this sandbox:
- Healthy case: a real `uvicorn api.main:app` process, script exits 0 on
  the first successful check.
- Unhealthy case: pointed at a port nothing is listening on, script
  retries the configured number of times, then actually invokes
  `$ROLLBACK_CMD` (confirmed via a marker file the command touches) and
  exits 1.

## What `$ROLLBACK_CMD` should be, once real infra exists

This script deliberately does not implement a rollback itself — "roll
back" means something different depending on the deploy target:

- Kubernetes: `kubectl rollout undo deployment/persona-platform-api`
- Docker Swarm: `docker service update --rollback persona-platform-api`
- A load balancer pointed at tagged images: a script that re-points it at
  the previous tag
- A simple single-host systemd setup: `systemctl start persona-platform-api@<previous-version>`

Whichever of these applies once a real environment is chosen, set
`ROLLBACK_CMD` to it in the CI/CD pipeline step that calls this script
after a deploy.

## Wiring into CI/CD

Not yet added to `.github/workflows/ci.yml` — that workflow only runs
tests/lint on push, it does not deploy anywhere (there's nowhere to deploy
to yet). Once a real deploy target exists, add a post-deploy step:

```yaml
- name: Post-deploy health check (roll back on failure)
  env:
    HEALTH_URL: https://<real-deploy-host>/health
    ROLLBACK_CMD: <real rollback command for the chosen target>
  run: ./scripts/post_deploy_health_check.sh
```
