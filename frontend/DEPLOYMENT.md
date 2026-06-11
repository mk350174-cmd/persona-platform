# Persona Hub Frontend — Deployment Guide

## Overview

The Persona Hub frontend is a React 18 SPA built with Vite, featuring real-time WebSocket chat, advanced visualizations, and PWA support. This guide covers development, testing, and production deployment.

---

## Prerequisites

- **Node.js 18+** (includes npm 9+)
- **Git** for version control
- **Vercel CLI** or **Netlify CLI** for serverless deployment (optional)
- **Docker** (optional, for containerized deployment)

---

## Development

### Setup

```bash
cd frontend
npm install
```

### Environment Configuration

Create `.env.development` for local development:

```env
VITE_API_URL=http://localhost:8000/api
VITE_WS_URL=ws://localhost:8000
VITE_ENABLE_ANALYTICS=true
VITE_ENABLE_VOICE=true
VITE_ENABLE_PWA=true
```

### Start Dev Server

```bash
npm run dev
```

The app will be available at `http://localhost:5173` with:
- **Hot Module Replacement (HMR)** for instant updates
- **Automatic proxy** to backend at `/api` and `/ws`
- **Source maps** for debugging

### Key Development Features

- **Fast Refresh:** Code changes reflect instantly
- **TypeScript Support:** ES modules with full type checking
- **Material Design 3:** Tailwind CSS with 73 custom colors
- **Dark Mode:** Toggle via Theme context
- **i18n:** English/Turkish translation keys

---

## Testing

### Unit Tests

```bash
npm run test
```

Coverage targets: 80%+ for critical components

### Performance Testing

#### Lighthouse Audit (Local)

```bash
npm run lighthouse
```

Or use Chrome DevTools → Lighthouse tab

**Target Scores:**
- Performance: >85
- Accessibility: >90
- Best Practices: >90
- SEO: >80
- PWA: >80

#### Bundle Analysis

```bash
npm run build -- --analyze
```

Examine output in `dist/` directory:
- Main JS: ~1.6 MB min (~560 KB gzipped)
- CSS: ~8.5 KB (~2.5 KB gzipped)
- Code-split chunks: Three.js, Recharts, React-Markdown, jsPDF

#### Load Testing

Simulate 100+ concurrent users:

```bash
# Install artillery globally
npm install -g artillery

# Run load test
artillery run load-test.yml
```

**load-test.yml:**
```yaml
config:
  target: "http://localhost:5173"
  phases:
    - duration: 60
      arrivalRate: 10
      name: "Warm up"
    - duration: 120
      arrivalRate: 50
      name: "Ramp up"
    - duration: 60
      arrivalRate: 100
      name: "Spike"

scenarios:
  - name: "Catalog browsing"
    flow:
      - get:
          url: "/"
      - get:
          url: "/catalog"
      - think: 5
      - get:
          url: "/personas/socrates"
```

---

## Building

### Production Build

```bash
npm run build
```

Output:
- **dist/** — Static files ready for deployment
- **dist/index.html** — SPA entry point
- **dist/assets/** — Bundled JS/CSS/images

**Build Optimization:**
- Minification & tree-shaking
- Code splitting (separate chunks for large libraries)
- Source maps disabled in production
- Asset hashing for cache busting

### Build Size

Typical output:
```
dist/index.html                    0.78 kB
dist/assets/index-{hash}.css       8.56 kB (gzip: 2.50 kB)
dist/assets/three-{hash}.js        512 kB (gzip: 128 kB)
dist/assets/recharts-{hash}.js     385 kB (gzip: 111 kB)
dist/assets/react-markdown-{hash}  123 kB (gzip: 37 kB)
dist/assets/index-{hash}.js        1.6 MB (gzip: 560 kB)
```

**Total:** ~2.5 MB uncompressed, ~750 KB gzipped

---

## Deployment Options

### Option 1: Vercel (Recommended)

**Advantages:** Optimal for React SPA, global CDN, automatic deployments

#### Setup

```bash
npm i -g vercel
vercel login
vercel link
```

#### Deploy

```bash
# Preview deployment
vercel

# Production deployment
vercel --prod
```

**Configuration** (`vercel.json`):
```json
{
  "buildCommand": "npm run build",
  "outputDirectory": "dist",
  "rewrites": [
    {
      "source": "/:path((?!_next|assets|public).*)",
      "destination": "/index.html"
    }
  ],
  "env": {
    "VITE_API_URL": "@api_url"
  }
}
```

#### Environment Variables

Set in Vercel dashboard:
```
VITE_API_URL = https://api.persona-hub.com/api
VITE_WS_URL = wss://api.persona-hub.com
VITE_ENABLE_PWA = true
```

---

### Option 2: Netlify

**Advantages:** Easy setup, good for JAMstack, built-in forms

#### Setup

```bash
npm i -g netlify-cli
netlify login
netlify link
```

#### Deploy

```bash
# Preview
netlify deploy

# Production
netlify deploy --prod
```

**Configuration** (`netlify.toml`):
```toml
[build]
command = "npm run build"
publish = "dist"

[dev]
command = "npm run dev"
port = 3000

[[redirects]]
from = "/*"
to = "/index.html"
status = 200

[[headers]]
for = "/assets/*"
[headers.values]
Cache-Control = "public, max-age=31536000, immutable"

[context.production.environment]
VITE_API_URL = "https://api.persona-hub.com/api"
VITE_WS_URL = "wss://api.persona-hub.com"
```

---

### Option 3: Self-Hosted (FastAPI)

Serve frontend from FastAPI server:

```python
# api/main.py
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

app = FastAPI()

# Register API routes first
app.include_router(...)

# Serve frontend build
app.mount("/", StaticFiles(directory="frontend/dist", html=True), name="static")

# SPA fallback (serve index.html for all non-API routes)
@app.get("/{full_path:path}")
async def serve_spa(full_path: str):
    return FileResponse("frontend/dist/index.html")
```

**Docker Setup:**

```dockerfile
# Build frontend
FROM node:18-alpine AS frontend-builder
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ .
RUN npm run build

# Build backend
FROM python:3.11-slim
WORKDIR /app

# Copy frontend dist
COPY --from=frontend-builder /app/frontend/dist ./api/static

# Copy backend
COPY api/ ./api
COPY requirements.txt .

RUN pip install -r requirements.txt

EXPOSE 8000
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

---

### Option 4: Docker Compose

```yaml
version: '3.8'
services:
  frontend:
    image: node:18-alpine
    working_dir: /app/frontend
    volumes:
      - .:/app
    ports:
      - "5173:5173"
    command: npm install && npm run dev

  backend:
    image: python:3.11-slim
    working_dir: /app
    volumes:
      - .:/app
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://user:pass@postgres:5432/persona_hub
    command: uvicorn api.main:app --host 0.0.0.0 --reload

  postgres:
    image: postgres:15-alpine
    environment:
      - POSTGRES_USER=user
      - POSTGRES_PASSWORD=pass
      - POSTGRES_DB=persona_hub
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data

volumes:
  postgres_data:
```

---

## Performance Optimization

### 1. Code Splitting

Automatic for large libraries:
- `three.js` (512 KB)
- `recharts` (385 KB)
- `react-markdown` (123 KB)
- `jspdf` (~150 KB)

### 2. Asset Optimization

```bash
# Image optimization (if used)
npm install -D vite-plugin-imagemin
```

### 3. Caching Strategy

**Service Worker** (`public/service-worker.js`):
- Network-first for API calls
- Cache-first for static assets
- Offline fallback to index.html

### 4. Compression

Enable Gzip in server config:
```nginx
gzip on;
gzip_types text/plain text/css text/javascript application/json;
gzip_min_length 1000;
```

### 5. CDN Configuration

```nginx
# Vercel/Netlify handles automatically
# For self-hosted, use CloudFlare or AWS CloudFront:
Add-Type -AssemblyName System.Net.Http
$response = Invoke-WebRequest -Uri "https://api.cloudflare.com/client/v4/zones/{zone_id}/purge_cache" -Method POST
```

---

## Security

### Headers

Already configured in deployment:
- `X-Content-Type-Options: nosniff`
- `X-Frame-Options: DENY`
- `X-XSS-Protection: 1; mode=block`
- `Referrer-Policy: strict-origin-when-cross-origin`

### HTTPS

- **Vercel/Netlify:** Automatic SSL
- **Self-hosted:** Use Let's Encrypt with certbot
  ```bash
  certbot certonly --standalone -d persona-hub.com
  ```

### CSP (Content Security Policy)

Add to `index.html`:
```html
<meta http-equiv="Content-Security-Policy" 
      content="default-src 'self'; 
               script-src 'self' 'wasm-unsafe-eval';
               style-src 'self' 'unsafe-inline';
               img-src 'self' data: https:;
               font-src 'self' fonts.googleapis.com;
               connect-src 'self' api.persona-hub.com wss://api.persona-hub.com">
```

---

## Monitoring & Logging

### Error Tracking (Sentry)

```javascript
// src/main.jsx
import * as Sentry from "@sentry/react";

Sentry.init({
  dsn: import.meta.env.VITE_SENTRY_DSN,
  environment: import.meta.env.MODE,
  tracesSampleRate: 0.1,
});
```

### Analytics (Google Analytics)

```javascript
// src/main.jsx
import ReactGA from 'react-ga4';

ReactGA.initialize(import.meta.env.VITE_GA_TRACKING_ID);
```

### Custom Logging

```javascript
// src/services/logger.js
export const logEvent = (event, data) => {
  console.log(`[${new Date().toISOString()}]`, event, data);
  // Send to backend analytics endpoint
};
```

---

## CI/CD Pipeline

GitHub Actions workflow (`.github/workflows/frontend-ci.yml`):

1. **Test Phase** (on every push/PR)
   - Install dependencies
   - Run linter (ESLint)
   - Build project
   - Upload artifacts

2. **Lighthouse Phase** (on every push/PR)
   - Run Lighthouse audit
   - Check performance thresholds
   - Generate report

3. **Preview Deployment** (on PRs)
   - Deploy to Netlify preview
   - Add comment with preview URL
   - Enable testing before merge

4. **Production Deployment** (on main branch)
   - Build production bundle
   - Deploy to Vercel/production server
   - Notify team of deployment

---

## Rollback Procedure

### Vercel

```bash
# View deployments
vercel list

# Rollback to previous
vercel rollback
```

### Netlify

```bash
# Rollback in dashboard
# Settings → Deployments → Deploys → Redeploy
netlify deploy --prod --alias=rollback
```

### Self-Hosted

```bash
# Keep previous build
cp -r dist dist.backup
npm run build
# If needed: mv dist.backup dist && restart service
```

---

## Troubleshooting

### API Connection Issues

```javascript
// Debug API calls
// Browser Console → Network tab
// Check VITE_API_URL matches backend domain
```

### WebSocket Connection Failed

```javascript
// Check ws:// vs wss:// protocol matches HTTPS
// Verify backend accepts WebSocket upgrades
// Check CORS headers for ws protocol
```

### Build Size Warnings

```bash
# Analyze bundle
npm run build -- --analyze

# Reduce Three.js size:
import { Scene, PerspectiveCamera } from 'three/src/Three'
```

### Performance Degradation

```bash
# Profile with Chrome DevTools
# Performance → Record → Analyze flame chart
# Lighthouse audit → identify bottlenecks
```

---

## Checklist Before Production

- [ ] Environment variables set (.env.production)
- [ ] Lighthouse audit passed (>85 all metrics)
- [ ] WebSocket connection tested
- [ ] API endpoints verified
- [ ] PWA installable on mobile
- [ ] Offline functionality tested
- [ ] HTTPS/SSL working
- [ ] Error tracking (Sentry) configured
- [ ] Analytics configured
- [ ] Rollback procedure documented
- [ ] Team notified of deployment
- [ ] Monitoring dashboards set up
- [ ] Backup of production built

---

## Next Steps

1. **Scale Backend:** Handle increased user load
2. **Real-time Notifications:** WebSocket for new messages
3. **Analytics Dashboard:** Track user engagement
4. **Mobile App:** React Native version
5. **Admin Panel:** User/content management

---

**Last Updated:** June 2026  
**Frontend Version:** 1.0.0  
**React:** 18+  
**Node:** 18+  
**Status:** Production Ready ✅
