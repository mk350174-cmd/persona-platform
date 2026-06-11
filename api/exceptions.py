"""Custom exception handlers for security and error management."""

import logging
from fastapi import Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from sqlalchemy.exc import SQLAlchemyError

logger = logging.getLogger("persona_hub")


async def generic_exception_handler(request: Request, exc: Exception):
    """Handle unexpected exceptions with generic error message."""
    request_id = request.headers.get("X-Request-ID", "unknown")
    logger.error(
        f"Unhandled exception in {request.method} {request.url.path}",
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
    request_id = request.headers.get("X-Request-ID", "unknown")
    logger.warning(
        f"Validation error in {request.method} {request.url.path}: {len(exc.errors())} errors",
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
    request_id = request.headers.get("X-Request-ID", "unknown")
    logger.error(
        f"Database error in {request.method} {request.url.path}",
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
    request_id = request.headers.get("X-Request-ID", "unknown")
    logger.warning(
        f"Value error in {request.method} {request.url.path}: {str(exc)[:100]}",
        extra={"request_id": request_id},
    )
    return JSONResponse(
        status_code=400,
        content={
            "error": "Invalid value provided.",
            "request_id": request_id,
        },
    )
