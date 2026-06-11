# Future PR Prevention Rules

## Summary

PR #5 identified 4 critical test infrastructure issues that would recur in future PRs without explicit prevention:

| Issue | Root Cause | Prevention | Enforcement |
|---|---|---|---|
| **Test Fixture Fragmentation** | Files had individual fixtures instead of using centralized `conftest.py` | Move all fixtures to `conftest.py` | Pre-commit hook: `no-test-fixtures-outside-conftest` |
| **Module State Pollution** | Rate limiter state not cleaned between tests | Add state cleanup to `conftest.py` autouse fixture | Pre-commit hook: automatic cleanup |
| **API Schema Drift** | Tests checking for wrong field names (outdated schemas) | Write API contract tests validating response schemas | Manual: `tests/test_api_contracts.py` |
| **Placeholder Code in Production** | Hardcoded admin email check in refund endpoint | Block TODO/FIXME/HACK in `api/` files | Pre-commit hook: `no-placeholder-code-in-api` |

---

## Rule 1: Centralized Test Fixtures

**Goal:** All pytest fixtures in `tests/conftest.py` — no file-level definitions.

**Why:** Fixture fragmentation caused partial fixes when infrastructure changed.

### Implementation

**Pre-commit hook:** `scripts/check_fixtures.py`

Blocks commits that add `@pytest.fixture` to test files outside `conftest.py`.

### Usage

✅ **Correct:**
```python
# tests/conftest.py
@pytest.fixture
def authenticated_user(test_db):
    user, api_key = create_user(test_db, "test@example.com")
    return {"user": user, "api_key": api_key}

# tests/test_api.py
def test_endpoint(authenticated_user):
    response = client.get("/endpoint", headers={"X-API-Key": authenticated_user["api_key"]})
```

❌ **Incorrect (blocked by pre-commit):**
```python
# tests/test_api.py
@pytest.fixture  # ← BLOCKED: Move to conftest.py
def authenticated_user(test_db):
    ...
```

### When Adding New Test Files

1. Add fixtures to `tests/conftest.py`
2. Import/use in your new test file
3. Never define fixtures in test files

---

## Rule 2: Module State Isolation

**Goal:** All module-level state cleared between tests via autouse fixtures.

**Why:** Rate limit quota exhaustion in CI showed that module-level state persists across tests.

### Implementation

**Autouse fixture in `tests/conftest.py`:**
```python
@pytest.fixture(autouse=True)
def _reset_module_state():
    """Clear ALL module-level state between tests."""
    from api.middleware.rate_limiter import _rate_limit_state
    from api.main import limiter

    _rate_limit_state.clear()
    try:
        if hasattr(limiter, '_storage') and hasattr(limiter._storage, 'storage'):
            limiter._storage.storage.clear()
    except (AttributeError, TypeError):
        pass  # Handle version differences

    yield

    # Cleanup after test
    _rate_limit_state.clear()
    try:
        if hasattr(limiter, '_storage') and hasattr(limiter._storage, 'storage'):
            limiter._storage.storage.clear()
    except (AttributeError, TypeError):
        pass
```

### When Adding New Module-Level State

If you **must** use module-level state (e.g., cache, config singleton):

1. Add cleanup to `_reset_module_state`:
   ```python
   from my_module import _my_cache
   _my_cache.clear()
   ```

2. Document why dependency injection wasn't possible
3. Test with parallel execution: `pytest tests/ -n auto`

### Better: Use Dependency Injection

```python
# Instead of module-level state:
# ❌ _cache = {}

# Use class-based state:
# ✅
class Cache:
    def __init__(self):
        self.data = {}

cache_manager = Cache()

@app.get("/...")
def endpoint(cache: Cache = Depends(lambda: cache_manager)):
    return cache.get("key")
```

---

## Rule 3: API Schema Validation

**Goal:** Response schemas validated in tests prevent schema drift.

**Why:** Endpoint implementations changed but tests still checked for old field names.

### Implementation

**File:** `tests/test_api_contracts.py`

Validates that all endpoint responses have correct fields with correct types.

### Usage

For each endpoint, add a test that validates:
1. Required fields present
2. Field types correct
3. Response structure matches specification

```python
def test_revenue_analytics_schema(self, client, authenticated_user):
    """Validate /admin/analytics/revenue response schema."""
    response = client.get(
        "/admin/analytics/revenue",
        headers={"X-API-Key": authenticated_user["api_key"]},
    )
    assert response.status_code == 200
    data = response.json()

    # Document what fields MUST exist
    assert "period" in data
    assert "total_revenue_usd" in data
    assert isinstance(data["total_revenue_usd"], (int, float))
```

### When Adding New Endpoints

1. Add response schema validation to `tests/test_api_contracts.py`
2. Use template at bottom of file:
   ```python
   class TestNewEndpointTemplate:
       def test_new_endpoint_success_schema(self, client, authenticated_user):
           # Copy template, customize path/fields
   ```

3. Validate request schema (Pydantic `extra='forbid'`):
   ```python
   def test_new_endpoint_rejects_extra_fields(self, client, authenticated_user):
       response = client.post(
           "/endpoint",
           headers={"X-API-Key": authenticated_user["api_key"]},
           json={"valid_field": "value", "invalid_field": "value"},  # Extra field
       )
       assert response.status_code == 422  # Pydantic rejects
   ```

---

## Rule 4: No Placeholder Code in Production

**Goal:** Block TODO/FIXME/HACK/PLACEHOLDER in `api/` files.

**Why:** Hardcoded admin email in refund endpoint made feature unusable.

### Implementation

**Pre-commit hook:** `scripts/check_placeholder_code.py`

Blocks commits that add placeholder markers to `api/` files.

### Usage

❌ **Blocked:**
```python
# api/main.py
if user.email not in ["admin@example.com"]:  # ← Hardcoded
    raise HTTPException(status_code=403)
```

✅ **Correct:**
```python
# api/main.py
if user.role != "admin":
    raise HTTPException(status_code=403, detail="Admin access required.")
```

✅ **If unavoidable, mark @production-ready:**
```python
# api/feature_flags.py
# @production-ready: Feature flag lookup from cache; see issue #X
_feature_flags_cache = {}
```

### When Adding Features

1. Complete implementation before committing
2. If stuck mid-implementation, commit to feature branch
3. Use draft PR, mark as "DRAFT" in title
4. Never push incomplete code to PR branch

---

## Rule 5: Database Isolation (File-based SQLite)

**Goal:** Use file-based SQLite with `tmp_path` fixture for proper test isolation.

**Why:** In-memory `:memory:` databases break when `create_all` runs on one connection and tests use another.

### Implementation

**In `tests/conftest.py`:**
```python
@pytest.fixture
def test_db(tmp_path):
    """Create isolated file-based SQLite database."""
    db_file = tmp_path / "test.db"
    engine = create_engine(
        f"sqlite:///{db_file}",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    session = TestingSessionLocal()
    yield session
    session.close()
```

**Do NOT use:**
```python
# ❌ In-memory databases
engine = create_engine("sqlite:///:memory:")

# ❌ Session scope (shared across tests)
@pytest.fixture(scope="session")
def test_db():
    ...

# ✅ Function scope (fresh per test)
@pytest.fixture
def test_db(tmp_path):
    ...
```

---

## Testing the Prevention Rules

### 1. Test fixture isolation
```bash
# Should fail with helpful error
echo "@pytest.fixture\ndef test_db(): pass" > tests/test_bad.py
pre-commit run no-test-fixtures-outside-conftest --files tests/test_bad.py
# Output: ERROR: tests/test_bad.py has pytest fixtures: ['test_db']
```

### 2. Test placeholder detection
```bash
# Should fail with helpful error
echo "# TODO: Implement admin check" > api/test_bad.py
pre-commit run no-placeholder-code-in-api --files api/test_bad.py
# Output: ERROR: api/test_bad.py contains placeholder/TODO code
```

### 3. Test module state isolation
```bash
# Should pass (state is cleared between tests)
pytest tests/ -n auto -q
```

### 4. Test schema validation
```bash
# Should catch schema mismatches
pytest tests/test_api_contracts.py -v
```

### 5. Test database isolation
```bash
# Should pass (fresh db per test)
pytest tests/ -q
```

---

## Pre-commit Hook Setup

### Install hooks
```bash
pip install pre-commit
pre-commit install
```

### Run all hooks
```bash
pre-commit run --all-files
```

### Run specific hook
```bash
pre-commit run no-test-fixtures-outside-conftest --all-files
```

### Skip hook (not recommended)
```bash
git commit --no-verify
```

---

## Documentation

- **TEST_ISOLATION.md** — Detailed test isolation patterns and troubleshooting
- **test_api_contracts.py** — Contract tests template for response schemas
- **PREVENTION_RULES.md** — This document

---

## Enforcement Checklist for Future PRs

Before opening a PR:
- [ ] All fixtures in `tests/conftest.py` (no file-level definitions)
- [ ] Module state cleared in `_reset_module_state` if added
- [ ] API contract tests for new endpoints
- [ ] No TODO/FIXME/HACK/PLACEHOLDER in `api/` files
- [ ] Database fixture uses `tmp_path` and function scope
- [ ] Tests pass locally: `pytest tests/ -q`
- [ ] Tests pass with parallel: `pytest tests/ -n auto`
- [ ] Pre-commit hooks pass: `pre-commit run --all-files`

---

## CI/CD Integration

These prevention rules are automatically enforced:
- **Pre-commit:** Run locally before commit
- **CI:** `.github/workflows/ci.yml` runs tests with matrix (Python 3.10, 3.11, 3.12)
- **Bandit/Gitleaks:** Security scanning blocks secrets/vulnerabilities
- **Coverage:** Ensure test coverage maintained

---

## Example: Adding a New Endpoint

### Step 1: Design the endpoint
```python
# api/main.py
@app.get("/api/new-feature")
def new_feature(user: User = Depends(get_current_user)):
    return {"result": "success", "value": 42}
```

### Step 2: Add API contract test
```python
# tests/test_api_contracts.py
class TestNewFeature:
    def test_new_feature_schema(self, client, authenticated_user):
        """Validate /api/new-feature response schema."""
        response = client.get(
            "/api/new-feature",
            headers={"X-API-Key": authenticated_user["api_key"]},
        )
        assert response.status_code == 200
        data = response.json()
        assert "result" in data
        assert "value" in data
        assert isinstance(data["value"], int)
```

### Step 3: Add functional tests
```python
# tests/test_my_feature.py (imports fixtures from conftest.py)
def test_new_feature_computation(authenticated_user, test_db):
    # Test business logic
    pass
```

### Step 4: Commit
```bash
git add api/main.py tests/test_api_contracts.py tests/test_my_feature.py
pre-commit run --all-files  # ✅ All hooks pass
git commit -m "Add new feature endpoint with contract tests"
```

### Step 5: Open PR
- Tests pass locally: `pytest tests/ -q`
- Pre-commit passes: `pre-commit run --all-files`
- CI passes: GitHub Actions matrix test
- Ready to merge!

---

## Future Enhancements

These prevention rules can be extended with:
1. **Auto-generate contract tests from OpenAPI schema** (Rule 5 in original plan)
2. **Parallel test execution by default** (catch race conditions early)
3. **Code coverage gates** (maintain >80% coverage)
4. **API documentation sync** (OpenAPI spec stays in sync with code)
5. **Performance regression detection** (automated load testing in CI)

See `docs/PREVENTION_RULES.md` for details.

---

## Support

If prevention rules block a legitimate commit:
1. Check the error message — it's usually clear
2. Read `docs/TEST_ISOLATION.md` for patterns
3. Adjust code to follow rules (don't skip hooks with `--no-verify`)
4. If rule needs exception, add to exceptions dict in hook script with comment explaining why

**Rule of thumb:** The hooks exist to catch real bugs. Follow them.
