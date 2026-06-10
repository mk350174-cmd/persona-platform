# Persona Platform API Documentation

**Base URL:** `https://api.persona-hub.com` (production) | `http://localhost:8000` (development)

**API Version:** 1.0.0

**Authentication:** API Key in `X-API-Key` header (required for authenticated endpoints)

**Response Format:** JSON

---

## Table of Contents

1. [System Endpoints](#system-endpoints)
2. [Catalog Endpoints](#catalog-endpoints)
3. [Authentication](#authentication)
4. [Payments & Billing](#payments--billing)
5. [Subscriptions](#subscriptions)
6. [Compilation](#compilation)
7. [Admin Endpoints](#admin-endpoints)
8. [Webhooks](#webhooks)
9. [WebSocket](#websocket)
10. [Error Handling](#error-handling)
11. [Rate Limiting](#rate-limiting)
12. [Examples](#examples)

---

## System Endpoints

### Health Check
```
GET /health
```
**Public endpoint** — No authentication required.

**Response (200 OK):**
```json
{
  "status": "ok",
  "version": "1.0.0",
  "db": true,
  "personas": 495
}
```

**Use case:** Monitoring, load balancer health checks, deployment verification.

---

## Catalog Endpoints

### List All Personas
```
GET /personas
```
**Public endpoint** — Browse entire persona library.

**Query Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `skip` | integer | No | Pagination offset (default: 0) |
| `limit` | integer | No | Items per page (default: 50, max: 500) |
| `search` | string | No | Search by name, description (fuzzy match) |
| `tier` | string | No | Filter by tier (e.g., `basic`, `pro`) |

**Response (200 OK):**
```json
{
  "items": [
    {
      "id": "einstein",
      "name": "Albert Einstein",
      "description": "Theoretical physicist, relativity pioneer",
      "tier": "basic",
      "image_url": "https://api.persona-hub.com/images/einstein.jpg",
      "tags": ["physics", "genius", "scientist"],
      "featured": true
    }
  ],
  "total": 495,
  "skip": 0,
  "limit": 50
}
```

---

### Get Persona Details
```
GET /personas/{persona_id}
```
**Public endpoint** — Get full persona details.

**Path Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `persona_id` | string | Persona identifier (e.g., `einstein`) |

**Response (200 OK):**
```json
{
  "id": "einstein",
  "name": "Albert Einstein",
  "description": "...",
  "tier": "pro",
  "image_url": "...",
  "tags": ["physics", "scientist"],
  "featured": true,
  "voice_id": "einstein_en",
  "model": "persona-needle-26m",
  "capabilities": {
    "compile": true,
    "voice": true,
    "chat": true
  }
}
```

**Error (404 Not Found):**
```json
{
  "detail": "Persona not found"
}
```

---

### Library Statistics
```
GET /personas/stats/library
```
**Public endpoint** — Get library overview statistics.

**Response (200 OK):**
```json
{
  "total_personas": 495,
  "tiers": {
    "basic": 250,
    "pro": 200,
    "expert": 45
  },
  "featured_count": 50,
  "voice_enabled_count": 100,
  "tags": {
    "scientist": 45,
    "historical": 120,
    "philosophy": 60
  }
}
```

---

## Authentication

### Register User
```
POST /auth/register
```
**Public endpoint** — Create new user account.

**Request Body:**
```json
{
  "email": "user@example.com",
  "password": "SecurePassword123!",
  "name": "John Doe"
}
```

**Validation Rules:**
- Email: RFC 5322 format, unique in system
- Password: Minimum 8 characters, at least 1 uppercase, 1 lowercase, 1 digit, 1 special char
- Name: 2-100 characters

**Response (201 Created):**
```json
{
  "id": "usr_abc123",
  "email": "user@example.com",
  "name": "John Doe",
  "api_key": "prs_abc123def456...",
  "email_verified": false,
  "created_at": "2024-06-10T12:00:00Z"
}
```

**Important:** Store the `api_key` securely — you won't be shown it again. Use it in `X-API-Key` header for all authenticated requests.

**Error (400 Bad Request):**
```json
{
  "detail": "Email already registered"
}
```

---

### Request Email Verification
```
POST /auth/request-verification
```
**Public endpoint** — Send verification email.

**Request Body:**
```json
{
  "email": "user@example.com"
}
```

**Response (200 OK):**
```json
{
  "message": "Verification email sent",
  "expires_in_hours": 24
}
```

**Dev Mode:** If `RESEND_API_KEY` is not set, verification link prints to server logs.

---

### Verify Email
```
POST /auth/verify-email
```
**Public endpoint** — Confirm email with token.

**Request Body:**
```json
{
  "token": "evt_abc123def456..."
}
```

**Response (200 OK):**
```json
{
  "message": "Email verified successfully",
  "user_id": "usr_abc123",
  "verified_at": "2024-06-10T12:05:00Z"
}
```

**Error (400 Bad Request):**
```json
{
  "detail": "Token expired or invalid"
}
```

---

### Login
```
POST /auth/login
```
**Public endpoint** — Authenticate with email and password.

**Request Body:**
```json
{
  "email": "user@example.com",
  "password": "SecurePassword123!"
}
```

**Response (200 OK):**
```json
{
  "user_id": "usr_abc123",
  "email": "user@example.com",
  "api_key": "prs_abc123def456...",
  "expires_at": "2024-06-17T12:00:00Z"
}
```

**Security Notes:**
- Failed attempts tracked per IP + email
- 5 consecutive failures → 5-minute lockout
- Constant-time comparison prevents user enumeration
- Lockout clears on successful login

**Error (401 Unauthorized):**
```json
{
  "detail": "Invalid email or password"
}
```

**Error (429 Too Many Requests):**
```json
{
  "detail": "Account locked for 5 minutes due to failed login attempts"
}
```

---

### Get Current User
```
GET /me
```
**Authenticated endpoint** — Get logged-in user profile.

**Headers:**
```
X-API-Key: prs_abc123def456...
```

**Response (200 OK):**
```json
{
  "id": "usr_abc123",
  "email": "user@example.com",
  "name": "John Doe",
  "tier": "pro",
  "email_verified": true,
  "created_at": "2024-06-10T12:00:00Z",
  "stripe_customer_id": "cus_abc123"
}
```

**Error (401 Unauthorized):**
```json
{
  "detail": "Invalid API key"
}
```

---

### Get User Purchases
```
GET /me/purchases
```
**Authenticated endpoint** — List all persona purchases.

**Headers:**
```
X-API-Key: prs_abc123def456...
```

**Query Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `skip` | integer | Pagination offset (default: 0) |
| `limit` | integer | Items per page (default: 50) |

**Response (200 OK):**
```json
{
  "items": [
    {
      "id": "prc_xyz789",
      "persona_id": "einstein",
      "purchase_type": "one-time",
      "amount": 19.99,
      "currency": "USD",
      "created_at": "2024-06-10T12:00:00Z",
      "expires_at": null,
      "deleted_at": null
    }
  ],
  "total": 5
}
```

---

## Payments & Billing

### Create Checkout Session (Single Persona)
```
POST /checkout/{persona_id}
```
**Authenticated endpoint** — Generate Stripe checkout URL.

**Path Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `persona_id` | string | Persona to purchase |

**Query Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `tier` | string | No | `monthly` or `annual` (default: `monthly`) |
| `promo` | string | No | Promo code for discount |
| `ref` | string | No | Referral code (issuer's user ID) |
| `locale` | string | No | Currency/locale (e.g., `en-US`, `de-DE`, `tr-TR`, default: `en-US`) |

**Headers:**
```
X-API-Key: prs_abc123def456...
```

**Response (200 OK):**
```json
{
  "checkout_url": "https://checkout.stripe.com/pay/cs_abc123...",
  "session_id": "cs_abc123...",
  "persona_id": "einstein",
  "price": 19.99,
  "currency": "USD",
  "expires_at": "2024-06-10T13:00:00Z"
}
```

**Logic:**
1. Wallet balance checked for available credits
2. If wallet has credits, deducted automatically
3. Remaining amount charged via Stripe
4. On successful payment, persona access granted

**Error (400 Bad Request):**
```json
{
  "detail": "Promo code invalid or expired"
}
```

---

### Create Bundle Checkout
```
POST /checkout/bundle/{bundle_id}
```
**Authenticated endpoint** — Purchase multiple personas at discounted rate.

**Bundle IDs:**
| ID | Personas | Price | Savings |
|----|----------|-------|---------|
| `bundle-10` | 10 personas | $49 | 34% off individual |
| `bundle-50` | 50 personas | $199 | 40% off individual |
| `bundle-495` | All 495 personas | $999 | 58% off individual |

**Path Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `bundle_id` | string | e.g., `bundle-10`, `bundle-50`, `bundle-495` |

**Query Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `promo` | string | Promo code (optional) |
| `ref` | string | Referral code (optional) |
| `locale` | string | Currency/locale (optional) |

**Response (200 OK):**
```json
{
  "checkout_url": "https://checkout.stripe.com/pay/cs_xyz789...",
  "bundle_id": "bundle-495",
  "bundle_name": "Complete Library",
  "persona_count": 495,
  "price": 999.00,
  "currency": "USD",
  "savings_percent": 58
}
```

---

### Get Wallet Balance
```
GET /me/wallet
```
**Authenticated endpoint** — View credit balance.

**Headers:**
```
X-API-Key: prs_abc123def456...
```

**Response (200 OK):**
```json
{
  "balance": 50.00,
  "currency": "USD",
  "updated_at": "2024-06-10T12:00:00Z",
  "transactions": [
    {
      "id": "wlt_abc123",
      "type": "referral",
      "amount": 5.00,
      "description": "Referral credit from user123",
      "created_at": "2024-06-09T15:30:00Z"
    }
  ]
}
```

---

### Generate Referral Code
```
POST /me/referral-code
```
**Authenticated endpoint** — Create unique referral code.

**Headers:**
```
X-API-Key: prs_abc123def456...
```

**Response (200 OK):**
```json
{
  "code": "REF_abc123",
  "user_id": "usr_abc123",
  "created_at": "2024-06-10T12:00:00Z",
  "credit_per_referral": 5.00,
  "total_referrals": 3,
  "total_credits_issued": 15.00
}
```

**Referral Flow:**
1. User A generates referral code `REF_abc123`
2. User B registers with code `REF_abc123` in email
3. User B makes first purchase
4. User A receives $5 credit automatically
5. User B can use credit for future purchases

---

### Get User Invoices
```
GET /me/invoices
```
**Authenticated endpoint** — List purchase invoices.

**Headers:**
```
X-API-Key: prs_abc123def456...
```

**Query Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `skip` | integer | Offset (default: 0) |
| `limit` | integer | Items per page (default: 50) |

**Response (200 OK):**
```json
{
  "items": [
    {
      "id": "inv_abc123",
      "stripe_invoice_id": "in_abc123...",
      "amount": 19.99,
      "currency": "USD",
      "status": "paid",
      "description": "Einstein Persona Purchase",
      "created_at": "2024-06-10T12:00:00Z",
      "paid_at": "2024-06-10T12:05:00Z",
      "invoice_url": "https://stripe.com/..."
    }
  ],
  "total": 5
}
```

---

### Create Billing Portal Session
```
POST /billing/portal
```
**Authenticated endpoint** — Redirect to Stripe customer portal.

**Headers:**
```
X-API-Key: prs_abc123def456...
```

**Response (200 OK):**
```json
{
  "portal_url": "https://billing.stripe.com/session/cs_test_abc123...",
  "redirect_url": "https://persona-hub.com/dashboard"
}
```

**Use case:** User management of subscriptions, payment methods, invoices via Stripe dashboard.

---

## Subscriptions

### List Subscription Tiers
```
GET /subscription/tiers
```
**Public endpoint** — Available subscription options.

**Response (200 OK):**
```json
{
  "tiers": [
    {
      "id": "basic_monthly",
      "name": "Basic (Monthly)",
      "price": 19.99,
      "currency": "USD",
      "billing_period": "monthly",
      "persona_limit": 10,
      "features": ["chat", "compile", "basic-voice"]
    },
    {
      "id": "pro_monthly",
      "name": "Pro (Monthly)",
      "price": 49.99,
      "currency": "USD",
      "billing_period": "monthly",
      "persona_limit": 100,
      "features": ["chat", "compile", "premium-voice", "priority-support"]
    },
    {
      "id": "basic_annual",
      "name": "Basic (Annual)",
      "price": 99.00,
      "currency": "USD",
      "billing_period": "annual",
      "persona_limit": 10,
      "features": ["chat", "compile", "basic-voice"],
      "discount_percent": 20
    },
    {
      "id": "pro_annual",
      "name": "Pro (Annual)",
      "price": 290.00,
      "currency": "USD",
      "billing_period": "annual",
      "persona_limit": 100,
      "features": ["chat", "compile", "premium-voice", "priority-support"],
      "discount_percent": 20
    }
  ]
}
```

---

### Create Subscription
```
POST /subscribe/{tier}
```
**Authenticated endpoint** — Subscribe to a tier.

**Path Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `tier` | string | Subscription tier ID (e.g., `pro_monthly`, `basic_annual`) |

**Headers:**
```
X-API-Key: prs_abc123def456...
```

**Response (200 OK):**
```json
{
  "checkout_url": "https://checkout.stripe.com/pay/cs_abc123...",
  "subscription_id": "sub_abc123",
  "tier": "pro_monthly",
  "amount": 49.99,
  "billing_cycle_starts": "2024-06-10",
  "billing_cycle_ends": "2024-07-10"
}
```

---

### Get Current Subscription
```
GET /me/subscription
```
**Authenticated endpoint** — Active subscription details.

**Headers:**
```
X-API-Key: prs_abc123def456...
```

**Response (200 OK):**
```json
{
  "id": "sub_abc123",
  "tier": "pro_monthly",
  "amount": 49.99,
  "currency": "USD",
  "billing_period": "monthly",
  "status": "active",
  "current_period_start": "2024-06-10",
  "current_period_end": "2024-07-10",
  "next_billing_date": "2024-07-10",
  "auto_renew": true
}
```

**Error (404 Not Found):**
```json
{
  "detail": "No active subscription"
}
```

---

### Cancel Subscription
```
DELETE /me/subscription
```
**Authenticated endpoint** — Cancel active subscription.

**Headers:**
```
X-API-Key: prs_abc123def456...
```

**Response (200 OK):**
```json
{
  "message": "Subscription cancelled",
  "subscription_id": "sub_abc123",
  "effective_date": "2024-07-10",
  "final_billing_date": "2024-07-10"
}
```

---

## Compilation

### Compile Persona
```
POST /v1/compile/{persona_id}
```
**Authenticated endpoint** — Generate persona model/weights.

**Path Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `persona_id` | string | Persona to compile (must own/purchase) |

**Headers:**
```
X-API-Key: prs_abc123def456...
```

**Query Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `tier` | string | `basic`, `pro`, `expert` (default: `pro`) |
| `format` | string | `pytorch`, `onnx`, `safetensors` (default: `pytorch`) |

**Response (200 OK):**
```json
{
  "compilation_id": "cmp_abc123",
  "persona_id": "einstein",
  "status": "completed",
  "tier": "pro",
  "format": "pytorch",
  "file_size_mb": 450,
  "download_url": "https://api.persona-hub.com/downloads/cmp_abc123/model.pth",
  "checksum": "sha256:abc123...",
  "compiled_at": "2024-06-10T12:05:00Z",
  "expires_at": "2024-06-17T12:05:00Z"
}
```

**Download Expiry:** Links valid for 7 days; re-compile if expired.

---

### Compile All Platforms
```
POST /v1/compile/{persona_id}/all-platforms
```
**Authenticated endpoint** — Generate for iOS, Android, Web, Desktop.

**Headers:**
```
X-API-Key: prs_abc123def456...
```

**Response (200 OK):**
```json
{
  "compilation_id": "cmp_abc123",
  "persona_id": "einstein",
  "status": "completed",
  "platforms": {
    "ios": {
      "file_size_mb": 120,
      "download_url": "...",
      "checksum": "sha256:..."
    },
    "android": {
      "file_size_mb": 130,
      "download_url": "...",
      "checksum": "sha256:..."
    },
    "web": {
      "file_size_mb": 95,
      "download_url": "...",
      "checksum": "sha256:..."
    },
    "desktop": {
      "file_size_mb": 140,
      "download_url": "...",
      "checksum": "sha256:..."
    }
  }
}
```

---

### Compile All Tiers
```
POST /v1/compile/{persona_id}/all-tiers
```
**Authenticated endpoint** — Generate basic, pro, expert models.

**Headers:**
```
X-API-Key: prs_abc123def456...
```

**Response (200 OK):**
```json
{
  "compilation_id": "cmp_abc123",
  "persona_id": "einstein",
  "tiers": {
    "basic": {
      "size_mb": 120,
      "download_url": "...",
      "params": 26000000
    },
    "pro": {
      "size_mb": 450,
      "download_url": "...",
      "params": 26000000
    },
    "expert": {
      "size_mb": 1200,
      "download_url": "...",
      "params": 26000000
    }
  }
}
```

---

### Generate Voice
```
POST /v1/compile/{persona_id}/voice
```
**Authenticated endpoint** — Generate MP3 voice synthesis.

**Headers:**
```
X-API-Key: prs_abc123def456...
```

**Query Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `text` | string | Text to synthesize (1-500 characters) |
| `language` | string | `en`, `es`, `fr`, `de`, `tr`, `ja` (default: `en`) |
| `voice_preset` | string | `default`, `calm`, `energetic`, `formal` |

**Response (200 OK):**
```json
{
  "voice_id": "v_abc123",
  "persona_id": "einstein",
  "text": "Hello, I am Albert Einstein...",
  "language": "en",
  "voice_preset": "calm",
  "file_size_kb": 150,
  "duration_seconds": 8.5,
  "download_url": "https://api.persona-hub.com/downloads/v_abc123/voice.mp3",
  "checksum": "sha256:xyz789...",
  "generated_at": "2024-06-10T12:00:00Z"
}
```

---

## Admin Endpoints

### Refund Purchase
```
POST /admin/refund/{purchase_id}
```
**Admin-only endpoint** — Refund and revoke persona access.

**Path Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `purchase_id` | string | Purchase to refund |

**Headers:**
```
X-API-Key: admin_key_...
```

**Request Body:**
```json
{
  "reason": "User requested refund"
}
```

**Response (200 OK):**
```json
{
  "purchase_id": "prc_abc123",
  "refund_id": "ref_abc123",
  "amount": 19.99,
  "currency": "USD",
  "status": "completed",
  "user_access_revoked": true,
  "refunded_at": "2024-06-10T12:00:00Z"
}
```

**Security:** Admin role required; action logged to audit_log table.

---

## Webhooks

### Stripe Events
```
POST /webhook/stripe
```
**Webhook endpoint** — Receive payment updates from Stripe.

**Security:**
- Signed with Stripe signature (`Stripe-Signature` header)
- Processed within 10 minutes or rejected
- Idempotent: duplicate events ignored via StripeEvent table

**Events Handled:**
| Event | Action |
|-------|--------|
| `checkout.session.completed` | Grant persona access, issue referral credits |
| `invoice.payment_succeeded` | Record invoice, update subscription |
| `invoice.payment_failed` | Log failure, disable auto-renew |
| `customer.subscription.deleted` | Revoke subscription access |

**Request (from Stripe):**
```
POST /webhook/stripe
Stripe-Signature: t=1234567890,v1=abc123...
Content-Type: application/json

{
  "id": "evt_abc123",
  "type": "checkout.session.completed",
  "data": {
    "object": {
      "id": "cs_abc123",
      "customer": "cus_abc123",
      "payment_status": "paid"
    }
  }
}
```

**Response (200 OK):**
```json
{
  "received": true
}
```

---

## WebSocket

### Chat with Persona
```
WebSocket /ws/chat/{persona_id}
```
**WebSocket endpoint** — Real-time conversation with persona.

**Headers:**
```
Authorization: Bearer {api_key}
```

**Connection Flow:**

1. **Connect:**
   ```
   ws://localhost:8000/ws/chat/einstein
   ```

2. **Send Message:**
   ```json
   {
     "type": "message",
     "text": "What is your theory of relativity?",
     "user_id": "usr_abc123"
   }
   ```

3. **Receive Response:**
   ```json
   {
     "type": "response",
     "text": "The theory of relativity...",
     "persona_id": "einstein",
     "timestamp": "2024-06-10T12:00:00Z"
   }
   ```

4. **Error:**
   ```json
   {
     "type": "error",
     "message": "Persona not found or access denied",
     "code": "PERSONA_NOT_FOUND"
   }
   ```

**Connection Requirements:**
- Valid API key (X-API-Key header or URL param)
- Must own or have purchased persona
- Max 10 concurrent connections per user
- Idle timeout: 30 minutes

---

## Error Handling

### Error Response Format
```json
{
  "detail": "Human-readable error message",
  "error_code": "ERROR_CODE",
  "request_id": "req_abc123"
}
```

### HTTP Status Codes

| Code | Meaning | Retry? |
|------|---------|--------|
| 200 | Success | — |
| 201 | Created | — |
| 400 | Bad Request | No |
| 401 | Unauthorized | No |
| 403 | Forbidden | No |
| 404 | Not Found | No |
| 429 | Rate Limited | Yes (with backoff) |
| 500 | Server Error | Yes (with backoff) |
| 503 | Service Unavailable | Yes (with backoff) |

### Common Errors

| Error | Status | Cause | Solution |
|-------|--------|-------|----------|
| `INVALID_API_KEY` | 401 | Missing/expired key | Regenerate API key |
| `PERSONA_NOT_FOUND` | 404 | Invalid persona_id | Check persona_id exists |
| `ACCESS_DENIED` | 403 | Don't own persona | Purchase before compile |
| `RATE_LIMIT_EXCEEDED` | 429 | Too many requests | Reduce frequency, use backoff |
| `STRIPE_ERROR` | 400 | Payment issue | Check Stripe dashboard |
| `EMAIL_NOT_VERIFIED` | 403 | Email verification required | Verify email first |

---

## Rate Limiting

### Limits Per API Key

| Endpoint | Limit | Window |
|----------|-------|--------|
| `/personas` | 1000 | 1 hour |
| `/v1/compile/*` | 100 | 1 hour |
| `/checkout/*` | 50 | 1 hour |
| `/ws/chat` | 10 concurrent | Per session |
| Default (other) | 500 | 1 hour |

### Rate Limit Headers

**Response Headers:**
```
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 999
X-RateLimit-Reset: 1623336000
X-RateLimit-Reset-After: 3599
```

### Backoff Strategy

```python
import time
for attempt in range(4):  # Max 4 retries
    response = requests.get(url, headers={'X-API-Key': key})
    if response.status_code == 429:
        wait_time = 2 ** attempt  # 1s, 2s, 4s, 8s
        time.sleep(wait_time)
    elif response.ok:
        break
    else:
        raise Exception(response.text)
```

---

## Examples

### Register and Purchase

```bash
# 1. Register
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "alice@example.com",
    "password": "SecurePass123!",
    "name": "Alice"
  }'

# Response:
# {
#   "api_key": "prs_abc123def456...",
#   "email": "alice@example.com"
# }

# 2. Get checkout URL
curl -X POST http://localhost:8000/checkout/einstein \
  -H "X-API-Key: prs_abc123def456..." \
  -H "Content-Type: application/json"

# Response:
# {
#   "checkout_url": "https://checkout.stripe.com/pay/cs_abc123..."
# }

# 3. User visits checkout_url, completes Stripe payment
# 4. Webhook fires: persona access granted automatically
# 5. User can now compile

# 5. Compile persona
curl -X POST "http://localhost:8000/v1/compile/einstein?tier=pro" \
  -H "X-API-Key: prs_abc123def456..."

# Response:
# {
#   "download_url": "https://api.persona-hub.com/downloads/cmp_abc123/model.pth",
#   "file_size_mb": 450
# }
```

### Subscription Flow

```bash
# Get tiers
curl http://localhost:8000/subscription/tiers

# Subscribe to Pro (annual, 20% off)
curl -X POST http://localhost:8000/subscribe/pro_annual \
  -H "X-API-Key: prs_abc123def456..."

# Response includes Stripe checkout URL

# Check subscription status
curl http://localhost:8000/me/subscription \
  -H "X-API-Key: prs_abc123def456..."

# Cancel anytime
curl -X DELETE http://localhost:8000/me/subscription \
  -H "X-API-Key: prs_abc123def456..."
```

### Multi-Currency Example

```bash
# Purchase in EUR
curl -X POST "http://localhost:8000/checkout/einstein?locale=de-DE" \
  -H "X-API-Key: prs_abc123def456..."

# Response:
# {
#   "price": 17.99,
#   "currency": "EUR"
# }

# Purchase in TRY (Turkish Lira)
curl -X POST "http://localhost:8000/checkout/einstein?locale=tr-TR" \
  -H "X-API-Key: prs_abc123def456..."

# Response:
# {
#   "price": 353.50,
#   "currency": "TRY"
# }
```

---

## Support

- **Interactive Docs:** `http://localhost:8000/docs` (Swagger UI)
- **Alternative Docs:** `http://localhost:8000/redoc` (ReDoc)
- **GitHub Issues:** https://github.com/mk350174-cmd/persona-platform/issues
- **Email:** support@persona-hub.com
