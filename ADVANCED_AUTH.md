# Advanced API Security — H96

**Purpose:** OAuth2 integration, JWT with refresh tokens, RBAC (role-based access control), session management.

**Key Features:**
- OAuth2 (Google, GitHub) for social login
- JWT tokens (short-lived access + long-lived refresh)
- RBAC with granular permissions
- Session invalidation on logout
- Password strength validation
- Admin user management

---

## Architecture

### Authentication Flows

#### 1. OAuth2 (Google/GitHub)

```
Client → /auth/oauth/google → Authorization URL
↓
Client → Google Authorization Server → Redirect with code
↓
API → POST /auth/oauth/google/callback?code=...&state=...
↓
API ← Google Token Endpoint ← Exchange code for access token
↓
API ← Google User Info Endpoint ← Get email, profile
↓
API → Create/link user in database
↓
API → Generate JWT tokens (access + refresh)
↓
Client ← JWT tokens (store in secure storage)
```

#### 2. JWT Token Refresh

```
Client → /auth/oauth/token + refresh_token
↓
API → Validate refresh token (long-lived)
↓
API → Generate new access token (short-lived, 15 min)
↓
Client ← New access token
```

#### 3. Session Invalidation (Logout)

```
Client → POST /auth/logout + Authorization: Bearer {token}
↓
API → Hash token, store in InvalidatedSession table
↓
API → Add to session_manager.invalidated_tokens
↓
API → Return success
↓
Client ← OK (client discards token)
↓
Subsequent requests → 401 (token in blacklist)
```

### RBAC (Role-Based Access Control)

**Roles:**
- `admin` — Full access to all endpoints
- `moderator` — Can read all users, flag content, read audit logs
- `user` — Standard user access (compile personas, read own profile)
- `free` — Free tier (read personas only)

**Permissions:**
```python
{
    "admin": {
        "users:read_all",
        "users:write_all",
        "policies:write",
        "rollback:execute_immediate",
        "audit:read",
        "settings:write",
    },
    "moderator": {
        "users:read_all",
        "personas:flag_abuse",
        "audit:read",
        "rollback:execute_with_approval",
    },
    "user": {
        "personas:read",
        "personas:compile",
        "users:read_own",
        "users:write_own",
        "orders:read_own",
    },
    "free": {
        "personas:read",
        "users:read_own",
    },
}
```

---

## Setup Guide

### 1. JWT Configuration

Set environment variables:

```bash
export JWT_SECRET_KEY="your-secret-key-here"  # 32+ chars, keep secure
export JWT_ACCESS_TOKEN_LIFETIME_MINUTES=15   # Access token TTL
export JWT_REFRESH_TOKEN_LIFETIME_DAYS=7      # Refresh token TTL
```

In production, use a key management service (AWS KMS, HashiCorp Vault, etc.):

```python
# api/advanced_auth.py (already configured)
self.secret_key = os.getenv("JWT_SECRET_KEY", secrets.token_urlsafe(32))
```

### 2. Google OAuth2 Setup

#### Step 1: Create OAuth2 Credentials in Google Cloud Console

1. Go to https://console.cloud.google.com/
2. Create a new project
3. Enable Google+ API
4. Create OAuth2 credentials (Web application)
5. Add authorized redirect URIs:
   - http://localhost:8000/auth/oauth/google/callback (development)
   - https://api.yourdomain.com/auth/oauth/google/callback (production)

#### Step 2: Set Environment Variables

```bash
export GOOGLE_OAUTH_CLIENT_ID="..."
export GOOGLE_OAUTH_CLIENT_SECRET="..."
export GOOGLE_OAUTH_REDIRECT_URI="http://localhost:8000/auth/oauth/google/callback"
```

#### Step 3: Test Flow

```bash
# Get authorization URL
curl http://localhost:8000/auth/oauth/google

# Redirect user to returned auth_url
# User authorizes app in Google
# Browser redirects to callback with code parameter
# API exchanges code for tokens and creates user
```

### 3. GitHub OAuth2 Setup

#### Step 1: Create OAuth App in GitHub Settings

1. Go to https://github.com/settings/developers
2. Click "New OAuth App"
3. Fill in:
   - Application name: "Persona Platform"
   - Homepage URL: http://localhost:8000
   - Authorization callback URL: http://localhost:8000/auth/oauth/github/callback

#### Step 2: Set Environment Variables

```bash
export GITHUB_OAUTH_CLIENT_ID="..."
export GITHUB_OAUTH_CLIENT_SECRET="..."
export GITHUB_OAUTH_REDIRECT_URI="http://localhost:8000/auth/oauth/github/callback"
```

#### Step 3: Test Flow

```bash
# Get authorization URL
curl http://localhost:8000/auth/oauth/github

# Redirect user to returned auth_url
# User authorizes app in GitHub
# Browser redirects to callback with code parameter
# API exchanges code for tokens and creates user
```

### 4. Database Migrations

Create migration file:

```bash
alembic revision -m "H96: Advanced authentication (OAuth2, JWT, RBAC)"
```

The migration (auto-created via `init_db()`) will create:
- oauth2_credentials table
- invalidated_sessions table
- Add role column to users table

Verify:

```bash
sqlite3 persona_store.db ".schema oauth2_credentials"
sqlite3 persona_store.db ".schema invalidated_sessions"
```

---

## API Reference

### OAuth2 Endpoints

#### GET /auth/oauth/google

Get Google authorization URL.

**Response:**
```json
{
  "auth_url": "https://accounts.google.com/o/oauth2/v2/auth?client_id=...",
  "state": "temp:google:..."
}
```

Redirect user to `auth_url`. User grants permission, then Google redirects to callback.

#### GET /auth/oauth/github

Get GitHub authorization URL.

**Response:**
```json
{
  "auth_url": "https://github.com/login/oauth/authorize?client_id=...",
  "state": "temp:github:..."
}
```

#### GET /auth/oauth/google/callback

Callback handler (browser redirect).

**Parameters:**
- `code` — Authorization code from Google
- `state` — State token for verification

**Response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "user_id": "abc123...",
  "email": "user@example.com"
}
```

#### GET /auth/oauth/github/callback

Callback handler (browser redirect).

**Parameters:**
- `code` — Authorization code from GitHub
- `state` — State token for verification

**Response:** Same as Google callback

### JWT Token Endpoints

#### POST /auth/oauth/token

Refresh access token using refresh token.

**Request:**
```json
{
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

**Response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 900
}
```

### Session Management

#### POST /auth/logout

Invalidate current session.

**Authentication:** Bearer {access_token}

**Response:**
```json
{
  "status": "logged_out",
  "message": "Session invalidated",
  "user_id": "abc123..."
}
```

#### POST /auth/logout/all

Invalidate all sessions for user (security lock).

**Authentication:** Bearer {access_token}

**Response:**
```json
{
  "status": "all_sessions_invalidated",
  "message": "All sessions have been terminated",
  "user_id": "abc123..."
}
```

### User Profile

#### GET /auth/me

Get current user's profile.

**Authentication:** Bearer {access_token}

**Response:**
```json
{
  "id": "abc123...",
  "email": "user@example.com",
  "role": "user",
  "active": true,
  "email_verified": true,
  "created_at": "2024-06-10T12:00:00Z",
  "oauth_providers": [
    {
      "provider": "google",
      "connected_at": "2024-06-10T12:00:00Z",
      "last_used_at": "2024-06-10T15:30:00Z"
    }
  ]
}
```

#### PATCH /auth/me/password

Change password.

**Authentication:** Bearer {access_token}

**Request:**
```json
{
  "old_password": "CurrentPassword123!",
  "new_password": "NewPassword456!"
}
```

**Response:**
```json
{
  "status": "password_changed",
  "message": "Password changed. Please login again."
}
```

### User Management (Admin)

#### GET /auth/users/{user_id}

Get user profile (requires users:read_all permission).

**Authentication:** Bearer {access_token}

**Response:**
```json
{
  "id": "abc123...",
  "email": "user@example.com",
  "role": "user",
  "active": true,
  "created_at": "2024-06-10T12:00:00Z",
  "email_verified": true
}
```

#### PATCH /auth/users/{user_id}/role

Update user's role (admin only).

**Authentication:** Bearer {access_token}

**Request:**
```json
{
  "new_role": "moderator"
}
```

**Response:**
```json
{
  "status": "role_updated",
  "user_id": "abc123...",
  "role": "moderator"
}
```

#### DELETE /auth/users/{user_id}

Soft-delete user (admin only).

**Authentication:** Bearer {access_token}

**Response:**
```json
{
  "status": "user_deleted",
  "user_id": "abc123...",
  "deleted_at": "2024-06-10T16:00:00Z"
}
```

### RBAC & Permissions

#### GET /auth/permissions

Get current user's permissions.

**Authentication:** Bearer {access_token}

**Response:**
```json
{
  "user_id": "abc123...",
  "role": "user",
  "permissions": [
    "personas:read",
    "personas:compile",
    "users:read_own",
    "users:write_own",
    "orders:read_own"
  ]
}
```

#### GET /auth/roles

List all available roles.

**Response:**
```json
{
  "roles": [
    {
      "name": "admin",
      "description": "Admin user"
    },
    {
      "name": "moderator",
      "description": "Moderator user"
    },
    {
      "name": "user",
      "description": "User user"
    },
    {
      "name": "free",
      "description": "Free user"
    }
  ]
}
```

---

## Integration Guide

### 1. Protect Endpoints with JWT

```python
from api.advanced_auth import get_current_user_jwt

@app.get("/protected")
def protected_endpoint(
    user: User = Depends(get_current_user_jwt),
):
    return {"user_id": user.id, "email": user.email}
```

### 2. Require Specific Permission

```python
from api.advanced_auth import require_permission

@app.delete("/users/{user_id}")
def delete_user(
    user_id: str,
    current_user: User = Depends(require_permission("users:write_all")),
):
    # This endpoint requires users:write_all permission
    pass
```

### 3. Require Specific Role

```python
from api.advanced_auth import require_role, UserRole

@app.patch("/policies")
def update_policy(
    current_user: User = Depends(require_role(UserRole.ADMIN)),
):
    # This endpoint requires admin role or higher
    pass
```

### 4. Check Permission in Code

```python
from api.advanced_auth import has_permission, UserRole

user_role = UserRole(user.role)
if has_permission(user_role, "policies:write"):
    # User has permission
    pass
```

### 5. Client-Side Implementation

```javascript
// Authenticate with Google
async function loginWithGoogle() {
  const response = await fetch('/auth/oauth/google');
  const {auth_url} = await response.json();
  window.location.href = auth_url;  // Redirect to Google
}

// Handle callback
async function handleCallback() {
  const params = new URLSearchParams(window.location.search);
  const code = params.get('code');
  const state = params.get('state');
  
  const response = await fetch('/auth/oauth/google/callback', {
    method: 'GET',
    headers: {'Accept': 'application/json'}
  });
  
  const {access_token, refresh_token} = await response.json();
  
  // Store in localStorage (or preferably: secure httpOnly cookie)
  localStorage.setItem('access_token', access_token);
  localStorage.setItem('refresh_token', refresh_token);
}

// Make authenticated request
async function fetchProtected(url) {
  const token = localStorage.getItem('access_token');
  const response = await fetch(url, {
    headers: {'Authorization': `Bearer ${token}`}
  });
  
  // If 401, refresh token
  if (response.status === 401) {
    const refreshToken = localStorage.getItem('refresh_token');
    const newTokenResponse = await fetch('/auth/oauth/token', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({refresh_token: refreshToken})
    });
    
    const {access_token} = await newTokenResponse.json();
    localStorage.setItem('access_token', access_token);
    
    // Retry original request
    return fetchProtected(url);
  }
  
  return response;
}

// Logout
async function logout() {
  const token = localStorage.getItem('access_token');
  await fetch('/auth/logout', {
    method: 'POST',
    headers: {'Authorization': `Bearer ${token}`}
  });
  
  localStorage.removeItem('access_token');
  localStorage.removeItem('refresh_token');
  window.location.href = '/';
}
```

---

## Security Considerations

### Token Storage

**Not Recommended:**
```javascript
// DON'T: localStorage vulnerable to XSS
localStorage.setItem('token', token);

// DON'T: sessionStorage also vulnerable to XSS
sessionStorage.setItem('token', token);
```

**Recommended:**
```javascript
// DO: httpOnly cookie (secure, not accessible to JS)
// Server sets: Set-Cookie: token=...; HttpOnly; Secure; SameSite=Strict
// Browser automatically includes in requests
```

**For SPAs:**
```javascript
// DO: Store in memory variable (lost on refresh, OK)
let accessToken = null;

// OR: Use refresh token in httpOnly cookie, store access token in memory
```

### CORS Configuration

Configure CORS to only allow trusted origins:

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://yourdomain.com"],  # NOT "*"
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)
```

### Session Invalidation

On logout, tokens are invalidated immediately. However:

1. **Access token cache:** If API caches user data by token, clear cache on logout
2. **Distributed systems:** Use Redis for session management (current implementation uses in-memory)
3. **Token expiry:** Access tokens expire in 15 minutes, providing some protection

### Password Strength

Enforced password requirements:
- Minimum 8 characters
- At least one uppercase letter
- At least one lowercase letter
- At least one digit
- At least one special character (!@#$%^&*()_+=-[]{}|;:,.<>?)

### Rate Limiting

Apply rate limiting to auth endpoints:

```python
from slowapi import Limiter

limiter = Limiter(key_func=get_remote_address)

@router.post("/oauth/token")
@limiter.limit("5/minute")  # 5 requests per minute
def refresh_access_token(...):
    pass
```

---

## Troubleshooting

### OAuth2 Callback Fails

**Issue:** "Invalid state token"

**Solution:**
1. Verify state token is passed correctly
2. Check environment variables (GOOGLE_OAUTH_CLIENT_ID, etc.)
3. Verify redirect URI matches in provider console
4. Check server logs for detailed error

### JWT Token Rejected

**Issue:** "Invalid token" or "Token has expired"

**Solution:**
1. Verify JWT_SECRET_KEY is consistent (don't rotate without migration)
2. Check token expiry: decode JWT at jwt.io (online decoder)
3. Refresh token if expired: POST /auth/oauth/token
4. Verify Authorization header format: "Bearer {token}"

### Permission Denied

**Issue:** 403 Forbidden for admin endpoint

**Solution:**
1. Check user's role: GET /auth/me
2. Check required permission: GET /auth/permissions
3. Verify role has permission in ROLE_PERMISSIONS dict
4. Admin can change role: PATCH /auth/users/{user_id}/role

### Sessions Not Invalidated

**Issue:** User can still access after logout

**Solution:**
1. In production, use Redis for session manager (currently in-memory)
2. Check invalidated_sessions table: `SELECT * FROM invalidated_sessions`
3. Ensure logout endpoint was called before discarding token
4. Check token hasn't been refreshed (new token is valid)

---

## Performance Considerations

### Token Validation

Current implementation validates JWT signature on every request (< 1ms).

**For higher load:**
1. Cache token claims in Redis with short TTL
2. Use async signature validation
3. Batch-validate multiple tokens

### Session Storage

Current implementation:
- In-memory set (single process)
- Limited to ~100K invalidated tokens
- Lost on server restart

**Production:**
```python
# Use Redis for distributed session management
import redis

class SessionManager:
    def __init__(self):
        self.redis = redis.Redis(host='redis', port=6379)
    
    def invalidate_session(self, token: str, user_id: str):
        self.redis.setex(f"invalid_token:{token}", 3600*24, "1")
    
    def is_session_valid(self, token: str) -> bool:
        return not self.redis.exists(f"invalid_token:{token}")
```

### OAuth2 Token Refresh

Current implementation makes HTTP request to provider on refresh. For higher load:
1. Cache access tokens with TTL (but less secure)
2. Use provider's refresh token (already supported for Google)
3. Implement token refresh in background job

---

## Deployment Checklist

- [ ] Set JWT_SECRET_KEY (unique per environment)
- [ ] Configure Google OAuth2 (or skip if not using)
- [ ] Configure GitHub OAuth2 (or skip if not using)
- [ ] Run database migrations: `alembic upgrade head`
- [ ] Test OAuth2 flow (Google, GitHub)
- [ ] Test JWT token refresh
- [ ] Test logout (session invalidation)
- [ ] Test RBAC (admin, moderator, user roles)
- [ ] Enable HTTPS/TLS in production
- [ ] Configure CORS for your domain
- [ ] Set rate limits on auth endpoints
- [ ] Monitor failed login attempts
- [ ] Set up session cleanup job (purge expired tokens)

---

## References

- **JWT:** https://jwt.io/
- **OAuth2:** https://oauth.net/2/
- **OWASP Auth Cheat Sheet:** https://cheatsheetseries.owasp.org/cheatsheets/Authentication_Cheat_Sheet.html
- **Google OAuth2:** https://developers.google.com/identity/protocols/oauth2
- **GitHub OAuth2:** https://docs.github.com/en/developers/apps/building-oauth-apps
