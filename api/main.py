"""
Persona Compiler API — FastAPI application
==========================================
Endpoints (public):
  GET  /health
  GET  /personas
  GET  /personas/{id}
  POST /auth/register

Endpoints (requires X-API-Key):
  GET  /me
  GET  /me/purchases
  GET  /v1/personas/{id}/image         → portrait image (must own/purchase persona)
  POST /checkout/{persona_id}          → Stripe checkout URL
  POST /checkout/{persona_id}/mock     → dev-only instant grant
  POST /v1/compile/{id}                → compile (purchased personas only)
  POST /v1/compile/{id}/all-platforms
  POST /v1/compile/{id}/all-tiers
  POST /v1/compile/{id}/voice          → ElevenLabs MP3

Webhooks:
  POST /webhook/stripe

Run:
  uvicorn api.main:app --reload --port 8000

Env vars:
  STRIPE_SECRET_KEY      sk_test_... or sk_live_...
  STRIPE_WEBHOOK_SECRET  whsec_...
  BASE_URL               http://localhost:8000

See ASSET_MIGRATION.md for image URL migration guide (public → authenticated).
"""

from fastapi import FastAPI, HTTPException, Depends, Request, Header, WebSocket, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, Response
from fastapi.exceptions import RequestValidationError
from sqlalchemy.orm import Session
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from typing import Optional
from pathlib import Path
import asyncio
import logging
import time
import os
import stripe
import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
try:
    from posthog import Posthog
except ImportError:
    Posthog = None

from api.db import (
    init_db, get_db, create_user, get_user_by_email,
    create_email_verification_token, consume_verification_token,
    has_pending_verification, hash_password,
    User, log_usage, grant_free_persona, generate_referral_code,
    get_or_create_wallet, get_referral_code_by_code, BUNDLE_PRICING,
)
from api.auth import get_current_user, require_persona_access
from api.payments import (
    create_checkout_session, handle_webhook, mock_purchase,
    create_subscription_session,
)
from api.catalog import get_persona_vector, PERSONA_CATALOG
from persona_math.persona_library import search_personas, library_stats, PERSONA_LIBRARY
from api.db import check_quota, SUBSCRIPTION_TIERS, cancel_subscription, increment_request_count
from api.ws import persona_chat_ws
from api.voice import synthesize_speech, tts_available
from api.visual_params import get_visual_params
from api.routers.persona_router import router as persona_router
from api.routers.api_keys import router as api_keys_router
from api.routers.feature_flags import router as feature_flags_router
from api.routers.performance import router as performance_router
from api.routers.rollback import router as rollback_router
from api.routers.observability import router as observability_router
from api.routers.advanced_auth import router as advanced_auth_router
from api.routers.cache import router as cache_router
from api.routers.analytics import router as analytics_router
from api.routers.uploads import router as uploads_router
from persona_math.compiler import (
    compile_persona,
    compile_all_platforms,
    compile_all_tiers,
    SUPPORTED_PLATFORMS,
    SUPPORTED_TIERS,
)
from api.middleware.security_headers import SecurityHeadersMiddleware
from api.middleware.audit_logger import AuditLoggerMiddleware
from api.middleware.rate_limiter import RateLimitMiddleware
from api.exceptions import (
    generic_exception_handler,
    validation_exception_handler,
    database_exception_handler,
    value_error_handler,
)
from api.models import (
    RegisterRequest,
    LoginRequest,
    VerifyEmailRequest,
    RequestVerificationRequest,
    CompileRequest,
    AllPlatformsRequest,
    AllTiersRequest,
    VoiceRequest,
)
from api.email_service import send_verification_email
from api.auth import authenticate_password
from api.observability import (
    track_signup, track_checkout, track_compilation, set_posthog_client,
)

# ── Logging ───────────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger("persona_hub")

# ── Sentry Error Tracking ─────────────────────────────────────────────────────

sentry_dsn = os.getenv("SENTRY_DSN", "")
if sentry_dsn:
    sentry_sdk.init(
        dsn=sentry_dsn,
        integrations=[
            FastApiIntegration(),
            SqlalchemyIntegration(),
        ],
        traces_sample_rate=float(os.getenv("SENTRY_TRACES_SAMPLE_RATE", "0.1")),
        profiles_sample_rate=float(os.getenv("SENTRY_PROFILES_SAMPLE_RATE", "0.1")),
        environment=os.getenv("ENVIRONMENT", "development"),
        release=os.getenv("APP_VERSION", "1.0.0"),
        debug=os.getenv("ENVIRONMENT", "development") == "development",
    )

# ── PostHog Analytics ─────────────────────────────────────────────────────────

posthog_client = None
posthog_key = os.getenv("POSTHOG_API_KEY", "")
if posthog_key and Posthog:
    posthog_client = Posthog(
        api_key=posthog_key,
        host=os.getenv("POSTHOG_HOST", "https://eu.posthog.com"),
        debug=os.getenv("ENVIRONMENT", "development") == "development",
    )
    # Export to observability module
    set_posthog_client(posthog_client)

# ── Rate limiter ───────────────────────────────────────────────────────────────

limiter = Limiter(key_func=get_remote_address, default_limits=["1000/hour"])

# ── App init ───────────────────────────────────────────────────────────────────

# CORS configuration: default to restrictive list, require explicit env var for production
_CORS_DEFAULT = ""  # Empty string = no CORS (restrictive default)
_CORS_ORIGINS = [o.strip() for o in os.getenv("CORS_ORIGINS", _CORS_DEFAULT).split(",") if o.strip()]

app = FastAPI(
    title="Persona Compiler API",
    description="""
## Persona Compiler API

Production-ready AI persona marketplace. Purchase, compile, and interact with 495 historically-grounded AI personas.

### Authentication
All endpoints (except `/health`, `/personas`, `/auth/*`) require one of:
- **X-API-Key** header: `X-API-Key: prs_...`
- **Authorization** header: `Authorization: Bearer prs_...`
- **JWT Bearer** (OAuth2 flow): `Authorization: Bearer eyJ...`

### Rate Limits
- Default: 1000 requests/hour per API key
- `/v1/compile`: 100/hour
- `/ws/chat`: 30 messages/minute per connection

### Versioning
API is versioned at `/v1`. Deprecated endpoints return `Deprecation: true` header.
""",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_tags=[
        {"name": "system",      "description": "Health checks and system info"},
        {"name": "auth",        "description": "Registration, login, email verification"},
        {"name": "catalog",     "description": "Browse 495 AI personas"},
        {"name": "payments",    "description": "Stripe checkout and billing"},
        {"name": "compile",     "description": "Compile personas to platform-specific configs"},
        {"name": "rollback",    "description": "Automatic rollback and self-healing"},
        {"name": "observability","description": "Metrics, traces, and structured logs"},
        {"name": "feature-flags","description": "A/B testing and gradual rollouts"},
        {"name": "performance", "description": "Regression detection and baselines"},
        {"name": "cache",       "description": "Redis cache management"},
        {"name": "analytics",   "description": "Usage analytics and reporting"},
    ],
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Request body size limit middleware (prevent DoS via large payloads)
# Limit: 10 MB (matches nginx client_max_body_size)
@app.middleware("http")
async def limit_request_size(request: Request, call_next):
    """Limit request body size to prevent DoS attacks."""
    if request.method in ["POST", "PUT", "PATCH"]:
        content_length = request.headers.get("content-length", "0")
        try:
            size = int(content_length)
            if size > 10_000_000:  # 10 MB limit
                from fastapi.responses import JSONResponse
                return JSONResponse(
                    status_code=413,
                    content={"error": "Payload too large (max 10 MB)"},
                )
        except ValueError:
            pass  # Invalid content-length, let nginx handle it
    return await call_next(request)


# Per-API-key rate limiting middleware (before security headers to catch rate limit exceptions early)
app.add_middleware(RateLimitMiddleware)

# Audit logging middleware (logs security events)
app.add_middleware(AuditLoggerMiddleware)

# Security headers middleware (must be added BEFORE CORS to ensure headers are not overwritten)
app.add_middleware(SecurityHeadersMiddleware)

# CORS configuration: explicit origin list (no wildcards in production)
app.add_middleware(
    CORSMiddleware,
    allow_origins=_CORS_ORIGINS if _CORS_ORIGINS else ["localhost:3000", "localhost:8000"],
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["authorization", "content-type"],
)

# Register custom exception handlers (must be after app initialization)
app.add_exception_handler(Exception, generic_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(SQLAlchemyError, database_exception_handler)
app.add_exception_handler(ValueError, value_error_handler)

# Configure Stripe for payment processing
stripe.api_key = os.getenv("STRIPE_SECRET_KEY", "")

# PersonaNeedle endpoints (CEID / drift / voice / profile / history) — see api/routers/persona_router.py
app.include_router(persona_router, prefix="/api/v1")

# API Key management endpoints (rotation, revocation, list) — see api/routers/api_keys.py
app.include_router(api_keys_router)

# Feature Flags endpoints (A/B testing, rollouts, targeting) — see api/routers/feature_flags.py
app.include_router(feature_flags_router)

# Performance Monitoring endpoints (metrics, regression detection) — see api/routers/performance.py
app.include_router(performance_router)

# Rollback Management endpoints (automatic rollback, self-healing) — see api/routers/rollback.py
app.include_router(rollback_router)

# Observability & Monitoring endpoints (metrics, traces, logs) — see api/routers/observability.py
app.include_router(observability_router)

# Analytics & Reporting endpoints (dashboard, revenue, DAU, cohort retention) — see api/routers/analytics.py
app.include_router(analytics_router)

# Advanced Authentication endpoints (OAuth2, JWT, RBAC, sessions) — see api/routers/advanced_auth.py
app.include_router(advanced_auth_router)

# Cache Management endpoints (Redis stats, flush, health) — see api/routers/cache.py
app.include_router(cache_router)

# File Upload endpoints (avatars, compiled configs) — see api/routers/uploads.py
app.include_router(uploads_router)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    start = time.time()
    response = await call_next(request)
    ms = round((time.time() - start) * 1000)
    logger.info("%s %s %s %dms", request.method, request.url.path, response.status_code, ms)
    return response


_AUDIO_CACHE_DIR = Path("/tmp/persona_audio")
_AUDIO_MAX_AGE_HOURS = 24


async def _audio_cache_cleaner():
    """Background task: delete audio files older than 24 hours every hour."""
    while True:
        await asyncio.sleep(3600)
        if not _AUDIO_CACHE_DIR.exists():
            continue
        cutoff = time.time() - _AUDIO_MAX_AGE_HOURS * 3600
        removed = 0
        for f in _AUDIO_CACHE_DIR.iterdir():
            if f.is_file() and f.stat().st_mtime < cutoff:
                try:
                    f.unlink()
                    removed += 1
                except OSError:
                    pass
        if removed:
            logger.info("Audio cache: removed %d stale files", removed)


def _run_migrations() -> None:
    """Apply pending Alembic migrations (no-op if already up to date)."""
    try:
        from alembic.config import Config
        from alembic import command as alembic_cmd
        ini_path = Path(__file__).parent.parent / "alembic.ini"
        if ini_path.exists():
            cfg = Config(str(ini_path))
            alembic_cmd.upgrade(cfg, "head")
            logger.info("Database migrations applied")
            return
    except Exception as exc:
        logger.warning("Alembic migration failed (%s) — falling back to create_all", exc)
    init_db()


@app.on_event("startup")
async def startup():
    # Validate critical security-related secrets
    stripe_secret = os.getenv("STRIPE_WEBHOOK_SECRET", "").strip()
    if stripe_secret:
        if len(stripe_secret) < 32:
            raise RuntimeError(
                "STRIPE_WEBHOOK_SECRET is configured but too short (< 32 chars). "
                "This may indicate a misconfiguration. Please verify."
            )
        logger.info("Stripe webhook secret validated at startup")
    else:
        logger.warning("STRIPE_WEBHOOK_SECRET not configured — webhook validation disabled")

    required = ["ANTHROPIC_API_KEY"]
    missing = [k for k in required if not os.getenv(k)]
    if missing:
        logger.warning("Missing recommended env vars: %s", missing)

    _run_migrations()
    _AUDIO_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    asyncio.create_task(_audio_cache_cleaner())
    logger.info("Persona Hub API started — %d personas loaded", len(PERSONA_LIBRARY))


# ── Static assets ──────────────────────────────────────────────────────────────

_DEMO_DIR = Path(__file__).parent.parent / "demo"
_ASSETS_DIR = _DEMO_DIR / "assets"
_ASSETS_DIR.mkdir(parents=True, exist_ok=True)

app.mount("/assets", StaticFiles(directory=str(_ASSETS_DIR)), name="assets")

# External asset base URL — e.g. https://raw.githubusercontent.com/owner/repo/main
# When set, image_url is always returned (remote 404s handled by frontend onerror).
# When unset, falls back to local demo/assets/personas/ file existence check.
#
# DEPRECATED: Use GET /api/v1/personas/{persona_id}/image (authenticated) instead.
# See ASSET_MIGRATION.md for migration guide.
_PERSONA_ASSETS_BASE = os.getenv("PERSONA_ASSETS_BASE_URL", "").rstrip("/")

# Public base URL for referral links and Stripe billing-portal redirects.
BASE_URL = os.getenv("BASE_URL", "http://localhost:8000")


def _persona_image_url(persona_id: str) -> str | None:
    """
    Get persona image URL.

    DEPRECATED: Construct URLs to GET /api/v1/personas/{persona_id}/image instead.
    Public /assets/personas/{id}.png serving will be removed in a future release.

    See ASSET_MIGRATION.md for migration guide.
    """
    if _PERSONA_ASSETS_BASE:
        return f"{_PERSONA_ASSETS_BASE}/{persona_id}.png"
    img_path = _ASSETS_DIR / "personas" / f"{persona_id}.png"
    return f"/assets/personas/{persona_id}.png" if img_path.exists() else None

@app.get("/demo", include_in_schema=False)
def serve_demo():
    """
    Simulation page (GET /demo?persona=machiavelli&tier=text).
    WebSocket auth: Connect with Authorization header (Authorization: Bearer prs_...).
    """
    demo_file = _DEMO_DIR / "index.html"
    if demo_file.exists():
        return FileResponse(str(demo_file))
    return {"message": "Demo not found. Create demo/index.html"}


@app.get("/catalog", include_in_schema=False)
def serve_catalog():
    """Persona marketplace landing page."""
    f = _DEMO_DIR / "catalog.html"
    if f.exists():
        return FileResponse(str(f))
    return {"message": "Catalog page not found."}


@app.get("/dashboard", include_in_schema=False)
def serve_dashboard():
    """User dashboard page."""
    f = _DEMO_DIR / "dashboard.html"
    if f.exists():
        return FileResponse(str(f))
    return {"message": "Dashboard not found."}


@app.get("/", include_in_schema=False)
def serve_landing():
    """Marketing landing page."""
    f = _DEMO_DIR / "landing.html"
    if f.exists():
        return FileResponse(str(f))
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url="/catalog")


@app.get("/personas/{persona_id}/detail", include_in_schema=False)
def serve_persona_detail(persona_id: str):
    """Persona detail / purchase page."""
    f = _DEMO_DIR / "persona_detail.html"
    if f.exists():
        return FileResponse(str(f))
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url=f"/catalog#{persona_id}")


@app.get("/checkout/success", include_in_schema=False)
def serve_checkout_success():
    """Post-payment success page."""
    f = _DEMO_DIR / "checkout_success.html"
    if f.exists():
        return FileResponse(str(f))
    return {"message": "Purchase successful."}


@app.get("/checkout/cancel", include_in_schema=False)
def serve_checkout_cancel():
    """Payment cancelled page."""
    f = _DEMO_DIR / "checkout_cancel.html"
    if f.exists():
        return FileResponse(str(f))
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url="/catalog")


@app.get("/ceid-monitor", include_in_schema=False)
def serve_ceid_monitor():
    """CEID drift monitoring dashboard."""
    f = _DEMO_DIR / "ceid_monitor.html"
    if f.exists():
        return FileResponse(str(f))
    return {"message": "CEID monitor not found."}


@app.get("/config.js", include_in_schema=False)
def serve_config_js():
    """Runtime API base URL config for frontend pages."""
    base = os.getenv("BASE_URL", "")
    js = f"window.PERSONA_API_URL = '{base}';"
    return Response(content=js, media_type="application/javascript")


# ── WebSocket ──────────────────────────────────────────────────────────────────

@app.websocket("/ws/chat/{persona_id}")
async def ws_chat(
    websocket: WebSocket,
    persona_id: str,
    tier: str = "text",
    platform: str = "raw",
):
    """
    Real-time persona conversation with streaming text + optional voice + visual params.
    Auth: Authorization header required (Authorization: Bearer prs_...)
    Query params: tier=text|voice|full, platform=raw
    """
    # Extract API key from Authorization header
    auth_header = websocket.headers.get("authorization", "")
    api_key = None

    if auth_header.startswith("Bearer "):
        api_key = auth_header[7:]  # Remove "Bearer " prefix

    if not api_key or not api_key.startswith("prs_"):
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Missing Authorization header")
        return

    _tier     = websocket.query_params.get("tier", tier)
    _platform = websocket.query_params.get("platform", platform)
    await persona_chat_ws(websocket, persona_id, api_key, _tier, _platform)


# ── Request models ─────────────────────────────────────────────────────────────

# ── Public endpoints ───────────────────────────────────────────────────────────

@app.get("/health", tags=["system"])
@limiter.limit("100/hour")  # Allow monitoring, but prevent enumeration DoS
async def health(request: Request, db: Session = Depends(get_db)):
    try:
        db.execute(text("SELECT 1"))
        db_ok = True
    except Exception:
        db_ok = False
    return {
        "status": "ok" if db_ok else "degraded",
        "version": "1.0.0",
        "db": db_ok,
        "personas": len(PERSONA_LIBRARY),
    }


@app.get("/personas", tags=["catalog"])
@limiter.limit("100/hour")  # Per-IP rate limit to prevent enumeration/scraping
def get_catalog(
    request: Request,
    domain: Optional[str] = None,
    tags: Optional[str] = None,
    q: Optional[str] = None,
    min_price: float = 0,
    max_price: float = 999,
    limit: int = 100,
    offset: int = 0,
    include_scores: bool = False,
):
    """
    List personas. Supports filtering by domain, tags (comma-separated), text search, price range.
    Set include_scores=true to add CEID quality badges to each result. No auth required.
    """
    tag_list = [t.strip() for t in tags.split(",")] if tags else None
    results = search_personas(
        query=q or "",
        domain=domain,
        tags=tag_list,
        min_price=min_price,
        max_price=max_price,
    )

    if include_scores:
        from persona_math.ceid import ceid_full_diagnostic
        from persona_math.foundation import metallic_score_raw
        from persona_math.threshold import persona_coordinate
        for r in results:
            pid = r.get("id")
            try:
                P = get_persona_vector(pid)
                diag = ceid_full_diagnostic(P)
                coord = persona_coordinate(P)
                r["ceid_score"] = round(diag.get("ceid_composite", 0.0), 4)
                r["metallic_score"] = round(metallic_score_raw(P), 4)
                r["quadrant"] = coord.get("quadrant", "Q?")
                r["power_ethics_ratio"] = round(coord.get("power_axis", 0) / max(coord.get("ethics_axis", 0.01), 0.01), 2)
            except Exception:
                pass

    # Attach image_url to each result
    for r in results:
        r["image_url"] = _persona_image_url(r.get("id", ""))

    total = len(results)
    page = results[offset: offset + limit]
    return {
        "total":    total,
        "offset":   offset,
        "limit":    limit,
        "personas": page,
    }


@app.get("/personas/stats/library", tags=["catalog"])
@limiter.limit("50/hour")  # Prevent repeated scraping of stats data
def get_library_stats(request: Request):
    """Library statistics: total personas, domain breakdown, avg price."""
    stats = library_stats()
    stats["catalog_ids_preview"] = list(PERSONA_LIBRARY.keys())[:20]
    return stats


@app.get("/personas/{persona_id}", tags=["catalog"])
@limiter.limit("200/hour")  # Higher limit for detail requests, but prevent scraping
def get_persona_detail(request: Request, persona_id: str):
    """Persona detail with pricing. No auth required."""
    spec = PERSONA_LIBRARY.get(persona_id)
    if spec:
        data = {"id": persona_id, **PERSONA_CATALOG.get(persona_id, spec)}
    else:
        meta = PERSONA_CATALOG.get(persona_id)
        if meta is None:
            raise HTTPException(status_code=404, detail=f"Persona '{persona_id}' not found.")
        data = {"id": persona_id, **meta}

    data["image_url"] = _persona_image_url(persona_id)
    return data


_REQUIRE_EMAIL_VERIFICATION = os.getenv("REQUIRE_EMAIL_VERIFICATION", "false").lower() == "true"


@app.post("/auth/register", tags=["auth"])
@limiter.limit("5/hour")
def register(request: Request, req: RegisterRequest, db: Session = Depends(get_db)):
    """
    Register a new account. Returns your API key — store it safely.
    One account per email address. A verification email is sent to confirm your address.
    Optional: provide a password to enable /auth/login (alternative to API key).
    Free tier: new users get 1 free persona (Socrates) + referral code.
    """
    existing = get_user_by_email(db, req.email)
    if existing:
        raise HTTPException(
            status_code=409,
            detail="Email already registered. If you lost your API key, contact support.",
        )
    user, full_key = create_user(db, req.email)

    # Track signup event
    track_signup(user.id, req.email, auth_method="email_password" if req.password else "email")

    # Set password if provided
    if req.password:
        user.password_hash = hash_password(req.password)
        db.commit()

    # B20: Grant free tier — 1 free persona (Socrates)
    grant_free_persona(db, user.id, "persona_socrates")
    # Create wallet for user
    get_or_create_wallet(db, user.id)
    # B21: Generate referral code
    ref_code = generate_referral_code(db, user.id)

    # Send verification email (non-blocking; failure logged but doesn't block registration)
    token = create_email_verification_token(db, user.id)
    send_verification_email(req.email, token)

    response = {
        "email": user.email,
        "email_verified": user.email_verified,
        "password_enabled": bool(req.password),
        "referral_code": ref_code,  # User can share this to earn credits
        "free_personas": ["persona_socrates"],  # B20: Free tier personas
    }

    if _REQUIRE_EMAIL_VERIFICATION:
        response["message"] = (
            "Account created. Check your email to verify your address "
            "and receive your API key."
        )
    else:
        response["api_key"] = full_key
        response["message"] = (
            "Store your API key safely — it won't be shown again. "
            "Use it in the X-API-Key header. "
            "A verification email has been sent. "
            "You have 1 free persona and a referral code to earn credits."
        )

    return response


@app.post("/auth/verify-email", tags=["auth"])
@limiter.limit("10/hour")
def verify_email(request: Request, req: VerifyEmailRequest, db: Session = Depends(get_db)):
    """
    Verify email address using the token sent to your inbox.
    Returns the API key if REQUIRE_EMAIL_VERIFICATION is enabled.
    """
    user = consume_verification_token(db, req.token)
    if user is None:
        raise HTTPException(
            status_code=400,
            detail="Invalid or expired verification token.",
        )
    response: dict = {"email": user.email, "email_verified": True, "message": "Email verified."}
    if _REQUIRE_EMAIL_VERIFICATION:
        # Regenerate and return the full key now that email is verified
        from api.db import hash_api_key, User as UserModel
        full_key = UserModel.generate_api_key()
        user.api_key = full_key[:20]
        user.api_key_hash = hash_api_key(full_key)
        db.commit()
        response["api_key"] = full_key
        response["message"] = "Email verified. Store your API key safely — it won't be shown again."
    return response


@app.post("/auth/request-verification", tags=["auth"])
@limiter.limit("3/hour")
def request_verification(request: Request, req: RequestVerificationRequest, db: Session = Depends(get_db)):
    """Re-send a verification email. No-op if email is already verified."""
    user = get_user_by_email(db, req.email)
    # Always return 200 to avoid email enumeration
    if user is None or user.email_verified:
        return {"message": "If the email exists and is unverified, a link has been sent."}
    if has_pending_verification(db, user.id):
        return {"message": "A verification email was recently sent. Please check your inbox."}
    token = create_email_verification_token(db, user.id)
    send_verification_email(req.email, token)
    return {"message": "Verification email sent."}


@app.post("/auth/login", tags=["auth"])
@limiter.limit("10/hour")
def login(request: Request, req: LoginRequest, db: Session = Depends(get_db)):
    """
    Login with email and password. Returns API key on success.
    Failed attempts are tracked; 5 failures trigger 5-minute lockout.
    """
    client_ip = request.client.host if request.client else "unknown"
    user = authenticate_password(db, req.email, req.password, client_ip)

    return {
        "api_key": user.api_key,  # Prefix stored in DB; full key not retrievable
        "email": user.email,
        "message": (
            "Login successful. Use the API key prefix above "
            "(stored in your client). To retrieve the full key, use /auth/register."
        ),
    }


# ── Authenticated endpoints ────────────────────────────────────────────────────

@app.get("/me", tags=["auth"])
def get_me(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Your account details and purchased personas."""
    owned = [p.persona_id for p in user.purchases]
    return {
        "email": user.email,
        "created_at": user.created_at,
        "purchased_personas": owned,
        "n_purchases": len(owned),
    }


@app.get("/me/purchases", tags=["auth"])
def get_purchases(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List your purchased personas with purchase dates."""
    return {
        "purchases": [
            {
                "persona_id": p.persona_id,
                "purchased_at": p.purchased_at,
                "amount_usd": (p.amount_usd / 100) if p.amount_usd else None,
            }
            for p in user.purchases
        ]
    }


# ── Checkout ───────────────────────────────────────────────────────────────────

@app.post("/checkout/{persona_id}", tags=["payments"])
@limiter.limit("20/hour")
def checkout(
    request: Request,
    persona_id: str,
    tier: Optional[str] = None,     # B13: basic_monthly, basic_annual, pro_monthly, pro_annual
    promo: Optional[str] = None,    # B14: promo code
    ref: Optional[str] = None,      # B21: referral code from signup link
    locale: str = "usd",            # B23: currency locale (usd, eur, try, gbp, jpy, aud, cad)
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Create a Stripe Checkout Session to purchase a persona or subscription tier.

    Query parameters:
    - tier: subscription tier (basic_monthly, basic_annual, pro_monthly, pro_annual) — B13
    - promo: coupon code for discount — B14
    - ref: referral code (applies $5 credit if referee's first purchase) — B21
    - locale: currency locale (usd, eur, try, gbp, jpy, aud, cad) — B23

    Returns {checkout_url} — redirect the user there.
    """
    meta = PERSONA_CATALOG.get(persona_id)
    if meta is None:
        raise HTTPException(status_code=404, detail=f"Persona '{persona_id}' not found.")

    # B21: If referral code provided, verify it exists
    referrer_id = None
    if ref:
        ref_code = get_referral_code_by_code(db, ref)
        if not ref_code:
            raise HTTPException(status_code=400, detail="Invalid referral code.")
        referrer_id = ref_code.referrer_id

    # Track checkout initiation
    price_usd = meta.get("price_usd", 9.99)
    track_checkout(user.id, persona_id, price_usd)

    return create_checkout_session(user, persona_id, meta, db, tier=tier, promo=promo, referrer_id=referrer_id, locale=locale)


@app.post("/checkout/bundle/{bundle_id}", tags=["payments"])
@limiter.limit("20/hour")
def checkout_bundle(
    request: Request,
    bundle_id: str,
    locale: str = "usd",  # B23: currency locale
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Purchase a bundle of personas at a discounted price (B15).
    Bundle IDs: bundle_10 (10 personas, $49), bundle_50 (50 personas, $199), bundle_495 (all 495, $999)
    Query parameter: locale (usd, eur, try, gbp, jpy, aud, cad) for multi-currency pricing (B23)
    Returns {checkout_url} — redirect the user there.
    """
    bundle = BUNDLE_PRICING.get(bundle_id)
    if not bundle:
        raise HTTPException(
            status_code=404,
            detail=f"Bundle '{bundle_id}' not found. Choose: {list(BUNDLE_PRICING.keys())}"
        )

    # Create a bundle "meta" object for checkout
    bundle_meta = {
        "name": bundle["name"],
        "description": bundle["description"],
        "price_usd": bundle["price_usd"],
        "bundle_id": bundle_id,
    }

    # Pass bundle_id as the persona_id to distinguish from individual persona purchases
    result = create_checkout_session(user, bundle_id, bundle_meta, db, locale=locale)
    result["bundle"] = bundle_id
    result["personas_count"] = bundle["personas"]
    result["savings_percent"] = bundle["savings_pct"]
    return result


@app.post("/checkout/{persona_id}/mock", tags=["payments"])
def checkout_mock(
    persona_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Development only: grant persona access without Stripe.
    Disabled when STRIPE_SECRET_KEY is a live key.
    """
    meta = PERSONA_CATALOG.get(persona_id)
    if meta is None:
        raise HTTPException(status_code=404, detail=f"Persona '{persona_id}' not found.")
    return mock_purchase(user, persona_id, db)


@app.get("/checkout/success", tags=["payments"], include_in_schema=False)
def checkout_success(session_id: str):
    return {"status": "success", "session_id": session_id,
            "message": "Purchase complete. You can now compile this persona."}


@app.get("/checkout/cancel", tags=["payments"], include_in_schema=False)
def checkout_cancel():
    return {"status": "cancelled"}


# ── Subscription ───────────────────────────────────────────────────────────────

@app.get("/subscription/tiers", tags=["subscription"])
def list_subscription_tiers():
    """Available subscription plans with pricing."""
    return {
        "tiers": {
            k: {
                "price_usd_per_month": v["price_usd"],
                "monthly_requests": v["monthly_requests"] or "unlimited",
                "label": v["label"],
            }
            for k, v in SUBSCRIPTION_TIERS.items()
        }
    }


@app.post("/subscribe/{tier}", tags=["subscription"])
def subscribe(
    tier: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Create a Stripe Checkout Session for a monthly subscription.
    Tiers: basic ($9/mo, 1 000 calls) | pro ($29/mo, unlimited).
    Returns {checkout_url}.
    """
    return create_subscription_session(user, tier, db)


@app.get("/me/subscription", tags=["subscription"])
def get_my_subscription(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Your current subscription status and quota."""
    quota = check_quota(db, user.id)
    if not quota["has_subscription"]:
        return {
            "has_subscription": False,
            "message": "No active subscription. POST /subscribe/basic or /subscribe/pro",
            "available_tiers": list(SUBSCRIPTION_TIERS.keys()),
        }
    return quota


@app.delete("/me/subscription", tags=["subscription"])
def cancel_my_subscription(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Cancel your current subscription."""
    cancelled = cancel_subscription(db, user.id)
    if not cancelled:
        raise HTTPException(status_code=404, detail="No active subscription found.")
    return {"status": "cancelled"}


# ── Referral Program (B21) ────────────────────────────────────────────────────

@app.post("/me/referral-code", tags=["payments"])
def get_my_referral_code(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get or create a referral code for earning credits.
    Share the referral URL with friends — when they sign up and make a purchase,
    you get $5 credit toward your next purchase.
    """
    code = generate_referral_code(db, user.id)
    return {
        "code": code,
        "url": f"{BASE_URL}?ref={code}",
        "message": "Share this code with friends to earn $5 credits per signup + first purchase.",
    }


# ── Wallet/Credits (B22) ──────────────────────────────────────────────────────

@app.get("/me/wallet", tags=["payments"])
def get_wallet_balance(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get your wallet balance (in cents).
    Credit is automatically deducted from wallet before charging Stripe.
    """
    wallet = get_or_create_wallet(db, user.id)
    return {
        "balance_cents": wallet.balance_cents or 0,
        "balance_usd": (wallet.balance_cents or 0) / 100,
    }


# ── Invoices (B17) ────────────────────────────────────────────────────────────

@app.get("/me/invoices", tags=["payments"])
def get_my_invoices(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    limit: int = 50,
):
    """
    Get your recent invoices for accounting and tax purposes.
    Each invoice includes a link to the PDF for download.
    """
    from api.db import get_user_invoices
    invoices = get_user_invoices(db, user.id, limit=limit)
    return {
        "invoices": [
            {
                "id": inv.id,
                "stripe_invoice_id": inv.stripe_invoice_id,
                "amount_usd": inv.amount_usd_cents / 100,
                "status": inv.status,
                "issued_at": inv.issued_at.isoformat() if inv.issued_at else None,
                "due_at": inv.due_at.isoformat() if inv.due_at else None,
                "pdf_url": inv.pdf_url,
            }
            for inv in invoices
        ]
    }


# ── Billing Portal (B16) ──────────────────────────────────────────────────────

@app.post("/billing/portal", tags=["payments"])
def create_billing_portal_session(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Create a Stripe Billing Portal session for managing subscriptions.
    Returns a redirect URL to Stripe's customer portal where you can:
    - View and download invoices
    - Update payment method
    - Cancel subscription
    - View billing history
    """
    if not stripe.api_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Payment system not configured.",
        )

    if not user.stripe_customer_id:
        raise HTTPException(
            status_code=400,
            detail="No subscription found. Make a subscription purchase first.",
        )

    try:
        session = stripe.billing_portal.Session.create(
            customer=user.stripe_customer_id,
            return_url=f"{BASE_URL}/me",
        )
        return {"url": session.url}
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Billing portal error: {str(e)}")


# ── Admin: Refund endpoint (B18) ───────────────────────────────────────────────

@app.post("/admin/refund/{purchase_id}", tags=["admin"])
def refund_purchase(
    request: Request,
    purchase_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    ADMIN ONLY: Issue a refund for a purchase and revoke persona access (B18).
    Soft-deletes the purchase record (for GDPR/KVKK compliance).
    """
    from api.db import Purchase
    from datetime import datetime, timezone

    if user.role != "admin":
        raise HTTPException(
            status_code=403,
            detail="Admin access required.",
        )

    purchase = db.query(Purchase).filter(Purchase.id == purchase_id).first()
    if not purchase:
        raise HTTPException(status_code=404, detail="Purchase not found.")

    # Soft-delete the purchase
    purchase.deleted_at = datetime.now(timezone.utc)
    db.commit()

    # Attempt to issue Stripe refund if session exists
    refund_result = None
    if purchase.stripe_session_id:
        try:
            # Retrieve the payment intent from the session
            checkout_session = stripe.checkout.Session.retrieve(purchase.stripe_session_id)
            payment_intent = checkout_session.payment_intent
            if payment_intent:
                refund = stripe.Refund.create(charge=payment_intent)
                refund_result = {"stripe_refund_id": refund.id, "status": refund.status}
        except Exception as e:
            # Log error but still consider purchase soft-deleted
            logger.warning(f"Failed to refund Stripe payment: {e}")

    return {
        "status": "refunded",
        "purchase_id": purchase_id,
        "persona_id": purchase.persona_id,
        "user_id": purchase.user_id,
        "amount_refunded_usd": (purchase.amount_usd or 0) / 100,
        "stripe_refund": refund_result,
        "message": "Purchase access revoked. Stripe refund issued if applicable.",
    }


# ── Stripe webhook (no auth — Stripe sends directly) ──────────────────────────

@app.post("/webhook/stripe", tags=["payments"], include_in_schema=False)
async def stripe_webhook(
    request: Request,
    stripe_signature: Optional[str] = Header(default=None, alias="Stripe-Signature"),
    db: Session = Depends(get_db),
):
    raw_body = await request.body()
    if not stripe_signature:
        raise HTTPException(status_code=400, detail="Missing Stripe-Signature header.")
    return handle_webhook(raw_body, stripe_signature, db)


# ── Compile (gated by purchase + subscription quota) ──────────────────────────

def _check_and_count(db: Session, user: User, endpoint: str, persona_id: str) -> None:
    """Enforce subscription quota; increment counter on success."""
    quota = check_quota(db, user.id)
    if quota["has_subscription"] and not quota["allowed"]:
        raise HTTPException(
            status_code=429,
            detail=f"Monthly limit reached ({quota['used']}/{quota['limit']}). Upgrade to Pro.",
        )
    log_usage(db, user.id, endpoint, persona_id=persona_id)
    if quota["has_subscription"]:
        increment_request_count(db, user.id)


@app.post("/v1/compile/{persona_id}", tags=["compile"])
@limiter.limit("100/hour")
def compile(
    request: Request,
    persona_id: str,
    req: CompileRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Compile a purchased persona for the given platform and tier."""
    if req.platform not in SUPPORTED_PLATFORMS:
        raise HTTPException(400, detail=f"platform must be one of {SUPPORTED_PLATFORMS}")
    if req.tier not in SUPPORTED_TIERS:
        raise HTTPException(400, detail=f"tier must be one of {SUPPORTED_TIERS}")
    require_persona_access(persona_id, user, db)
    try:
        P = get_persona_vector(persona_id)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Persona '{persona_id}' not found.")
    result = compile_persona(P, persona_id=persona_id, platform=req.platform, tier=req.tier)
    _check_and_count(db, user, f"/v1/compile/{persona_id}", persona_id)
    # Track compilation event
    track_compilation(user.id, persona_id, req.platform)
    return result


@app.post("/v1/compile/{persona_id}/all-platforms", tags=["compile"])
@limiter.limit("100/hour")
def compile_platforms(
    request: Request,
    persona_id: str,
    req: AllPlatformsRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Compile persona for all platforms at the given tier."""
    if req.tier not in SUPPORTED_TIERS:
        raise HTTPException(400, detail=f"tier must be one of {SUPPORTED_TIERS}")
    require_persona_access(persona_id, user, db)
    try:
        P = get_persona_vector(persona_id)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Persona '{persona_id}' not found.")
    result = compile_all_platforms(P, persona_id=persona_id, tier=req.tier)
    _check_and_count(db, user, f"/v1/compile/{persona_id}/all-platforms", persona_id)
    return result


@app.post("/v1/compile/{persona_id}/all-tiers", tags=["compile"])
@limiter.limit("100/hour")
def compile_tiers(
    request: Request,
    persona_id: str,
    req: AllTiersRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Compile persona at all tiers for the given platform."""
    if req.platform not in SUPPORTED_PLATFORMS:
        raise HTTPException(400, detail=f"platform must be one of {SUPPORTED_PLATFORMS}")
    require_persona_access(persona_id, user, db)
    try:
        P = get_persona_vector(persona_id)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Persona '{persona_id}' not found.")
    result = compile_all_tiers(P, persona_id=persona_id, platform=req.platform)
    _check_and_count(db, user, f"/v1/compile/{persona_id}/all-tiers", persona_id)
    return result


@app.post("/v1/compile/{persona_id}/voice", tags=["compile"])
@limiter.limit("30/hour")
async def compile_voice(
    request: Request,
    persona_id: str,
    req: VoiceRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Synthesize a persona voice response as MP3 audio via ElevenLabs TTS."""
    if not tts_available():
        raise HTTPException(503, detail="Voice synthesis unavailable: ELEVENLABS_API_KEY not configured.")
    require_persona_access(persona_id, user, db)
    try:
        P = get_persona_vector(persona_id)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Persona '{persona_id}' not found.")
    vparams = get_visual_params(P, persona_id)
    audio_bytes = await synthesize_speech(req.text, persona_id, vparams.get("voice", {}))
    if not audio_bytes:
        raise HTTPException(status_code=502, detail="Voice synthesis failed.")
    _check_and_count(db, user, f"/v1/compile/{persona_id}/voice", persona_id)
    return Response(content=audio_bytes, media_type="audio/mpeg")
