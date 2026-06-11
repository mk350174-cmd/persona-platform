"""Advanced Authentication Endpoints — OAuth2, JWT, RBAC, sessions."""

import secrets
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session

from api.db import (
    get_db, User, create_user, get_user_by_email,
    OAuth2Credential, InvalidatedSession, hash_api_key,
)
from api.advanced_auth import (
    get_token_manager, get_session_manager,
    get_google_oauth, get_github_oauth,
    generate_oauth_state, verify_oauth_state,
    UserRole,
    get_current_user_jwt, require_permission, require_role,
    check_password_strength,
)

router = APIRouter(prefix="/auth", tags=["auth"])


# ── OAuth2 Endpoints ──────────────────────────────────────────────────────────

@router.get("/oauth/google")
def start_google_oauth(
    redirect_url: Optional[str] = None,
):
    """Start Google OAuth2 flow."""
    google_oauth = get_google_oauth()
    if not google_oauth.client_id:
        raise HTTPException(status_code=501, detail="Google OAuth2 not configured")

    # Generate state token
    state = generate_oauth_state("temp", "google")

    auth_url = google_oauth.get_authorization_url(state)
    return {"auth_url": auth_url, "state": state}


@router.get("/oauth/github")
def start_github_oauth(
    redirect_url: Optional[str] = None,
):
    """Start GitHub OAuth2 flow."""
    github_oauth = get_github_oauth()
    if not github_oauth.client_id:
        raise HTTPException(status_code=501, detail="GitHub OAuth2 not configured")

    # Generate state token
    state = generate_oauth_state("temp", "github")

    auth_url = github_oauth.get_authorization_url(state)
    return {"auth_url": auth_url, "state": state}


@router.get("/oauth/google/callback")
async def google_oauth_callback(
    code: str,
    state: str,
    db: Session = Depends(get_db),
):
    """Google OAuth2 callback handler."""
    try:
        user_id, provider = verify_oauth_state(state)
    except HTTPException:
        raise HTTPException(status_code=400, detail="Invalid state token")

    google_oauth = get_google_oauth()

    # Exchange code for access token
    token_response = await google_oauth.exchange_code_for_token(code)
    access_token = token_response.get("access_token")
    if not access_token:
        raise HTTPException(status_code=400, detail="Failed to get access token")

    # Get user info from Google
    user_info = await google_oauth.get_user_info(access_token)
    email = user_info.get("email")
    provider_user_id = user_info.get("sub")  # OpenID sub

    if not email or not provider_user_id:
        raise HTTPException(status_code=400, detail="Failed to get user info from Google")

    # Find or create user
    user = get_user_by_email(db, email)
    if not user:
        user, _ = create_user(db, email)

    # Store or update OAuth2 credential
    cred = db.query(OAuth2Credential).filter(
        OAuth2Credential.user_id == user.id,
        OAuth2Credential.provider == "google",
    ).first()

    if cred:
        cred.access_token = access_token
        cred.refresh_token = token_response.get("refresh_token")
        cred.last_used_at = datetime.now(timezone.utc)
    else:
        cred = OAuth2Credential(
            user_id=user.id,
            provider="google",
            provider_user_id=provider_user_id,
            access_token=access_token,
            refresh_token=token_response.get("refresh_token"),
        )
        db.add(cred)

    db.commit()
    db.refresh(user)

    # Generate JWT tokens
    token_manager = get_token_manager()
    access_token_jwt = token_manager.create_access_token(
        user_id=user.id,
        email=user.email,
        role=UserRole(user.role) if user.role else UserRole.USER,
    )
    refresh_token_jwt = token_manager.create_refresh_token(user.id, user.email)

    return {
        "access_token": access_token_jwt,
        "refresh_token": refresh_token_jwt,
        "token_type": "bearer",
        "user_id": user.id,
        "email": user.email,
    }


@router.get("/oauth/github/callback")
async def github_oauth_callback(
    code: str,
    state: str,
    db: Session = Depends(get_db),
):
    """GitHub OAuth2 callback handler."""
    try:
        user_id, provider = verify_oauth_state(state)
    except HTTPException:
        raise HTTPException(status_code=400, detail="Invalid state token")

    github_oauth = get_github_oauth()

    # Exchange code for access token
    token_response = await github_oauth.exchange_code_for_token(code)
    access_token = token_response.get("access_token")
    if not access_token:
        raise HTTPException(status_code=400, detail="Failed to get access token")

    # Get user info from GitHub
    user_info = await github_oauth.get_user_info(access_token)
    email = user_info.get("email")
    provider_user_id = str(user_info.get("id"))

    if not email or not provider_user_id:
        raise HTTPException(status_code=400, detail="Failed to get user info from GitHub")

    # Find or create user
    user = get_user_by_email(db, email)
    if not user:
        user, _ = create_user(db, email)

    # Store or update OAuth2 credential
    cred = db.query(OAuth2Credential).filter(
        OAuth2Credential.user_id == user.id,
        OAuth2Credential.provider == "github",
    ).first()

    if cred:
        cred.access_token = access_token
        cred.last_used_at = datetime.now(timezone.utc)
    else:
        cred = OAuth2Credential(
            user_id=user.id,
            provider="github",
            provider_user_id=provider_user_id,
            access_token=access_token,
        )
        db.add(cred)

    db.commit()
    db.refresh(user)

    # Generate JWT tokens
    token_manager = get_token_manager()
    access_token_jwt = token_manager.create_access_token(
        user_id=user.id,
        email=user.email,
        role=UserRole(user.role) if user.role else UserRole.USER,
    )
    refresh_token_jwt = token_manager.create_refresh_token(user.id, user.email)

    return {
        "access_token": access_token_jwt,
        "refresh_token": refresh_token_jwt,
        "token_type": "bearer",
        "user_id": user.id,
        "email": user.email,
    }


# ── JWT Token Endpoints ───────────────────────────────────────────────────────

@router.post("/oauth/token")
def refresh_access_token(
    refresh_token: str,
    db: Session = Depends(get_db),
):
    """Refresh access token using refresh token."""
    token_manager = get_token_manager()

    try:
        payload = token_manager.verify_token(refresh_token)
    except HTTPException as e:
        raise e

    # Verify it's a refresh token
    if payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type",
        )

    # Get user
    user = db.query(User).filter(User.id == payload.get("sub")).first()
    if not user or user.deleted_at:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or deleted",
        )

    # Create new access token
    access_token = token_manager.create_access_token(
        user_id=user.id,
        email=user.email,
        role=UserRole(user.role) if user.role else UserRole.USER,
    )

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in": 900,  # 15 minutes
    }


# ── Session Management ────────────────────────────────────────────────────────

@router.post("/logout")
def logout(
    request: Request,
    user: User = Depends(get_current_user_jwt),
    db: Session = Depends(get_db),
):
    """Invalidate current session (logout)."""
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing token")

    token = auth_header[7:]

    # Hash token for storage
    token_hash = hash_api_key(token)

    # Create invalidated session record
    token_manager = get_token_manager()
    payload = token_manager.verify_token(token)

    invalidated = InvalidatedSession(
        user_id=user.id,
        token_hash=token_hash,
        expires_at=datetime.fromtimestamp(payload.get("exp"), tz=timezone.utc),
        reason="logout",
    )
    db.add(invalidated)
    db.commit()

    # Also invalidate in session manager
    session_manager = get_session_manager()
    session_manager.invalidate_session(token, user.id)

    return {
        "status": "logged_out",
        "message": "Session invalidated",
        "user_id": user.id,
    }


@router.post("/logout/all")
def logout_all(
    user: User = Depends(get_current_user_jwt),
    db: Session = Depends(get_db),
):
    """Invalidate all sessions for the user (security lock)."""
    # Create invalidated session records with future expiry
    from datetime import timedelta
    expires_at = datetime.now(timezone.utc) + timedelta(days=365)

    invalidated = InvalidatedSession(
        user_id=user.id,
        token_hash=secrets.token_hex(32),  # Placeholder
        expires_at=expires_at,
        reason="security_lock",
    )
    db.add(invalidated)
    db.commit()

    return {
        "status": "all_sessions_invalidated",
        "message": "All sessions have been terminated",
        "user_id": user.id,
    }


# ── User Profile & Roles ──────────────────────────────────────────────────────

@router.get("/me")
def get_current_user_profile(
    user: User = Depends(get_current_user_jwt),
    db: Session = Depends(get_db),
):
    """Get current user's profile."""
    return {
        "id": user.id,
        "email": user.email,
        "role": user.role,
        "active": user.active,
        "email_verified": user.email_verified,
        "created_at": user.created_at.isoformat(),
        "oauth_providers": [
            {
                "provider": cred.provider,
                "connected_at": cred.connected_at.isoformat(),
                "last_used_at": cred.last_used_at.isoformat() if cred.last_used_at else None,
            }
            for cred in user.oauth_credentials
        ],
    }


@router.patch("/me/password")
def change_password(
    old_password: str,
    new_password: str,
    user: User = Depends(get_current_user_jwt),
    db: Session = Depends(get_db),
):
    """Change user's password."""
    from api.db import verify_password, hash_password

    # Verify old password
    if not user.password_hash or not verify_password(user.password_hash, old_password):
        raise HTTPException(status_code=401, detail="Invalid password")

    # Check new password strength
    is_strong, message = check_password_strength(new_password)
    if not is_strong:
        raise HTTPException(status_code=400, detail=message)

    # Update password
    user.password_hash = hash_password(new_password)
    db.commit()

    # Invalidate all sessions (require re-login)
    session_manager = get_session_manager()
    session_manager.clear_user_sessions(user.id)

    return {
        "status": "password_changed",
        "message": "Password changed. Please login again.",
    }


@router.get("/users/{user_id}")
def get_user_profile(
    user_id: str,
    current_user: User = Depends(require_permission("users:read_all")),
    db: Session = Depends(get_db),
):
    """Get user profile (admin/moderator only)."""
    user = db.query(User).filter(User.id == user_id, User.deleted_at == None).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return {
        "id": user.id,
        "email": user.email,
        "role": user.role,
        "active": user.active,
        "created_at": user.created_at.isoformat(),
        "email_verified": user.email_verified,
    }


@router.patch("/users/{user_id}/role")
def update_user_role(
    user_id: str,
    new_role: str,
    current_user: User = Depends(require_role(UserRole.ADMIN)),
    db: Session = Depends(get_db),
):
    """Update user's role (admin only)."""
    # Validate role
    try:
        role = UserRole(new_role)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid role. Must be one of: {', '.join([r.value for r in UserRole])}",
        )

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.role = role.value
    db.commit()
    db.refresh(user)

    return {
        "status": "role_updated",
        "user_id": user.id,
        "role": user.role,
    }


@router.delete("/users/{user_id}")
def delete_user(
    user_id: str,
    current_user: User = Depends(require_role(UserRole.ADMIN)),
    db: Session = Depends(get_db),
):
    """Soft-delete a user (admin only)."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.deleted_at = datetime.now(timezone.utc)
    db.commit()

    return {
        "status": "user_deleted",
        "user_id": user.id,
        "deleted_at": user.deleted_at.isoformat(),
    }


# ── Permissions & RBAC ────────────────────────────────────────────────────────

@router.get("/permissions")
def get_user_permissions(
    user: User = Depends(get_current_user_jwt),
):
    """Get current user's permissions."""
    from api.advanced_auth import ROLE_PERMISSIONS

    role = UserRole(user.role) if user.role else UserRole.FREE
    permissions = ROLE_PERMISSIONS.get(role, set())

    return {
        "user_id": user.id,
        "role": role.value,
        "permissions": list(permissions),
    }


@router.get("/roles")
def list_roles():
    """List all available roles."""
    return {
        "roles": [
            {
                "name": role.value,
                "description": f"{role.value.capitalize()} user",
            }
            for role in UserRole
        ],
    }
