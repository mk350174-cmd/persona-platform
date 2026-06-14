"""Custom exception handlers for security and error management."""

import logging
from fastapi import Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from sqlalchemy.exc import SQLAlchemyError

logger = logging.getLogger("persona_hub")


def _request_meta(request) -> tuple[str, str, str]:
    """Safely extract (method, path, request_id) for both HTTP and WebSocket scopes.

    WebSocket connections pass a ``WebSocket`` object which has no ``.method``, so we
    fall back to the ASGI scope to avoid masking the original error with an AttributeError.
    """
    method = getattr(request, "method", None) or request.scope.get("type", "request").upper()
    path = request.url.path if getattr(request, "url", None) else request.scope.get("path", "")
    request_id = request.headers.get("X-Request-ID", "unknown")
    return method, path, request_id


async def generic_exception_handler(request: Request, exc: Exception):
    """Handle unexpected exceptions with generic error message."""
    method, path, request_id = _request_meta(request)
    logger.error(
        f"Unhandled exception in {method} {path}",
        exc_info=True,
        extra={"request_id": request_id},
    )
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error. Please contact support.",
            "request_id": request_id,
        },
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle Pydantic validation errors with generic message."""
    method, path, request_id = _request_meta(request)
    logger.warning(
        f"Validation error in {method} {path}: {len(exc.errors())} errors",
        extra={"request_id": request_id},
    )
    return JSONResponse(
        status_code=422,
        content={
            "error": "Invalid request data.",
            "request_id": request_id,
        },
    )


async def database_exception_handler(request: Request, exc: SQLAlchemyError):
    """Handle database errors with generic message."""
    method, path, request_id = _request_meta(request)
    logger.error(
        f"Database error in {method} {path}",
        exc_info=True,
        extra={"request_id": request_id},
    )
    return JSONResponse(
        status_code=500,
        content={
            "error": "Database operation failed. Please contact support.",
            "request_id": request_id,
        },
    )


async def value_error_handler(request: Request, exc: ValueError):
    """Handle value errors with generic message."""
    method, path, request_id = _request_meta(request)
    logger.warning(
        f"Value error in {method} {path}: {str(exc)[:100]}",
        extra={"request_id": request_id},
    )
    return JSONResponse(
        status_code=400,
        content={
            "error": "Invalid value provided.",
            "request_id": request_id,
        },
    )
