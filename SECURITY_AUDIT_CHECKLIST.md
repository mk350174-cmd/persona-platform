# Security Audit Checklist — Pre-Launch (H102+)

**Purpose:** Comprehensive security audit for frontend, backend, and infrastructure before production launch.

**Audit Date:** _______________  
**Auditor:** _______________  
**Status:** 🟢 PASS / 🟡 CONDITIONAL / 🔴 FAIL

---

## Frontend Security (20 items)

### HTTPS/TLS & Headers
- [ ] HTTPS enforcement (redirect HTTP → HTTPS)
- [ ] TLS version ≥ 1.2 (no SSLv3, TLS 1.0, 1.1)
- [ ] HSTS header present (max-age ≥ 31536000)
- [ ] CSP header configured (no `unsafe-inline`, `unsafe-eval`)
- [ ] X-Frame-Options: DENY (clickjacking prevention)
- [ ] X-Content-Type-Options: nosniff (MIME type sniffing)
- [ ] X-XSS-Protection: 1; mode=block
- [ ] Referrer-Policy: strict-origin-when-cross-origin

### Application Security
- [ ] No hardcoded API keys in JavaScript
- [ ] API keys not stored in localStorage (use secure session storage)
- [ ] Password inputs not visible in DevTools (masked)
- [ ] Form inputs sanitized before submission
- [ ] No console.log() of sensitive data
- [ ] CSRF tokens on form submissions (if applicable)
- [ ] WebSocket uses WSS (secure)

### Dependencies & Build
- [ ] npm audit clean (no high/critical vulnerabilities)
- [ ] Production build without source maps
- [ ] Bundle size within limits (<2MB uncompressed, <600KB gzipped)
- [ ] Build reproducible (same hash for same code)
- [ ] No dev dependencies in production build

### PWA & Service Worker
- [ ] Service worker uses cache-first strategy (API responses)
- [ ] Service worker doesn't cache sensitive data
- [ ] PWA manifest has CSP-compliant icons
- [ ] Offline mode gracefully handles authentication

---

## Backend Security (25 items)

### API Authentication & Authorization
- [ ] API key hashing implemented (SHA-256 prefix storage)
- [ ] API key rotation with grace period (7 days)
- [ ] Token expiration enforced (JWT, session tokens)
- [ ] Password hashing (Argon2, not MD5/SHA1)
- [ ] Rate limiting per API key (not just IP)
- [ ] Rate limiting on authentication endpoints (5 attempts / 15 min)
- [ ] CORS whitelist configured (not `*`)
- [ ] CORS credentials only for trusted origins

### Input Validation & SQL Injection
- [ ] All endpoints validate input (Pydantic models)
- [ ] File uploads validated (type, size, content)
- [ ] SQL queries use parameterized statements (no string concatenation)
- [ ] JSON parsing validates schema
- [ ] Large payloads rejected (max size limits)

### Error Handling & Logging
- [ ] No stack traces in error responses
- [ ] No database credentials in logs
- [ ] No API keys in logs
- [ ] Sensitive data redacted from logs
- [ ] Error messages generic (don't leak info)
- [ ] Audit logging for sensitive operations
- [ ] Log retention policy enforced

### Database & Secrets
- [ ] Database passwords not in code (use env vars)
- [ ] Redis password configured (not default)
- [ ] Secrets manager configured (AWS Secrets, HashiCorp Vault)
- [ ] Secret rotation procedures documented
- [ ] Database backups encrypted
- [ ] Database access restricted by IP/security group

### WebSocket & Real-Time
- [ ] WebSocket authentication enforced
- [ ] WebSocket messages validated
- [ ] WebSocket rate limiting implemented
- [ ] No sensitive data in WebSocket messages (or encrypted)

---

## Infrastructure Security (20 items)

### Network & Firewall
- [ ] Firewall rules allow only required ports (80, 443, 5432 internal only)
- [ ] SSH access restricted (bastion host or specific IPs)
- [ ] No public database access (port 5432 internal only)
- [ ] No public Redis access (port 6379 internal only)
- [ ] Network segmentation (frontend, backend, database subnets)

### Access Control
- [ ] IAM roles follow least privilege principle
- [ ] Database users have minimal required permissions
- [ ] SSH keys rotated (no shared keys)
- [ ] Root/admin access disabled (sudo only)
- [ ] MFA enabled for admin access

### Encryption & Backups
- [ ] SSL certificates valid (not self-signed, expiry >30 days)
- [ ] Database encryption at rest (Postgres pgcrypto or AWS KMS)
- [ ] Backups encrypted at rest (S3 SSE-S3 or KMS)
- [ ] Backup access restricted (separate credentials)
- [ ] Backup retention policy enforced (30 days)

### Monitoring & Logging
- [ ] Centralized logging (ELK, Datadog, CloudWatch)
- [ ] Security event logging (failed logins, privilege escalation)
- [ ] Intrusion detection configured
- [ ] DDoS protection enabled (if cloud provider supports)
- [ ] VPC Flow Logs enabled

### Container & Deployment
- [ ] Docker images scanned for vulnerabilities (Trivy)
- [ ] Base images updated regularly
- [ ] No hardcoded secrets in Dockerfiles
- [ ] Secrets passed via environment variables
- [ ] Container registries private (not public)

---

## Compliance & Legal (15 items)

### GDPR Compliance (EU users)
- [ ] Privacy policy present and accessible
- [ ] Data processing agreement (DPA) with processors
- [ ] User consent collection (cookies, analytics)
- [ ] Data retention policy enforced (soft deletes)
- [ ] User data export capability (GDPR right to data portability)
- [ ] Right to deletion implemented (GDPR right to be forgotten)
- [ ] Data breach notification procedures documented

### Other Compliance (as applicable)
- [ ] KVKK compliance (Turkey - if applicable)
- [ ] CCPA compliance (California - if applicable)
- [ ] Terms of Service present
- [ ] Cookie consent banner (if tracking enabled)
- [ ] Accessibility audit (WCAG 2.1 Level AA minimum)
- [ ] Age verification (if collecting user age)
- [ ] Parental consent (if targeting minors)

---

## Vulnerability Scanning Results

### Automated Scans
**Run Date:** _______________

- [ ] OWASP ZAP scan completed (results: _____ issues)
- [ ] npm audit passed (0 high/critical vulnerabilities)
- [ ] pip audit passed (0 high/critical vulnerabilities)
- [ ] Trivy Docker scan passed (0 critical findings)
- [ ] gitleaks passed (no secrets committed)
- [ ] Bandit Python static analysis passed

### Manual Testing
- [ ] Attempted SQL injection (failed - protected)
- [ ] Attempted XSS injection (failed - sanitized)
- [ ] Attempted authentication bypass (failed)
- [ ] Tested rate limiting (working as expected)
- [ ] Tested error handling (no leaks)

---

## Third-Party Services Security

- [ ] Stripe API keys secured (production vs test)
- [ ] Resend (email) API keys secured
- [ ] Sentry DSN (error tracking) configured correctly
- [ ] Third-party integrations documented
- [ ] Third-party service agreements reviewed

---

## Security Issues Found

| # | Severity | Issue | Remediation | Status |
|---|----------|-------|------------|--------|
| 1 | | | | |
| 2 | | | | |
| 3 | | | | |

---

## Final Assessment

### Overall Security Posture
🟢 **SECURE** - All critical items passing, no blocking issues  
🟡 **CONDITIONAL** - Minor issues identified, documented for tracking  
🔴 **INSECURE** - Critical issues found, must fix before launch

### Blocking Issues
- [ ] None (proceed with launch)
- [ ] Found (describe below)

_______________________________________________

### Auditor Sign-Off

I certify that this security audit was completed thoroughly and accurately.

**Auditor Name:** _______________  
**Auditor Title:** _______________  
**Date:** _______________  
**Signature:** _______________

### Security Lead Approval

Based on this audit, I approve / do not approve this application for production launch.

**Security Lead Name:** _______________  
**Date:** _______________  
**Signature:** _______________

---

**Next Steps:**
1. Address any findings from this audit
2. Re-run automated scans after fixes
3. Schedule follow-up audit in 3 months
4. Track ongoing security issues in GitHub Issues

---

**Document Version:** 1.0  
**Last Updated:** 2026-06-11
