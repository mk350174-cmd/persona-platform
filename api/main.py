from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .db import init_db
from .routers import auth_router, persona_router, payments_router

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

# CORS: explicit allowlist, no wildcard (security-hardening pattern from
# the old api/, re-verified rather than copied — ADR 0001 T2-004).
_cors_origins = ["http://localhost:3000", "http://localhost:5173"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["Authorization", "Content-Type"],
)

app.include_router(auth_router.router)
app.include_router(persona_router.router)
app.include_router(payments_router.router)


@app.get("/health")
def health():
    return {"status": "ok"}
