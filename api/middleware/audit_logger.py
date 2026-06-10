"""Audit logging middleware for security events."""

import logging
import json
from fastapi import Request
from typing import Optional

logger = logging.getLogger("persona_hub.audit")


def extract_user_id(request: Request) -> Optional[str]:
    """Extract user ID from request (if available from auth middleware)."""
    # Can be set by auth middleware or retrieved from database
    return getattr(request.state, "user_id", None)


def extract_resource_id(request: Request) -> Optional[str]:
    """Extract resource ID from URL path."""
    path_params = getattr(request.scope, "path_params", {})
    return path_params.get("persona_id") or path_params.get("id")


class AuditLoggerMiddleware:
    """Log security-relevant events (auth failures, access denied, rate limit, etc.)."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, request: Request, call_next):
        response = await call_next(request)

        # Extract request context
        user_id = extract_user_id(request)
        resource_id = extract_resource_id(request)
        client_ip = request.client.host if request.client else "unknown"
        request_id = request.headers.get("X-Request-ID", "unknown")
        method = request.method
        path = request.url.path

        # Log security events
        if response.status_code == 401:  # Unauthorized
            logger.warning(
                "auth_failure",
                extra={
                    "request_id": request_id,
                    "user_id": user_id,
                    "endpoint": path,
                    "method": method,
                    "client_ip": client_ip,
                },
            )
        elif response.status_code == 403:  # Forbidden / Access Denied
            logger.warning(
                "access_denied",
                extra={
                    "request_id": request_id,
                    "user_id": user_id,
                    "endpoint": path,
                    "resource_id": resource_id,
                    "method": method,
                    "client_ip": client_ip,
                },
            )
        elif response.status_code == 429:  # Rate Limit Exceeded
            logger.warning(
                "rate_limit_exceeded",
                extra={
                    "request_id": request_id,
                    "user_id": user_id,
                    "endpoint": path,
                    "method": method,
                    "client_ip": client_ip,
                },
            )
        elif response.status_code == 413:  # Payload Too Large
            logger.warning(
                "request_size_limit_exceeded",
                extra={
                    "request_id": request_id,
                    "user_id": user_id,
                    "endpoint": path,
                    "method": method,
                    "client_ip": client_ip,
                    "content_length": request.headers.get("content-length", "unknown"),
                },
            )
        elif response.status_code >= 500:  # Server Error
            logger.error(
                "server_error",
                extra={
                    "request_id": request_id,
                    "user_id": user_id,
                    "endpoint": path,
                    "method": method,
                    "status_code": response.status_code,
                    "client_ip": client_ip,
                },
            )

        return response
