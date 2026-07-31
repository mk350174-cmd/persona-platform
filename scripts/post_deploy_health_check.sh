#!/usr/bin/env bash
# Post-deploy health check + rollback trigger (T2-046).
#
# Polls a health endpoint after a deploy; if it never comes up healthy,
# runs $ROLLBACK_CMD (the actual rollback mechanism — e.g. "kubectl rollout
# undo ...", "docker service update --rollback ...", a script that re-points
# a load balancer at the previous image tag — whatever the real deploy
# target uses). This script only knows how to detect failure and delegate;
# it does not implement a rollback itself, since that's specific to
# infrastructure that doesn't exist yet in this repo (T2-044/048/049).
#
# Usage:
#   ROLLBACK_CMD="echo would-rollback-here" ./scripts/post_deploy_health_check.sh
set -euo pipefail

HEALTH_URL="${HEALTH_URL:-http://localhost:8000/health}"
MAX_RETRIES="${MAX_RETRIES:-10}"
RETRY_DELAY="${RETRY_DELAY:-3}"
ROLLBACK_CMD="${ROLLBACK_CMD:?ROLLBACK_CMD must be set to the real rollback command for this deploy target}"

for ((i = 1; i <= MAX_RETRIES; i++)); do
    if curl -sf -o /dev/null "$HEALTH_URL"; then
        echo "healthy after $i attempt(s): $HEALTH_URL"
        exit 0
    fi
    echo "attempt $i/$MAX_RETRIES: $HEALTH_URL not healthy yet, retrying in ${RETRY_DELAY}s"
    sleep "$RETRY_DELAY"
done

echo "deploy did not become healthy after $MAX_RETRIES attempts — rolling back" >&2
eval "$ROLLBACK_CMD"
exit 1
