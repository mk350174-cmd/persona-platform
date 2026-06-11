"""Audit logging middleware — security events written to DB and Python logger."""

import logging
from typing import Optional

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from api.db import SessionLocal, write_audit_log

logger = logging.getLogger("persona_hub.audit")


def extract_user_id(request: Request) -> Optional[str]:
    return getattr(request.state, "user_id", None)


def extract_resource_id(request: Request) -> Optional[str]:
    path_params = getattr(request.scope, "path_params", {})
    return path_params.get("persona_id") or path_params.get("id")


_AUDIT_STATUS_CODES = {401, 403, 429, 413}

_EVENT_TYPES = {
    401: "auth_failure",
    403: "access_denied",
    429: "rate_limit_exceeded",
    413: "request_size_limit_exceeded",
}


class AuditLoggerMiddleware(BaseHTTPMiddleware):
    """Log security-relevant HTTP events to Python logger and the audit_log DB table."""

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)

        status = response.status_code
        if status not in _AUDIT_STATUS_CODES and status < 500:
            return response

        user_id = extract_user_id(request)
        resource_id = extract_resource_id(request)
        client_ip = request.client.host if request.client else "unknown"
        request_id = request.headers.get("X-Request-ID", "unknown")
        method = request.method
        path = request.url.path

        event_type = _EVENT_TYPES.get(status, "server_error")

        extra = {
            "request_id": request_id,
            "user_id": user_id,
            "endpoint": path,
            "method": method,
            "client_ip": client_ip,
            "status_code": status,
        }
        if resource_id:
            extra["resource_id"] = resource_id

        if status >= 500:
            logger.error(event_type, extra=extra)
        else:
            logger.warning(event_type, extra=extra)

        # Persist to DB (non-blocking: swallow errors to avoid breaking the response)
        try:
            db = SessionLocal()
            write_audit_log(
                db,
                event_type=event_type,
                user_id=user_id,
                endpoint=path,
                method=method,
                status_code=status,
                resource_id=resource_id,
                client_ip=client_ip,
            )
        except Exception as exc:
            logger.warning("audit_log DB write failed: %s", exc)
        finally:
            db.close()

        return response
