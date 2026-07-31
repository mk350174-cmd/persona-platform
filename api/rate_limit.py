"""Shared slowapi Limiter instance (T2-011). Separate module so routers can
import it for per-route decorators without a circular import on api.main."""
from __future__ import annotations

from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
