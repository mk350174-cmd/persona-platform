"""Security headers middleware for OWASP compliance."""

from fastapi import Request
from fastapi.responses import Response


class SecurityHeadersMiddleware:
    """Add security headers to all HTTP responses."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, request: Request, call_next):
        response = await call_next(request)

        # Prevent MIME type sniffing (blocks IE from interpreting files as different MIME types)
        response.headers["X-Content-Type-Options"] = "nosniff"

        # Prevent clickjacking attacks
        response.headers["X-Frame-Options"] = "DENY"

        # Legacy XSS protection header (for older browsers)
        response.headers["X-XSS-Protection"] = "1; mode=block"

        # Control how much referer information is sent (prevent credential leakage)
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # Enforce HTTPS and block HTTP (with 1-year HSTS preload)
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"

        # Content Security Policy: only load resources from same origin
        # Allow unsafe-inline for styles/scripts only if absolutely necessary (consider removing in production)
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: https:; "
            "font-src 'self'; "
            "connect-src 'self'; "
            "frame-ancestors 'none'; "
            "base-uri 'self'; "
            "form-action 'self'"
        )

        # Prevent embedding in iframes
        response.headers["X-Frame-Options"] = "DENY"

        # Additional security: deny permissions for sensitive features
        response.headers["Permissions-Policy"] = (
            "camera=(), "
            "microphone=(), "
            "geolocation=(), "
            "payment=(), "
            "usb=(), "
            "magnetometer=(), "
            "gyroscope=(), "
            "accelerometer=()"
        )

        return response
