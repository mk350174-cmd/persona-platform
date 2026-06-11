# Persona Hub Integration Guide

Complete guide for connecting the frontend to the FastAPI backend.

---

## Overview

The frontend is fully configured to communicate with the FastAPI backend through:
- **REST API** (40+ endpoints)
- **WebSocket** (real-time chat + notifications)
- **Health checks** (monitoring + diagnostics)

---

## Prerequisites

### Backend Requirements
- FastAPI server running on `http://localhost:8000` (development)
- Database configured (PostgreSQL recommended)
- All API endpoints implemented
- WebSocket support enabled
- CORS configured properly

### Frontend Prerequisites
- Node 18+
- All dependencies installed (`npm install`)
- Environment variables configured

---

## Step 1: Configure Environment

### Development (.env.development)

```env
# API Configuration
VITE_API_URL=http://localhost:8000/api
VITE_WS_URL=ws://localhost:8000

# Feature Flags
VITE_ENABLE_ANALYTICS=true
VITE_ENABLE_VOICE=true
VITE_ENABLE_PWA=true

# Optional Services
VITE_SENTRY_DSN=
VITE_GA_TRACKING_ID=
```

### Production (.env.production)

```env
# API Configuration (use your domain)
VITE_API_URL=https://api.persona-hub.com/api
VITE_WS_URL=wss://api.persona-hub.com

# Feature Flags
VITE_ENABLE_ANALYTICS=true
VITE_ENABLE_VOICE=true
VITE_ENABLE_PWA=true

# Error Tracking
VITE_SENTRY_DSN=https://your-sentry-dsn@sentry.io/project-id
```

---

## Step 2: Start Development Servers

### Terminal 1: Backend (FastAPI)

```bash
cd api
python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Expected output:
```
INFO:     Uvicorn running on http://0.0.0.0:8000
INFO:     Application startup complete
```

### Terminal 2: Frontend (React/Vite)

```bash
cd frontend
npm run dev
```

Expected output:
```
VITE v8.0.16  ready in 456 ms

➜  Local:   http://localhost:5173/
➜  press h to show help
```

### Terminal 3: Monitor Backend (optional)

```bash
# Watch logs for errors
tail -f api/logs/app.log
```

---

## Step 3: Health Checks

### Browser Console

```javascript
// Check API connectivity
import { health } from './services/health.js';

// Run diagnostics
const diagnostics = await health.runDiagnostics();
console.log(diagnostics);
```

Expected output:
```json
{
  "status": "healthy",
  "checks": {
    "api": { "status": "ok", "data": { ... } },
    "cache": { "status": "ok", "cache": { ... } }
  }
}
```

### Network Tab (Chrome DevTools)

1. Open DevTools → Network tab
2. Filter by `/api`
3. Verify requests show status 200
4. Check response times (<500ms target)

### WebSocket Connection (Chrome DevTools)

1. Network tab → Filter by `WS`
2. Connect to a persona chat
3. Verify WebSocket shows status 101 (Switching Protocols)
4. Monitor message streaming

---

## Step 4: Test Core Workflows

### Workflow 1: Authentication

```javascript
import { api } from './services/api.js';

// 1. Login
const loginResponse = await api.login('user@example.com', 'password');
console.log('Login response:', loginResponse.data);
// Expected: { api_key: 'prs_...', user_id: '...', email: '...' }

// 2. Get current user
const userResponse = await api.getMe();
console.log('Current user:', userResponse.data);
// Expected: { id: '...', email: '...', role: 'user' }

// 3. Store API key
localStorage.setItem('api_key', loginResponse.data.api_key);
```

### Workflow 2: Browse Personas

```javascript
import { api } from './services/api.js';

// 1. Get catalog
const catalog = await api.getCatalog();
console.log('Personas count:', catalog.data.length);

// 2. Get single persona
const persona = await api.getPersona('socrates');
console.log('Persona:', persona.data);
// Expected: { id, name, emoji, domain, description, ... }

// 3. Search with filters
const filtered = await api.listPersonas({
  domain: 'Philosophy',
  price_max: 50,
});
```

### Workflow 3: Real-time Chat

```javascript
// In React component
import { useWebSocket } from './hooks/useWebSocket.js';

function ChatComponent() {
  const { messages, sendMessage, isConnected } = useWebSocket('socrates', apiKey);

  return (
    <>
      <div className="messages">
        {messages.map((msg) => (
          <div key={msg.id} className={msg.role}>
            {msg.content}
          </div>
        ))}
      </div>
      <input onSend={(text) => sendMessage(text)} />
    </>
  );
}
```

### Workflow 4: Analytics

```javascript
import { api } from './services/api.js';

// 1. Get dashboard
const dashboard = await api.getDashboard();
console.log('Active users:', dashboard.data.activeUsers);

// 2. Get top personas
const topPersonas = await api.getTopPersonas(10);
console.log('Top 10:', topPersonas.data);

// 3. Export data
const csvBlob = await api.exportAnalytics('csv');
const url = URL.createObjectURL(csvBlob);
// Download or process CSV
```

### Workflow 5: Real-time Notifications

```javascript
import { notificationManager } from './services/notifications.js';

// Initialize (called in App.jsx)
notificationManager.init(apiKey, userId);

// Listen for notifications
notificationManager.on('notification', (notification) => {
  console.log('New notification:', notification);
  // notification = {
  //   type: 'success|error|warning|info',
  //   title: '...',
  //   body: '...',
  //   action: { type: '...', data: {...} }
  // }
});

// Show notification
notificationManager.addNotification({
  type: 'success',
  title: 'Message Sent',
  body: 'Your message was delivered',
});
```

---

## Step 5: Verify All Endpoints

Run this checklist to verify backend implementation:

### Authentication Endpoints

- [ ] `POST /auth/login` — Returns API key + user data
- [ ] `POST /auth/signup` — Creates new user
- [ ] `POST /auth/logout` — Invalidates session
- [ ] `GET /auth/me` — Returns current user (requires auth)
- [ ] `PATCH /auth/me/password` — Changes password
- [ ] `POST /auth/verify-email` — Verifies email token
- [ ] `POST /auth/request-verification` — Sends verification email
- [ ] `POST /auth/oauth/{provider}/callback` — OAuth flow

### Persona Endpoints

- [ ] `GET /v1/personas` — Returns all personas with filters
- [ ] `GET /v1/personas/{id}` — Returns single persona
- [ ] `GET /v1/personas/{id}/vector` — Returns persona vector
- [ ] `POST /v1/compile` — Compiles persona model
- [ ] `GET /v1/catalog` — Returns catalog metadata

### Purchase Endpoints

- [ ] `GET /v1/purchases` — Returns user's purchases
- [ ] `POST /v1/purchases` — Creates purchase
- [ ] `POST /v1/purchases/{id}/refund` — Refunds purchase

### WebSocket

- [ ] `WS /ws/chat/{persona_id}?tier=text|voice|full` — Chat streaming
- [ ] `WS /ws/notifications` — Real-time notifications

### Analytics Endpoints

- [ ] `GET /analytics/dashboard` — Dashboard overview
- [ ] `GET /analytics/personas/top` — Top personas
- [ ] `GET /analytics/personas/{id}` — Persona stats
- [ ] `GET /analytics/users/{id}` — User stats
- [ ] `GET /analytics/revenue` — Revenue report
- [ ] `GET /analytics/dau` — Daily active users
- [ ] `GET /analytics/retention` — Retention curves
- [ ] `GET /analytics/export/{format}` — Export data (csv, json, pdf)

### Cache Endpoints

- [ ] `GET /cache/health` — Cache status
- [ ] `GET /cache/stats` — Cache statistics
- [ ] `DELETE /cache/flush` — Clear all cache
- [ ] `DELETE /cache/personas/{id}` — Clear persona cache

### Health Check

- [ ] `GET /health` — Service health status

---

## Step 6: Test Error Handling

### Network Error
```javascript
// Simulate offline mode
// Browser DevTools → Network tab → Offline checkbox

try {
  await api.getCatalog();
} catch (error) {
  console.log('Error:', error.message);
  // Should show: "Network error - check your connection"
}
```

### 401 Unauthorized
```javascript
// Send request with invalid/expired key
localStorage.setItem('api_key', 'prs_invalid');

try {
  await api.getMe();
} catch (error) {
  console.log('Status:', error.response.status); // 401
  // Should redirect to /login
}
```

### 404 Not Found
```javascript
try {
  await api.getPersona('nonexistent-persona');
} catch (error) {
  console.log('Status:', error.response.status); // 404
  console.log('Message:', getErrorMessage(error)); // "Resource not found"
}
```

### Rate Limiting (429)
```javascript
// Send rapid requests
for (let i = 0; i < 100; i++) {
  api.getCatalog();
}

// Should receive 429 response after threshold
```

---

## Step 7: Performance Optimization

### Check Bundle Size

```bash
npm run build -- --analyze
```

Target limits:
- Main JS: <2MB (uncompressed), <600KB (gzipped)
- CSS: <10KB (uncompressed), <3KB (gzipped)

### Monitor Network Waterfall

Chrome DevTools → Network tab:
- HTML: <50ms
- JS chunks: <100ms each
- API calls: <500ms
- WebSocket upgrade: <200ms

### Lighthouse Audit

```bash
npm install -D @lhci/cli@^0.9
npx lhci autorun
```

Target scores:
- Performance: >85
- Accessibility: >90
- Best Practices: >90
- SEO: >80
- PWA: >80

---

## Step 8: Security Verification

### CORS Headers

```javascript
// Check response headers
fetch('http://localhost:8000/health')
  .then(r => {
    console.log('Access-Control-Allow-Origin:', r.headers.get('access-control-allow-origin'));
    console.log('Access-Control-Allow-Methods:', r.headers.get('access-control-allow-methods'));
  });
```

Expected headers:
```
Access-Control-Allow-Origin: http://localhost:5173
Access-Control-Allow-Methods: GET, POST, PUT, DELETE, OPTIONS
Access-Control-Allow-Credentials: true
```

### Security Headers

```javascript
// Check HTTPS + security headers
fetch('https://api.persona-hub.com/health')
  .then(r => {
    console.log('Strict-Transport-Security:', r.headers.get('strict-transport-security'));
    console.log('X-Content-Type-Options:', r.headers.get('x-content-type-options'));
    console.log('X-Frame-Options:', r.headers.get('x-frame-options'));
  });
```

### API Key Security

```javascript
// Verify API key is sent correctly
// Chrome DevTools → Network → Request Headers
// Should show: Authorization: Bearer prs_...
```

---

## Step 9: Deployment

### Staging Environment

```bash
# Build for staging
VITE_API_URL=https://staging-api.persona-hub.com/api npm run build

# Deploy to staging
vercel deploy --env staging
```

### Production Environment

```bash
# Build for production
VITE_API_URL=https://api.persona-hub.com/api npm run build

# Deploy to production
vercel deploy --prod
```

---

## Troubleshooting

### "API Connection Failed"

**Check:**
1. Backend is running (`http://localhost:8000`)
2. VITE_API_URL is correct
3. No firewall blocking connections
4. CORS is enabled on backend

**Debug:**
```javascript
import { health } from './services/health.js';
const result = await health.checkAPI();
console.log(result);
```

### "WebSocket Connection Failed"

**Check:**
1. Backend supports WebSocket upgrade
2. No firewall blocking WebSocket
3. VITE_WS_URL is correct (ws:// or wss://)
4. Backend has `/ws/` routes

**Debug:**
```javascript
const ws = new WebSocket('ws://localhost:8000/ws/health');
ws.onopen = () => console.log('Connected');
ws.onerror = (e) => console.error('Error:', e);
```

### "Unauthorized (401)"

**Check:**
1. API key is valid
2. API key hasn't expired
3. API key is sent in Authorization header
4. Backend validates token correctly

**Debug:**
```javascript
import { api } from './services/api.js';
const user = await api.getMe().catch(e => {
  console.log('Status:', e.response.status);
  console.log('Message:', e.response.data);
});
```

### "Timeout Errors"

**Check:**
1. Backend is responsive
2. Network latency is acceptable
3. Database queries are optimized
4. Cache is working (Redis)

**Debug:**
```javascript
const start = performance.now();
await api.getCatalog();
const duration = performance.now() - start;
console.log(`Request took ${duration}ms`);
```

### "CORS Issues"

**Check:**
1. Frontend URL is in CORS whitelist
2. Credentials are included in requests
3. Preflight requests are handled
4. Headers are correct

**Debug:**
```javascript
// Browser Network tab
// Look for OPTIONS request before actual request
// Check for Access-Control headers in response
```

---

## Monitoring in Production

### Health Check Endpoint

```bash
# Check every 30 seconds
curl -s http://api.persona-hub.com/health | jq '.status'
```

### WebSocket Monitoring

```javascript
// Monitor connection status
import { notificationManager } from './services/notifications.js';

notificationManager.on('connected', () => {
  console.log('Notifications connected');
  // Send analytics event
});

notificationManager.on('disconnected', () => {
  console.log('Notifications disconnected');
  // Send alert
});
```

### Error Tracking

```javascript
// Sentry initialization (in main.jsx)
import * as Sentry from "@sentry/react";

Sentry.init({
  dsn: import.meta.env.VITE_SENTRY_DSN,
  environment: import.meta.env.MODE,
  tracesSampleRate: 0.1,
});
```

---

## API Changes Log

Track API changes that require frontend updates:

| Date | Endpoint | Change | Impact |
|------|----------|--------|--------|
| | | | |

---

## Support & Documentation

- **Backend API Docs:** `http://localhost:8000/docs` (Swagger UI)
- **WebSocket Protocol:** See `frontend/src/hooks/useWebSocket.js`
- **Error Handling:** See `frontend/src/services/api.js`
- **Health Checks:** See `frontend/src/services/health.js`

---

**Last Updated:** June 2026  
**Status:** Ready for Production Integration ✅
