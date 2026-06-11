"""Per-API-key rate limiting middleware."""

from datetime import datetime, timedelta, timezone
from typing import Optional

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from fastapi import HTTPException, status

# In-memory rate limit tracking
# {api_key_prefix: {endpoint: {remaining: int, reset_at: datetime}}}
_rate_limit_state = {}

# Default quotas per endpoint (requests per hour)
ENDPOINT_QUOTAS = {
    "/health": 100,
    "/personas": 100,
    "/auth/register": 5,
    "/auth/login": 10,
    "/auth/verify-email": 10,
    "/auth/request-verification": 3,
    "/checkout": 20,
    "/v1/compile": 100,
    "/v1/compile/all-platforms": 50,
    "/v1/compile/all-tiers": 50,
    "/v1/compile/voice": 30,
    "/me": 100,
    "/me/purchases": 100,
    "/me/api-keys": 100,
    "/me/api-keys/rotate": 5,
}

DEFAULT_QUOTA = 1000  # fallback


def _extract_key_prefix(request: Request) -> Optional[str]:
    """Extract API key prefix (first 8 chars) from request for rate limiting."""
    auth_header = request.headers.get("authorization", "")
    if auth_header.startswith("Bearer prs_"):
        return auth_header.split()[1][:8]

    api_key = request.headers.get("x-api-key", "")
    if api_key.startswith("prs_"):
        return api_key[:8]

    return None


def _get_reset_time():
    """Get the next hour boundary (reset time for rate limit counter)."""
    now = datetime.now(timezone.utc)
    return now.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Per-API-key + per-endpoint rate limiting."""

    async def dispatch(self, request: Request, call_next):
        # Public endpoints: skip rate limiting
        if request.url.path in {"/health", "/personas", "/docs", "/redoc"}:
            return await call_next(request)

        # Extract API key prefix
        key_prefix = _extract_key_prefix(request)

        # No API key: skip (will be caught by auth layer)
        if not key_prefix:
            return await call_next(request)

        # Get quota for this endpoint
        endpoint = request.url.path.split("?")[0]  # Remove query params
        quota = ENDPOINT_QUOTAS.get(endpoint, DEFAULT_QUOTA)

        # Check rate limit
        now = datetime.now(timezone.utc)
        if key_prefix not in _rate_limit_state:
            _rate_limit_state[key_prefix] = {}

        endpoint_state = _rate_limit_state[key_prefix].get(endpoint)

        if endpoint_state is None:
            # First request: initialize
            endpoint_state = {"remaining": quota - 1, "reset_at": _get_reset_time()}
            _rate_limit_state[key_prefix][endpoint] = endpoint_state
        elif now >= endpoint_state["reset_at"]:
            # Hour boundary crossed: reset
            endpoint_state["remaining"] = quota - 1
            endpoint_state["reset_at"] = _get_reset_time()
        elif endpoint_state["remaining"] <= 0:
            # Rate limit exceeded
            reset_at = endpoint_state["reset_at"]
            seconds_until_reset = (reset_at - now).total_seconds()
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Rate limit exceeded for this endpoint. Resets in {seconds_until_reset:.0f}s.",
                headers={"Retry-After": str(int(seconds_until_reset))},
            )
        else:
            # Decrement remaining
            endpoint_state["remaining"] -= 1

        response = await call_next(request)

        # Add rate limit headers to response
        reset_at = endpoint_state["reset_at"]
        response.headers["X-RateLimit-Limit"] = str(quota)
        response.headers["X-RateLimit-Remaining"] = str(max(0, endpoint_state["remaining"]))
        response.headers["X-RateLimit-Reset"] = str(int(reset_at.timestamp()))

        return response
