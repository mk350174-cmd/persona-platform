# Test Isolation Guide

## Overview

Test isolation ensures that tests don't interfere with each other and provide reliable, consistent results across local development and CI environments.

## Key Principles

### 1. Database Isolation

**Problem:** SQLite `:memory:` databases create separate connection pools per URI, breaking table creation across connections.

**Solution:** Use file-based SQLite with `tmp_path` fixture for proper test isolation.

**Pattern (tests/conftest.py):**
```python
@pytest.fixture
def test_db(tmp_path):
    """Create isolated file-based SQLite database per test."""
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

**Why:**
- `tmp_path` is function-scoped: each test gets fresh database
- File-based SQLite shares state across connections within same test
- Tables persist for the entire test function
- No cross-test pollution

### 2. Module-Level State Cleanup

**Problem:** Module-level globals (caches, singletons, rate limit state) persist across tests, causing failures in CI when multiple tests run concurrently.

**Solution:** Clear module-level state before and after each test with autouse fixtures.

**Pattern (tests/conftest.py):**
```python
@pytest.fixture(autouse=True)
def _reset_module_state():
    """Clear module-level state between tests."""
    from api.middleware.rate_limiter import _rate_limit_state
    from api.main import limiter

    # Clear before
    _rate_limit_state.clear()
    try:
        if hasattr(limiter, '_storage') and hasattr(limiter._storage, 'storage'):
            limiter._storage.storage.clear()
    except (AttributeError, TypeError):
        pass  # Handle different slowapi versions

    yield

    # Clear after
    _rate_limit_state.clear()
    try:
        if hasattr(limiter, '_storage') and hasattr(limiter._storage, 'storage'):
            limiter._storage.storage.clear()
    except (AttributeError, TypeError):
        pass
```

**When to add:**
- Any new module-level state (caches, counters, limiter state)
- Register cleanup in `_reset_module_state` fixture above

### 3. Centralized Fixtures

**Problem:** Test fixture fragmentation (individual files defining their own fixtures) leads to:
- Partial fixes when infrastructure changes
- Inconsistent test environments
- Missed updates across files

**Solution:** All fixtures in `tests/conftest.py`, referenced by test files.

**Correct Pattern:**
```python
# tests/conftest.py
@pytest.fixture
def test_db(tmp_path):
    # ... database setup ...

@pytest.fixture
def authenticated_user(test_db):
    # ... user creation ...

# tests/test_api.py
def test_endpoint(authenticated_user):
    # Uses fixture from conftest
```

**Incorrect Pattern (BLOCKED by pre-commit):**
```python
# tests/test_api.py
@pytest.fixture
def test_db():  # ❌ BLOCKED: Move to conftest.py
    # ...

def test_endpoint(test_db):
    pass
```

### 4. Avoiding Module-Level State in Code

**Problem:** API code with module-level state breaks isolation.

**Bad Example:**
```python
# api/cache.py
_cache = {}  # ← Persists across tests!

def get_cache_value(key):
    return _cache.get(key)

def set_cache_value(key, value):
    _cache[key] = value
```

**Good Example (Dependency Injection):**
```python
# api/cache.py
class Cache:
    def __init__(self):
        self.data = {}

    def get(self, key):
        return self.data.get(key)

    def set(self, key, value):
        self.data[key] = value

# api/main.py
cache = Cache()

@app.get("/...")
def endpoint(cache: Cache = Depends(lambda: cache)):
    return cache.get("key")
```

**Or (Request-scoped):**
```python
# api/cache.py
class RequestCache:
    def __init__(self, request):
        self.request = request
        self.data = {}

# Each request gets fresh cache instance
```

## Testing Module-Level State

### For Reading:
If a module has unavoidable module-level state:
1. **Add to conftest cleanup** — register in `_reset_module_state`
2. **Document why** — explain why dependency injection wasn't possible
3. **Test isolation** — verify tests don't affect each other

### For Writing:
```python
# Don't:
_global_cache = {}

# Do:
class CacheManager:
    def __init__(self):
        self.cache = {}
```

## API Request/Response Isolation

### Pydantic Validation (`extra='forbid'`)

**Pattern:** Reject unknown fields for security.
```python
class RegisterRequest(BaseModel):
    email: str
    password: str

    class Config:
        extra = 'forbid'  # ← Rejects extra fields
```

**Test Impact:** Tests MUST only send documented fields.

**Common Mistakes:**
```python
# ❌ FAILS: extra field "name" not in RegisterRequest
client.post("/register", json={
    "email": "user@example.com",
    "password": "pass",
    "name": "John",  # ← REJECTED (extra='forbid')
})

# ✅ CORRECT
client.post("/register", json={
    "email": "user@example.com",
    "password": "pass",
})
```

### Response Schema Validation

**Pattern:** Always validate response structure in tests.

**Good Test:**
```python
def test_analytics_endpoint(client, authenticated_user):
    response = client.get(
        "/analytics/revenue",
        headers={"X-API-Key": authenticated_user.api_key},
    )
    assert response.status_code == 200
    data = response.json()

    # Validate schema
    assert "period" in data
    assert "total_revenue_usd" in data
    assert "mrr" in data
    assert "arpu" in data

    # Validate types
    assert isinstance(data["total_revenue_usd"], (int, float))
```

**Bad Test (from PR #5 failures):**
```python
# ❌ Assumes wrong field names
assert "dates" in data  # ← Wrong key, should be "days"
assert "dau" in data    # ← Wrong key, should be "series"

# ❌ Calls method on dict
value = data.lower()  # ← AttributeError: dict has no method lower()
```

## CI vs. Local Differences

### Common Pitfalls

1. **Rate limit quota exhaustion**
   - Local: Fresh quota for each test session
   - CI: Multiple test sessions share quota
   - Fix: Add `_reset_rate_limit_state` fixture

2. **Database file permissions**
   - Local: User owns tmp_path
   - CI: May run as different user
   - Fix: Use `check_same_thread=False`

3. **Concurrent test execution**
   - Local: Tests run serially (default)
   - CI: Tests may run in parallel
   - Fix: Ensure each test has isolated db file

4. **Environment variables**
   - Local: Shell exports
   - CI: os.environ set in conftest
   - Fix: Set in conftest, not shell

## Testing the Isolation

### Run locally with parallel execution:
```bash
# This should NOT fail even with -n parallel workers
pytest tests/ -n auto
```

### Run full suite multiple times:
```bash
# If tests pass in one session but fail in another,
# isolation is broken
for i in {1..5}; do pytest tests/ -q || exit 1; done
```

### Check module state leakage:
```bash
# Add debug to conftest to verify state is clean
@pytest.fixture(autouse=True)
def _verify_clean_state():
    from api.middleware.rate_limiter import _rate_limit_state
    assert len(_rate_limit_state) == 0, "Rate limit state not clean!"
    yield
```

## Adding New Tests

### Checklist:
- [ ] Use fixtures from `conftest.py`, not local definitions
- [ ] Validate response schemas match API spec
- [ ] Use correct Pydantic request fields (no extra fields)
- [ ] Clear module state in `_reset_module_state` if adding new globals
- [ ] Test runs locally: `pytest tests/test_new.py -v`
- [ ] Test runs with others: `pytest tests/ -q` (no failures)
- [ ] Test runs in parallel: `pytest tests/ -n auto` (no failures)

## Troubleshooting

### "sqlite3.OperationalError: no such table"
- **Cause:** Using `:memory:` SQLite or session-scoped fixture
- **Fix:** Use file-based SQLite with function-scoped fixture
- **Check:** `conftest.py` fixture uses `tmp_path`

### "429 Too Many Requests"
- **Cause:** Rate limit quota exhausted in CI
- **Fix:** Add `_reset_rate_limit_state` to `conftest.py`
- **Check:** All module-level state cleared between tests

### "422 Validation Error"
- **Cause:** Test sending extra fields Pydantic rejects
- **Fix:** Remove extra fields from test JSON payload
- **Check:** Test payload matches documented API request schema

### Tests pass locally but fail in CI
- **Cause:** Module state pollution or concurrent execution issues
- **Fix:** Add test to `_reset_module_state` cleanup
- **Check:** `pytest tests/ -n auto` passes locally

## References

- [Pytest Fixtures](https://docs.pytest.org/en/stable/fixture.html)
- [SQLAlchemy Testing](https://docs.sqlalchemy.org/en/20/orm/session_basics.html#when-do-i-construct-a-session)
- [Pydantic Config](https://docs.pydantic.dev/latest/concepts/models/#model-config)
- [FastAPI Testing](https://fastapi.tiangolo.com/advanced/testing-events/)
