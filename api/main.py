from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from .db import init_db
from .rate_limit import limiter
from .routers import apikey_router, auth_router, persona_router, payments_router

# Called eagerly at import time as well as via lifespan: TestClient only
# fires ASGI lifespan events when used as a context manager
# (`with TestClient(app) as c:`), and a bare `TestClient(app)` in a pytest
# fixture or ad-hoc script would silently skip table creation otherwise.
init_db()


@asynccontextmanager
async def _lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(
    title="Persona Platform API",
    description="Rebuilt web/app layer (ADR 0001) — auth, persona catalog, "
                "CEID measurement, WebSocket chat (transport-only), test-mode payments.",
    version="0.1.0",
    lifespan=_lifespan,
)

# Rate limiting (T2-011) — per-client-IP token bucket via slowapi. Auth
# endpoints carry stricter per-route limits (see auth_router.py); this
# registers the shared limiter + 429 handler + request-state middleware.
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

# CORS: explicit allowlist, no wildcard (security-hardening pattern from
# the old api/, re-verified rather than copied — ADR 0001 T2-004).
_cors_origins = ["http://localhost:3000", "http://localhost:5173"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)

app.include_router(auth_router.router)
app.include_router(apikey_router.router)
app.include_router(persona_router.router)
app.include_router(payments_router.router)


@app.get("/health")
def health():
    return {"status": "ok"}
