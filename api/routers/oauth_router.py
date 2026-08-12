"""Google/GitHub OAuth2 login (T2-008).

Not configured out of the box -- reads GOOGLE_CLIENT_ID/GOOGLE_CLIENT_SECRET
and GITHUB_CLIENT_ID/GITHUB_CLIENT_SECRET from the environment. If a
provider's credentials aren't set, its /login route returns 503 rather
than crashing (graceful-degradation pattern, CLAUDE.md). Real credentials
require registering an OAuth app with each provider -- see
docs/OAUTH2_KURULUM_REHBERI.md for the human steps; nothing here can do
that registration on the user's behalf.

CSRF protection uses a short-lived signed JWT as `state` instead of
server-side session storage, so this stays stateless and safe to run
behind multiple workers/instances without shared session state.
"""
from __future__ import annotations

import os
import time
from urllib.parse import urlencode

import httpx
from fastapi import APIRouter, HTTPException, Query, status
from fastapi.responses import RedirectResponse
from jose import jwt, JWTError
from sqlalchemy.orm import Session as OrmSession

from ..db import SessionLocal, User
from ..security import create_access_token, JWT_SECRET_KEY, JWT_ALGORITHM

router = APIRouter(prefix="/auth", tags=["oauth"])

_STATE_TTL_SECONDS = 300
FRONTEND_CALLBACK_URL = os.environ.get("FRONTEND_CALLBACK_URL")  # e.g. https://app.example.com/oauth-complete

# Static per-provider config. client_id/secret are read lazily (per
# request, via _provider_or_404) rather than frozen at import time, so
# tests can monkeypatch os.environ without needing to reimport this module.
_PROVIDERS = {
    "google": {
        "client_id_env": "GOOGLE_CLIENT_ID",
        "client_secret_env": "GOOGLE_CLIENT_SECRET",
        "authorize_url": "https://accounts.google.com/o/oauth2/v2/auth",
        "token_url": "https://oauth2.googleapis.com/token",
        "userinfo_url": "https://www.googleapis.com/oauth2/v3/userinfo",
        "scope": "openid email profile",
    },
    "github": {
        "client_id_env": "GITHUB_CLIENT_ID",
        "client_secret_env": "GITHUB_CLIENT_SECRET",
        "authorize_url": "https://github.com/login/oauth/authorize",
        "token_url": "https://github.com/login/oauth/access_token",
        "userinfo_url": "https://api.github.com/user",
        "scope": "read:user user:email",
    },
}


def _redirect_uri(provider: str, request_base_url: str) -> str:
    base = os.environ.get("OAUTH_REDIRECT_BASE", request_base_url.rstrip("/"))
    return f"{base}/auth/{provider}/callback"


def _make_state() -> str:
    return jwt.encode({"nonce": os.urandom(8).hex(), "exp": int(time.time()) + _STATE_TTL_SECONDS},
                       JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)


def _verify_state(state: str) -> None:
    try:
        jwt.decode(state, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
    except JWTError:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid or expired OAuth state")


def _provider_or_404(provider: str) -> dict:
    cfg = _PROVIDERS.get(provider)
    if cfg is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Unknown OAuth provider: {provider}")
    cfg = dict(cfg)
    cfg["client_id"] = os.environ.get(cfg["client_id_env"])
    cfg["client_secret"] = os.environ.get(cfg["client_secret_env"])
    return cfg


def _guard_configured(cfg: dict, provider: str) -> None:
    if not cfg["client_id"] or not cfg["client_secret"]:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            f"{provider} OAuth is not configured on this server "
            f"(missing {provider.upper()}_CLIENT_ID/{provider.upper()}_CLIENT_SECRET). "
            "See docs/OAUTH2_KURULUM_REHBERI.md.",
        )


@router.get("/{provider}/login")
def oauth_login(provider: str):
    cfg = _provider_or_404(provider)
    _guard_configured(cfg, provider)
    redirect_uri = _redirect_uri(provider, os.environ.get("OAUTH_REDIRECT_BASE", "http://localhost:8000"))
    params = {
        "client_id": cfg["client_id"],
        "redirect_uri": redirect_uri,
        "scope": cfg["scope"],
        "state": _make_state(),
        "response_type": "code",
    }
    return RedirectResponse(f"{cfg['authorize_url']}?{urlencode(params)}")


def _find_or_create_user(db: OrmSession, provider: str, oauth_id: str, email: str) -> User:
    user = db.query(User).filter(User.oauth_provider == provider, User.oauth_id == oauth_id).first()
    if user:
        return user
    # An existing password-registered account with the same email links to
    # OAuth rather than creating a duplicate account for the same person.
    user = db.query(User).filter(User.email == email).first()
    if user:
        user.oauth_provider = provider
        user.oauth_id = oauth_id
        db.commit()
        db.refresh(user)
        return user
    user = User(email=email, password_hash=None, date_of_birth=None,
                oauth_provider=provider, oauth_id=oauth_id, email_verified=True)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.get("/{provider}/callback")
def oauth_callback(provider: str, code: str = Query(...), state: str = Query(...)):
    cfg = _provider_or_404(provider)
    _guard_configured(cfg, provider)
    _verify_state(state)
    redirect_uri = _redirect_uri(provider, os.environ.get("OAUTH_REDIRECT_BASE", "http://localhost:8000"))

    with httpx.Client(timeout=10.0) as client:
        token_resp = client.post(
            cfg["token_url"],
            data={"client_id": cfg["client_id"], "client_secret": cfg["client_secret"],
                  "code": code, "redirect_uri": redirect_uri, "grant_type": "authorization_code"},
            headers={"Accept": "application/json"},
        )
        if token_resp.status_code != 200:
            raise HTTPException(status.HTTP_502_BAD_GATEWAY, f"{provider} token exchange failed")
        access_token = token_resp.json().get("access_token")
        if not access_token:
            raise HTTPException(status.HTTP_502_BAD_GATEWAY, f"{provider} did not return an access token")

        user_resp = client.get(cfg["userinfo_url"],
                                headers={"Authorization": f"Bearer {access_token}",
                                         "Accept": "application/json"})
        if user_resp.status_code != 200:
            raise HTTPException(status.HTTP_502_BAD_GATEWAY, f"{provider} userinfo request failed")
        info = user_resp.json()

        if provider == "google":
            oauth_id, email = info.get("sub"), info.get("email")
        else:  # github
            oauth_id = str(info.get("id"))
            email = info.get("email")
            if not email:
                # GitHub only returns email here if the user's primary email is public;
                # otherwise it requires a separate call to /user/emails.
                emails_resp = client.get("https://api.github.com/user/emails",
                                          headers={"Authorization": f"Bearer {access_token}",
                                                   "Accept": "application/json"})
                if emails_resp.status_code == 200:
                    primary = next((e for e in emails_resp.json() if e.get("primary")), None)
                    email = primary["email"] if primary else None

    if not oauth_id or not email:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, f"{provider} did not provide id/email")

    db = SessionLocal()
    try:
        user = _find_or_create_user(db, provider, oauth_id, email)
        access = create_access_token(user.id)
    finally:
        db.close()

    if FRONTEND_CALLBACK_URL:
        return RedirectResponse(f"{FRONTEND_CALLBACK_URL}?{urlencode({'token': access})}")
    return {"access_token": access, "token_type": "bearer",
            "needs_date_of_birth": user.date_of_birth is None}
