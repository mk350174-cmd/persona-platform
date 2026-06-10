# CI/CD Pipeline Setup (H87-H89)

## Overview

Comprehensive CI/CD pipeline for automated testing, security scanning, deployment, and notifications.

**Goals:**
- ✅ Multi-Python matrix testing (3.9, 3.10, 3.11, 3.12)
- ✅ Automated security scanning (gitleaks, bandit, safety)
- ✅ Code quality gates (linting, type checking, formatting)
- ✅ Auto-deploy on main branch merge
- ✅ Automated dependency updates (Dependabot)
- ✅ Slack/email notifications
- ✅ Local pre-commit hooks

## GitHub Actions Workflows

### 1. CI Matrix Testing (`ci-matrix.yml`)

**Triggers:**
- Push to main, develop, or feature branches
- Pull requests to main/develop

**Jobs:**
1. **test-matrix** — Tests across Python 3.9-3.12
   - Install dependencies
   - Lint with flake8
   - Type check with mypy
   - Run unit tests (security + payments)
   - Run integration tests (webhooks + payments)
   - Coverage report (minimum 75%)
   - Codecov upload

2. **security-scan** — Security analysis
   - gitleaks: Detect secrets in code
   - bandit: Python SAST analysis
   - safety: Check for vulnerable dependencies

3. **quality-gates** — Code quality checks
   - pylint: Code complexity analysis
   - black: Code formatting check
   - isort: Import sorting validation

4. **build-summary** — Overall status

**Example Output:**
```
✅ Python 3.9: 47 tests passed, coverage 82%
✅ Python 3.10: 47 tests passed, coverage 82%
✅ Python 3.11: 47 tests passed, coverage 82%
✅ Python 3.12: 47 tests passed, coverage 82%
✅ Security Scan: No secrets detected, 0 SAST issues
✅ Quality Gates: All checks passed
```

### 2. Auto-Deploy (`deploy.yml`)

**Triggers:**
- Push to main branch
- Tag creation (releases)

**Jobs:**
1. **build-and-deploy**
   - Build Docker image
   - Push to container registry
   - Create GitHub deployment
   - Run database migrations
   - Slack notification

2. **release** (on version tags)
   - Generate changelog
   - Create GitHub Release
   - Auto-upload artifacts

3. **health-check**
   - Wait for deployment
   - Health endpoint verification
   - Smoke tests
   - Post results to Slack

**Deployment Strategy:**
```
Push to main
    ↓
Trigger CI pipeline
    ↓
If all tests pass:
    - Build Docker image
    - Push to registry
    - Create deployment
    ↓
Post-deploy health checks
    ↓
Notify team (Slack)
```

### 3. Notifications (`notifications.yml`)

**Triggers:**
- Workflow completion (CI or Deploy)

**Notifications:**
1. **Slack** — Build status, branch, author, commit link
2. **Email** — Only on failures
3. **GitHub** — Status check, auto-assignment on failure

**Slack Message Example:**
```
✅ CI - Multi-Python Matrix Tests succeeded

Branch: `main`
Author: @developer
Commit: "Feat: Add payment features"

View workflow: https://github.com/.../actions/runs/...
```

## Dependabot Configuration

**File:** `.github/dependabot.yml`

**Features:**
- Weekly dependency updates
- Python packages, GitHub Actions, Docker
- Grouped updates (dev, production, major)
- Auto-rebase and merge on passing tests
- Slack notifications

**Update Schedule:**
```
Monday 03:00 UTC: pip dependencies
Monday 04:00 UTC: GitHub Actions
Monday 05:00 UTC: Docker images
```

**Example:** Dependabot PR
```
Title: chore(deps): update dependencies

- Update pytest from 7.4.0 to 7.4.2
- Update sqlalchemy from 2.0.20 to 2.0.21
- Update stripe from 5.4.0 to 5.5.0

✅ All checks passed
```

## Pre-Commit Hooks

**Install:**
```bash
pip install pre-commit
pre-commit install
pre-commit install --hook-type commit-msg
```

**Hooks Enabled:**
1. **black** — Code formatting
2. **isort** — Import sorting
3. **flake8** — Linting
4. **mypy** — Type checking
5. **bandit** — Security scanning
6. **yamllint** — YAML validation
7. **commitizen** — Commit message format
8. **detect-private-key** — Secret detection
9. **trailing-whitespace** — Whitespace cleanup

**Usage:**
```bash
# Run on all files
pre-commit run --all-files

# Run on staged files (automatic)
git commit -m "message"  # Hooks run automatically

# Update hooks
pre-commit autoupdate

# Skip hooks (not recommended)
git commit --no-verify
```

**Example Hook Run:**
```
black .................................................. passed
isort .................................................. passed
flake8 ................................................ passed
mypy .................................................  passed
bandit ............................................... passed
yamllint ............................................. passed
commitizen ........................................... passed
```

## GitHub Secrets Required

**For Deployment:**
```
DATABASE_URL_PROD          # PostgreSQL connection string
SLACK_WEBHOOK             # Slack webhook URL for notifications
```

**Optional:**
```
MAIL_SERVER               # SMTP server
MAIL_PORT                 # SMTP port (e.g., 587)
MAIL_USERNAME             # SMTP username
MAIL_PASSWORD             # SMTP password
NOTIFICATION_EMAIL        # Email to notify on failure
```

**Set Secrets:**
```bash
# GitHub CLI
gh secret set SLACK_WEBHOOK --body "https://hooks.slack.com/..."
gh secret set DATABASE_URL_PROD --body "postgresql://..."

# Or via GitHub UI: Settings → Secrets → New repository secret
```

## CI/CD Metrics & Status

### Build Dashboard
- Workflow runs (success/failure rate)
- Test coverage trends
- Deployment frequency
- Lead time for changes
- Mean time to recovery

### Access Points:
```
GitHub: Settings → Actions → Workflows
Codecov: https://codecov.io/gh/mk350174-cmd/persona-platform
Slack: #deployments channel
```

## Troubleshooting

### Build Failures

**1. Python Version Incompatibility**
```bash
# Test locally
python3.9 -m pytest tests/
python3.12 -m pytest tests/
```

**2. Missing Dependencies**
```bash
# Update requirements
pip install -r requirements.txt -r requirements-api.txt
```

**3. Linting/Formatting Issues**
```bash
# Auto-fix
black api/ tests/
isort api/ tests/
```

**4. Secret Detection (gitleaks)**
```bash
# Remove secret from history
git filter-branch --tree-filter 'rm -f secrets.json'
git push --force-with-lease
```

### Deployment Issues

**1. Database Migration Fails**
```bash
# Rollback locally, test, then retry
alembic downgrade -1
# Fix migration
alembic upgrade head
```

**2. Health Check Timeout**
```bash
# Check deployment logs
kubectl logs -l app=persona-hub

# Manual health check
curl http://localhost:8000/health
```

**3. Slack Webhook Invalid**
```bash
# Update webhook URL
gh secret set SLACK_WEBHOOK --body "https://hooks.slack.com/..."
```

## Performance Optimization

### Caching
```yaml
cache: "pip"  # Cache Python packages between runs
```

### Parallel Jobs
```yaml
strategy:
  matrix:
    python-version: ["3.9", "3.10", "3.11", "3.12"]
```
Tests run in parallel across Python versions (~5 min total vs 20 min serial).

### Concurrency Control
```yaml
concurrency:
  group: ci-${{ github.ref }}
  cancel-in-progress: true
```
Automatically cancels previous runs on new push.

## Best Practices

### Commit Messages
Format: `type(scope): description`

**Examples:**
```
feat(payments): add wallet credit system
fix(webhook): handle duplicate events
chore(deps): update dependencies
docs: add load testing guide
test: improve payment coverage
```

### Branch Strategy
```
main              → Production-ready (protected)
  ↑ PR with CI
develop           → Integration branch
  ↑ PR with CI
feature/*         → Feature branches (auto-deploy on PR approval)
claude/*          → Development branches
```

### PR Requirements
- ✅ All CI checks pass
- ✅ Code review approval
- ✅ Coverage >= 75%
- ✅ No security issues
- ✅ Commit messages follow convention

## Monitoring & Alerts

### Key Metrics to Monitor
1. **Build Success Rate** — Should be > 95%
2. **Test Coverage** — Maintain >= 75%
3. **Deployment Frequency** — Daily or more
4. **Mean Time to Recovery** — < 1 hour
5. **Security Issues** — Zero critical

### Alert Thresholds
```
❌ Build fails      → Slack + Email to author
❌ Coverage drops   → PR comment warning
❌ Security issue   → Slack alert + block merge
⚠️  Slow tests      → Log warning, don't block
```

## Future Improvements

### H90+: Advanced Features
- [ ] Canary deployments (10% traffic)
- [ ] A/B testing framework
- [ ] Rollback automation
- [ ] Performance regression detection
- [ ] Database backup automation
- [ ] Cost tracking and optimization

## Resources

- [GitHub Actions Docs](https://docs.github.com/en/actions)
- [Dependabot Docs](https://docs.github.com/en/code-security/dependabot)
- [Pre-commit Framework](https://pre-commit.com/)
- [Semantic Commit Convention](https://www.conventionalcommits.org/)
- [DORA Metrics Guide](https://cloud.google.com/blog/products/devops-sre/measuring-devops-success-the-four-keys)
