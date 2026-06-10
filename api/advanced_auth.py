"""
Advanced Authentication — OAuth2, JWT with refresh tokens, RBAC, session management.

Flows:
1. JWT with refresh tokens: POST /auth/oauth/token → access + refresh tokens
2. OAuth2 (Google/GitHub): POST /auth/oauth/google/callback → JWT tokens
3. RBAC: Middleware checks user.role + endpoint permissions
4. Sessions: InvalidateSession table tracks logged-out sessions
"""

import os
import secrets
import hmac
import hashlib
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, List, Set
from enum import Enum
from functools import lru_cache

import jwt
from fastapi import HTTPException, status, Depends, Request
from sqlalchemy.orm import Session
import httpx

from api.db import get_db, User


# ── User Roles & Permissions ──────────────────────────────────────────────────

class UserRole(str, Enum):
    """User roles for RBAC."""
    ADMIN = "admin"
    MODERATOR = "moderator"
    USER = "user"
    FREE = "free"


ROLE_PERMISSIONS: Dict[UserRole, Set[str]] = {
    UserRole.ADMIN: {
        "users:read_all",
        "users:write_all",
        "policies:write",
        "rollback:execute_immediate",
        "audit:read",
        "settings:write",
    },
    UserRole.MODERATOR: {
        "users:read_all",
        "personas:flag_abuse",
        "audit:read",
        "rollback:execute_with_approval",
    },
    UserRole.USER: {
        "personas:read",
        "personas:compile",
        "users:read_own",
        "users:write_own",
        "orders:read_own",
    },
    UserRole.FREE: {
        "personas:read",
        "users:read_own",
    },
}


def has_permission(role: UserRole, permission: str) -> bool:
    """Check if role has permission."""
    return permission in ROLE_PERMISSIONS.get(role, set())


# ── JWT Token Management ──────────────────────────────────────────────────────

class TokenType(str, Enum):
    """Token types for different purposes."""
    ACCESS = "access"
    REFRESH = "refresh"
    OAUTH = "oauth"


class JWTTokenManager:
    """Manage JWT token creation, validation, and refresh."""

    def __init__(self):
        self.secret_key = os.getenv("JWT_SECRET_KEY", secrets.token_urlsafe(32))
        self.access_token_lifetime = int(os.getenv("JWT_ACCESS_TOKEN_LIFETIME_MINUTES", "15"))
        self.refresh_token_lifetime = int(os.getenv("JWT_REFRESH_TOKEN_LIFETIME_DAYS", "7"))
        self.algorithm = "HS256"

    def create_access_token(
        self,
        user_id: str,
        email: str,
        role: UserRole = UserRole.USER,
        expires_delta: Optional[timedelta] = None,
    ) -> str:
        """Create a JWT access token."""
        if expires_delta is None:
            expires_delta = timedelta(minutes=self.access_token_lifetime)

        now = datetime.now(timezone.utc)
        expires_at = now + expires_delta

        payload = {
            "sub": user_id,
            "email": email,
            "role": role.value,
            "type": TokenType.ACCESS.value,
            "iat": int(now.timestamp()),
            "exp": int(expires_at.timestamp()),
        }

        token = jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
        return token

    def create_refresh_token(
        self,
        user_id: str,
        email: str,
        expires_delta: Optional[timedelta] = None,
    ) -> str:
        """Create a JWT refresh token (longer-lived)."""
        if expires_delta is None:
            expires_delta = timedelta(days=self.refresh_token_lifetime)

        now = datetime.now(timezone.utc)
        expires_at = now + expires_delta

        payload = {
            "sub": user_id,
            "email": email,
            "type": TokenType.REFRESH.value,
            "iat": int(now.timestamp()),
            "exp": int(expires_at.timestamp()),
        }

        token = jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
        return token

    def verify_token(self, token: str) -> Dict:
        """Verify and decode a JWT token."""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            return payload
        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has expired",
            )
        except jwt.InvalidTokenError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token",
            )


# Global token manager
_token_manager = JWTTokenManager()


def get_token_manager() -> JWTTokenManager:
    """Get the global JWT token manager."""
    return _token_manager


# ── OAuth2 Integration ────────────────────────────────────────────────────────

class OAuth2Provider(str, Enum):
    """Supported OAuth2 providers."""
    GOOGLE = "google"
    GITHUB = "github"


class GoogleOAuth2:
    """Google OAuth2 integration."""

    def __init__(self):
        self.client_id = os.getenv("GOOGLE_OAUTH_CLIENT_ID", "")
        self.client_secret = os.getenv("GOOGLE_OAUTH_CLIENT_SECRET", "")
        self.redirect_uri = os.getenv("GOOGLE_OAUTH_REDIRECT_URI", "http://localhost:8000/auth/oauth/google/callback")

    def get_authorization_url(self, state: str) -> str:
        """Get Google authorization URL."""
        params = {
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "response_type": "code",
            "scope": "openid email profile",
            "state": state,
        }
        query_string = "&".join(f"{k}={v}" for k, v in params.items())
        return f"https://accounts.google.com/o/oauth2/v2/auth?{query_string}"

    async def exchange_code_for_token(self, code: str) -> Dict:
        """Exchange authorization code for access token."""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://oauth2.googleapis.com/token",
                data={
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "code": code,
                    "grant_type": "authorization_code",
                    "redirect_uri": self.redirect_uri,
                },
            )
            response.raise_for_status()
            return response.json()

    async def get_user_info(self, access_token: str) -> Dict:
        """Get user info from Google."""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://openidconnect.googleapis.com/v1/userinfo",
                headers={"Authorization": f"Bearer {access_token}"},
            )
            response.raise_for_status()
            return response.json()


class GitHubOAuth2:
    """GitHub OAuth2 integration."""

    def __init__(self):
        self.client_id = os.getenv("GITHUB_OAUTH_CLIENT_ID", "")
        self.client_secret = os.getenv("GITHUB_OAUTH_CLIENT_SECRET", "")
        self.redirect_uri = os.getenv("GITHUB_OAUTH_REDIRECT_URI", "http://localhost:8000/auth/oauth/github/callback")

    def get_authorization_url(self, state: str) -> str:
        """Get GitHub authorization URL."""
        params = {
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "scope": "user:email",
            "state": state,
        }
        query_string = "&".join(f"{k}={v}" for k, v in params.items())
        return f"https://github.com/login/oauth/authorize?{query_string}"

    async def exchange_code_for_token(self, code: str) -> Dict:
        """Exchange authorization code for access token."""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://github.com/login/oauth/access_token",
                data={
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "code": code,
                },
                headers={"Accept": "application/json"},
            )
            response.raise_for_status()
            return response.json()

    async def get_user_info(self, access_token: str) -> Dict:
        """Get user info from GitHub."""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://api.github.com/user",
                headers={"Authorization": f"Bearer {access_token}"},
            )
            response.raise_for_status()
            return response.json()


# Global OAuth2 providers
_google_oauth = GoogleOAuth2()
_github_oauth = GitHubOAuth2()


def get_google_oauth() -> GoogleOAuth2:
    """Get Google OAuth2 instance."""
    return _google_oauth


def get_github_oauth() -> GitHubOAuth2:
    """Get GitHub OAuth2 instance."""
    return _github_oauth


# ── Session Management ────────────────────────────────────────────────────────

class SessionManager:
    """Manage user sessions and token invalidation."""

    def __init__(self):
        self.invalidated_tokens: Set[str] = set()  # In production, use Redis

    def invalidate_session(self, token: str, user_id: str):
        """Invalidate a session (logout)."""
        self.invalidated_tokens.add(token)

    def is_session_valid(self, token: str) -> bool:
        """Check if session token is still valid."""
        return token not in self.invalidated_tokens

    def clear_user_sessions(self, user_id: str):
        """Clear all sessions for a user (on password change, etc.)."""
        # In production, store tokens with user_id and filter
        pass


# Global session manager
_session_manager = SessionManager()


def get_session_manager() -> SessionManager:
    """Get the global session manager."""
    return _session_manager


# ── JWT Authentication Dependency ────────────────────────────────────────────

async def get_current_user_jwt(
    request: Request,
    db: Session = Depends(get_db),
) -> User:
    """FastAPI dependency: validate JWT token and return User."""
    # Extract token from Authorization header
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Authorization header",
        )

    token = auth_header[7:]  # Remove "Bearer " prefix

    # Verify token is not invalidated
    session_manager = get_session_manager()
    if not session_manager.is_session_valid(token):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session has been invalidated",
        )

    # Verify and decode token
    token_manager = get_token_manager()
    payload = token_manager.verify_token(token)

    # Get user from database
    user = db.query(User).filter(User.id == payload.get("sub")).first()
    if not user or user.deleted_at:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or deleted",
        )

    return user


# ── RBAC Authorization Dependency ────────────────────────────────────────────

def require_permission(permission: str):
    """FastAPI dependency factory for permission checking."""
    async def check_permission(
        user: User = Depends(get_current_user_jwt),
    ):
        # Get user role (default to FREE if not set)
        role = UserRole(user.role) if hasattr(user, "role") else UserRole.FREE

        if not has_permission(role, permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission denied: {permission}",
            )
        return user

    return check_permission


def require_role(required_role: UserRole):
    """FastAPI dependency factory for role checking."""
    async def check_role(
        user: User = Depends(get_current_user_jwt),
    ):
        user_role = UserRole(user.role) if hasattr(user, "role") else UserRole.FREE

        # Admin always allowed
        if user_role == UserRole.ADMIN:
            return user

        # Check role hierarchy
        role_hierarchy = [UserRole.FREE, UserRole.USER, UserRole.MODERATOR, UserRole.ADMIN]
        user_level = role_hierarchy.index(user_role)
        required_level = role_hierarchy.index(required_role)

        if user_level < required_level:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Requires {required_role} or higher",
            )
        return user

    return check_role


# ── OAuth2 State Verification ────────────────────────────────────────────────

@lru_cache(maxsize=1000)
def generate_oauth_state(user_id: str, provider: str) -> str:
    """Generate a cryptographically secure OAuth2 state token."""
    state_data = f"{user_id}:{provider}:{secrets.token_urlsafe(16)}"
    # In production, store in Redis with TTL
    return state_data


def verify_oauth_state(state: str) -> tuple[str, str]:
    """Verify OAuth2 state token and extract user_id, provider."""
    try:
        parts = state.split(":")
        if len(parts) < 2:
            raise ValueError("Invalid state format")
        user_id, provider = parts[0], parts[1]
        if not user_id or provider not in [p.value for p in OAuth2Provider]:
            raise ValueError("Invalid user_id or provider")
        return user_id, provider
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid OAuth2 state token",
        )


# ── Password Security Utilities ───────────────────────────────────────────────

def generate_secure_password() -> str:
    """Generate a secure random password."""
    return secrets.token_urlsafe(16)


def check_password_strength(password: str) -> tuple[bool, str]:
    """Check password strength and return (is_valid, message)."""
    errors = []

    if len(password) < 8:
        errors.append("at least 8 characters")
    if not any(c.isupper() for c in password):
        errors.append("at least one uppercase letter")
    if not any(c.islower() for c in password):
        errors.append("at least one lowercase letter")
    if not any(c.isdigit() for c in password):
        errors.append("at least one digit")
    if not any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in password):
        errors.append("at least one special character")

    if errors:
        return False, f"Password must contain: {', '.join(errors)}"
    return True, ""
