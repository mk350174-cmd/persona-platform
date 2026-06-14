"""
Tests to improve coverage for api/exceptions.py.

Targets missed lines:
  26-32  → generic_exception_handler body (logging + JSONResponse)
  76-81  → value_error_handler body (logging + JSONResponse)

Also tests WebSocket scope detection in _request_meta (lines 18-19).
"""

import os
import pytest
import logging
from unittest.mock import AsyncMock, MagicMock, patch

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("STRIPE_SECRET_KEY", "sk_test_mock")

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from sqlalchemy.exc import SQLAlchemyError


# ── Helper: build a minimal mock Request ──────────────────────────────────────

def _make_http_request(path: str = "/test", method: str = "GET", request_id: str = "req-123"):
    """Create a minimal mock HTTP request."""
    req = MagicMock(spec=Request)
    req.method = method
    req.url = MagicMock()
    req.url.path = path
    req.headers = {"X-Request-ID": request_id}
    req.scope = {"type": "http", "path": path}
    return req


def _make_websocket_request(path: str = "/ws"):
    """
    Create a mock WebSocket-like request.
    WebSocket objects have no .method attribute; _request_meta falls back to scope.
    """
    req = MagicMock()
    # Remove method attribute to simulate WebSocket object
    del req.method
    req.url = MagicMock()
    req.url.path = path
    req.headers = {"X-Request-ID": "ws-req-456"}
    req.scope = {"type": "websocket", "path": path}
    return req


# ── _request_meta helper ──────────────────────────────────────────────────────

class TestRequestMeta:
    """Test the _request_meta helper for HTTP and WebSocket contexts."""

    def test_http_request_extracts_method_and_path(self):
        from api.exceptions import _request_meta
        req = _make_http_request("/some/path", method="POST", request_id="id-001")
        method, path, request_id = _request_meta(req)
        assert method == "POST"
        assert path == "/some/path"
        assert request_id == "id-001"

    def test_missing_request_id_defaults_to_unknown(self):
        from api.exceptions import _request_meta
        req = MagicMock(spec=Request)
        req.method = "GET"
        req.url = MagicMock()
        req.url.path = "/test"
        req.headers = {}  # no X-Request-ID
        req.scope = {"type": "http", "path": "/test"}
        method, path, request_id = _request_meta(req)
        assert request_id == "unknown"

    def test_websocket_request_uses_scope_type(self):
        """WebSocket objects have no .method; should fall back to scope['type'].upper()."""
        from api.exceptions import _request_meta

        # Use a plain object rather than MagicMock so getattr returns None
        class FakeWS:
            url = MagicMock()
            headers = {"X-Request-ID": "ws-999"}
            scope = {"type": "websocket", "path": "/ws"}

        FakeWS.url.path = "/ws"
        req = FakeWS()
        # No 'method' attribute on instance or class → getattr returns None

        method, path, request_id = _request_meta(req)
        assert method == "WEBSOCKET"
        assert path == "/ws"
        assert request_id == "ws-999"

    def test_websocket_no_url_attr_uses_scope_path(self):
        """WebSocket with url=None uses scope path."""
        from api.exceptions import _request_meta

        class FakeWSNoUrl:
            url = None
            headers = {"X-Request-ID": "ws-no-url"}
            scope = {"type": "websocket", "path": "/ws/chat"}

        method, path, request_id = _request_meta(FakeWSNoUrl())
        assert path == "/ws/chat"


# ── generic_exception_handler (lines 26-32) ───────────────────────────────────

class TestGenericExceptionHandler:
    """Test the catch-all 500 handler."""

    @pytest.mark.asyncio
    async def test_returns_500_json_response(self):
        from api.exceptions import generic_exception_handler
        req = _make_http_request("/boom", method="DELETE", request_id="err-007")
        exc = RuntimeError("something broke")

        response = await generic_exception_handler(req, exc)
        assert response.status_code == 500
        import json
        body = json.loads(response.body)
        assert body["error"] == "Internal server error. Please contact support."
        assert body["request_id"] == "err-007"

    @pytest.mark.asyncio
    async def test_logs_error(self, caplog):
        from api.exceptions import generic_exception_handler
        req = _make_http_request("/crash", method="GET", request_id="log-001")
        exc = ValueError("crash!")

        with caplog.at_level(logging.ERROR, logger="persona_hub"):
            await generic_exception_handler(req, exc)

        # At least one error-level record with the path
        assert any("crash" in r.message.lower() or "/crash" in r.message for r in caplog.records)


# ── validation_exception_handler (lines 41-54) ────────────────────────────────

class TestValidationExceptionHandler:
    """Test Pydantic validation error handler."""

    @pytest.mark.asyncio
    async def test_returns_422_with_generic_error(self):
        from api.exceptions import validation_exception_handler
        req = _make_http_request("/data", method="POST", request_id="val-001")

        # Build a minimal RequestValidationError
        from pydantic import ValidationError
        from pydantic import BaseModel

        class _M(BaseModel):
            x: int

        try:
            _M(x="not_an_int")  # type: ignore
        except ValidationError as pydantic_err:
            exc = RequestValidationError(errors=pydantic_err.errors())

        response = await validation_exception_handler(req, exc)
        assert response.status_code == 422
        import json
        body = json.loads(response.body)
        assert body["error"] == "Invalid request data."
        assert body["request_id"] == "val-001"


# ── database_exception_handler (lines 57-71) ─────────────────────────────────

class TestDatabaseExceptionHandler:
    """Test SQLAlchemy error handler."""

    @pytest.mark.asyncio
    async def test_returns_500_for_db_error(self):
        from api.exceptions import database_exception_handler
        req = _make_http_request("/db_op", method="POST", request_id="db-001")
        exc = SQLAlchemyError("connection failed")

        response = await database_exception_handler(req, exc)
        assert response.status_code == 500
        import json
        body = json.loads(response.body)
        assert "database" in body["error"].lower()
        assert body["request_id"] == "db-001"

    @pytest.mark.asyncio
    async def test_logs_db_error(self, caplog):
        from api.exceptions import database_exception_handler
        req = _make_http_request("/db_fail")
        exc = SQLAlchemyError("timeout")

        with caplog.at_level(logging.ERROR, logger="persona_hub"):
            await database_exception_handler(req, exc)

        assert any("database" in r.message.lower() for r in caplog.records)


# ── value_error_handler (lines 76-81) ────────────────────────────────────────

class TestValueErrorHandler:
    """Test ValueError handler."""

    @pytest.mark.asyncio
    async def test_returns_400_for_value_error(self):
        from api.exceptions import value_error_handler
        req = _make_http_request("/bad_value", method="PUT", request_id="ve-001")
        exc = ValueError("something is wrong with the value")

        response = await value_error_handler(req, exc)
        assert response.status_code == 400
        import json
        body = json.loads(response.body)
        assert body["error"] == "Invalid value provided."
        assert body["request_id"] == "ve-001"

    @pytest.mark.asyncio
    async def test_logs_value_error(self, caplog):
        from api.exceptions import value_error_handler
        req = _make_http_request("/value_path", method="GET", request_id="ve-log")
        exc = ValueError("bad_value")

        with caplog.at_level(logging.WARNING, logger="persona_hub"):
            await value_error_handler(req, exc)

        assert any("value" in r.message.lower() for r in caplog.records)

    @pytest.mark.asyncio
    async def test_value_error_truncates_long_message(self):
        """value_error_handler truncates exc message to 100 chars in log."""
        from api.exceptions import value_error_handler
        req = _make_http_request("/long_value")
        long_message = "x" * 200
        exc = ValueError(long_message)

        # Should not raise even with long messages
        response = await value_error_handler(req, exc)
        assert response.status_code == 400


# ── WebSocket scope via HTTP integration (optional smoke test) ────────────────

class TestWebsocketScopeViaIntegration:
    """Test that exception handlers survive when called from a WS-like context."""

    @pytest.mark.asyncio
    async def test_generic_handler_with_websocket_scope(self):
        from api.exceptions import generic_exception_handler

        class FakeWS:
            url = MagicMock()
            headers = {"X-Request-ID": "ws-exc-001"}
            scope = {"type": "websocket", "path": "/ws/test"}

        FakeWS.url.path = "/ws/test"

        exc = RuntimeError("ws error")
        response = await generic_exception_handler(FakeWS(), exc)
        assert response.status_code == 500

    @pytest.mark.asyncio
    async def test_value_error_handler_with_websocket_scope(self):
        from api.exceptions import value_error_handler

        class FakeWSBad:
            url = MagicMock()
            headers = {}
            scope = {"type": "websocket", "path": "/ws/bad"}

        FakeWSBad.url.path = "/ws/bad"

        exc = ValueError("ws value error")
        response = await value_error_handler(FakeWSBad(), exc)
        assert response.status_code == 400
