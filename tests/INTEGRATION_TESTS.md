# Backend Integration Tests — Persona Platform

Comprehensive test suite for the Persona Platform backend API and WebSocket endpoints.

## Overview

This test suite provides 30+ integration test cases covering:

### HTTP REST API Tests (`test_backend_integration.py`)
- **Health checks**: API connectivity, cache status
- **Authentication**: Registration, login, token validation
- **Persona API**: List, detail, CEID measurement, compilation
- **Purchase API**: Checkout, purchase list, refunds, wallet management
- **Analytics API**: Dashboard, revenue reports, exports (admin-only)
- **Error handling**: 401 Unauthorized, 403 Forbidden, 404 Not Found, 422 Validation
- **End-to-end workflows**: Complete signup → purchase → compile flows

### WebSocket Tests (`test_websocket_integration.py`)
- **Connection**: Authentication, tier negotiation, clean teardown
- **Messaging**: Send/receive text chunks, streaming order, protocol compliance
- **Error recovery**: Reconnection, message queue, backpressure handling
- **Load testing**: Concurrent connections (5-100+)
- **Latency**: Round-trip time, streaming chunk rate

## Quick Start

### Install Dependencies

```bash
pip install -r requirements-load-test.txt
```

### Run All Tests

```bash
pytest tests/ -v
```

### Run Specific Test Suite

```bash
# REST API tests only
pytest tests/test_backend_integration.py -v

# WebSocket tests only
pytest tests/test_websocket_integration.py -v

# Platform integration (existing tests)
pytest tests/test_platform_integration.py -v
```

### Run Specific Test Class

```bash
# Authentication tests
pytest tests/test_backend_integration.py::TestAuthenticationFlow -v

# Persona API tests
pytest tests/test_backend_integration.py::TestPersonaAPIEndpoints -v

# Purchase API tests
pytest tests/test_backend_integration.py::TestPurchaseAPI -v

# WebSocket connection tests
pytest tests/test_websocket_integration.py::TestWebSocketConnection -v
```

### Run with Markers

```bash
# Skip slow tests (load tests)
pytest tests/ -v -m "not slow"

# Run only integration tests
pytest tests/ -v -m "integration"

# Run only WebSocket tests
pytest tests/ -v -m "websocket"
```

## Test Structure

### Fixtures (Automatically Provided)

All fixtures are defined in `conftest.py` and automatically available to tests:

#### Database Fixtures
- `test_db`: In-memory SQLite database (session-scoped)
  - Pre-populated with schema
  - Shared across tests in same session
  
#### HTTP Client
- `client`: FastAPI TestClient with database override
  - Makes real API calls
  - No mocking (except database)
  - Fresh instance per test

#### User Fixtures
- `test_user(test_db)`: Standard user with API key
  - Email: `testuser@example.com`
  - Password: `password123`
  - Returns: `(user_obj, api_key_str)`

- `authenticated_user_with_wallet(test_db, test_user)`: User with wallet
  - Extends `test_user` with wallet setup
  - Initial balance: $0

- `authenticated_user_with_credits(test_db, authenticated_user_with_wallet)`: User with credits
  - Extends wallet fixture with $100 credit
  - Balance: 10000 cents = $100

- `admin_user(test_db)`: Admin user for privileged endpoints
  - Email: `admin@example.com`
  - Password: `adminpass123`
  - Role: `"admin"`

#### Persona Fixtures
- `test_persona(test_db)`: Free persona from catalog
  - Automatically finds first free persona
  - Returns: `(persona_id, metadata_dict)`

#### WebSocket
- `ws_client(client)`: WebSocket-enabled test client
  - Same as HTTP client but supports `.websocket_connect()`

### Example Test

```python
def test_user_can_view_profile(client, test_user):
    """Test that authenticated user can fetch their profile."""
    user, api_key = test_user
    
    response = client.get(
        "/me",
        headers={"X-API-Key": api_key}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == user.email
```

## Test Categories

### 1. Health Check Tests

Verify API is running and healthy.

```bash
pytest tests/test_backend_integration.py::TestHealthEndpoint -v
```

**Tests:**
- API responds to `/health` without auth
- Health response includes status information

### 2. Authentication Tests

Verify user registration, login, and session management.

```bash
pytest tests/test_backend_integration.py::TestAuthenticationFlow -v
```

**Tests:**
- User registration with valid email/password
- Duplicate email rejection
- Login with valid/invalid credentials
- Get current user profile
- Missing auth returns 401

### 3. Persona API Tests

Verify persona listing, detail view, CEID measurement, compilation.

```bash
pytest tests/test_backend_integration.py::TestPersonaAPIEndpoints -v
```

**Tests:**
- List personas (public)
- Get persona detail (public)
- Measure CEID (authenticated)
- Compile persona (requires purchase)
- Free personas skip purchase check

### 4. Purchase API Tests

Verify checkout, purchase history, refunds, wallet.

```bash
pytest tests/test_backend_integration.py::TestPurchaseAPI -v
```

**Tests:**
- Get empty purchase list for new user
- Personas appear in purchase list after grant
- Checkout requires authentication
- Checkout returns Stripe session URL
- Mock purchase endpoint for dev
- Wallet balance queries
- Refunds require admin role

### 5. Analytics API Tests

Verify admin-only analytics endpoints.

```bash
pytest tests/test_backend_integration.py::TestAnalyticsAPI -v
```

**Tests:**
- Dashboard requires admin role
- Admin can access dashboard
- Top personas endpoint
- Revenue report
- CSV export functionality
- DAU (Daily Active Users) report

### 6. Error Handling Tests

Verify proper error responses.

```bash
pytest tests/test_backend_integration.py::TestErrorHandling -v
```

**Tests:**
- Invalid API key → 401
- Missing API key → 401
- Forbidden access → 403
- Nonexistent endpoint → 404
- Invalid request body → 422
- Error responses include detail message

### 7. End-to-End Workflow Tests

Verify complete workflows work together.

```bash
pytest tests/test_backend_integration.py::TestEndToEndWorkflows -v
```

**Tests:**
- Register → Get profile (signup workflow)
- Browse → Compile free persona
- View purchase history
- Admin views dashboard and exports

### 8. WebSocket Connection Tests

Verify WebSocket establishment and teardown.

```bash
pytest tests/test_websocket_integration.py::TestWebSocketConnection -v
```

**Tests:**
- Connect with valid auth
- Connection fails without auth
- Connection fails with invalid key
- Invalid persona rejected
- Tier parameter handling (text, voice, full)

### 9. WebSocket Messaging Tests

Verify message sending and streaming.

```bash
pytest tests/test_websocket_integration.py::TestWebSocketMessaging -v
```

**Tests:**
- Send message, receive streamed response
- Text chunk order preserved
- Oversized messages rejected
- Ping-pong exchange
- Voice tier includes audio
- Full tier includes visual updates

### 10. WebSocket Error Recovery Tests

Verify error handling and recovery.

```bash
pytest tests/test_websocket_integration.py::TestWebSocketErrorRecovery -v
```

**Tests:**
- Clean connection close
- Rapid reconnection
- Message queue under load
- Connection limit per user (default: 5)
- Rate limiting on messages (default: 30/60s)

### 11. WebSocket Load Tests

Verify concurrent connection handling.

```bash
pytest tests/test_websocket_integration.py::TestWebSocketLoad -v -m "slow"
```

**Tests:**
- 10 concurrent connections
- Concurrent messaging on multiple connections
- Sustained connection with multiple interactions

### 12. WebSocket Latency Tests

Verify real-time performance.

```bash
pytest tests/test_websocket_integration.py::TestWebSocketLatency -v
```

**Tests:**
- Message round-trip time (target: < 500ms for first chunk)
- Streaming chunk rate (target: < 500ms between chunks)

## Common Test Patterns

### Testing with Authentication

```python
def test_authenticated_endpoint(client, test_user):
    user, api_key = test_user
    
    response = client.get(
        "/some/protected/endpoint",
        headers={"X-API-Key": api_key}
    )
    
    assert response.status_code == 200
```

### Testing with Admin Role

```python
def test_admin_only_endpoint(client, admin_user):
    admin, admin_key = admin_user
    
    response = client.get(
        "/admin/privileged/endpoint",
        headers={"X-API-Key": admin_key}
    )
    
    assert response.status_code == 200
```

### Testing Error Cases

```python
def test_error_case(client):
    response = client.get("/nonexistent/endpoint")
    
    assert response.status_code == 404
    data = response.json()
    assert "detail" in data
```

### Testing with Database State

```python
def test_with_database_setup(client, test_db, test_user, test_persona):
    user, api_key = test_user
    persona_id, _ = test_persona
    
    # Set up test data
    from api.db import grant_free_persona
    grant_free_persona(test_db, user.id, persona_id)
    test_db.commit()
    
    # Test with prepared state
    response = client.get(
        "/me/purchases",
        headers={"X-API-Key": api_key}
    )
    
    assert response.status_code == 200
```

### Testing WebSocket

```python
def test_websocket_message(ws_client, test_user, test_persona):
    user, api_key = test_user
    persona_id, _ = test_persona
    
    with ws_client.websocket_connect(
        f"/ws/chat/{persona_id}?tier=text",
        headers={"Authorization": f"Bearer {api_key}"}
    ) as websocket:
        # Send message
        websocket.send_json({
            "type": "message",
            "text": "Hello"
        })
        
        # Receive response
        response = websocket.receive_json()
        assert response["type"] in ["text_chunk", "error"]
```

## Configuration

### Environment Variables

Tests use these environment variables (auto-set to test values):

```bash
DATABASE_URL=sqlite:///:memory:        # In-memory test database
STRIPE_SECRET_KEY=sk_test_mock        # Mock Stripe key
```

### Pytest Configuration

Tests use pytest markers for organization:

```bash
# Skip slow tests
pytest tests/ -v -m "not slow"

# Run only integration tests
pytest tests/ -v -m "integration"

# Run only WebSocket tests
pytest tests/ -v -m "websocket"
```

Available markers:
- `@pytest.mark.slow`: Load tests, sustained tests
- `@pytest.mark.integration`: All integration tests (default)
- `@pytest.mark.websocket`: WebSocket-specific tests
- `@pytest.mark.load`: Load tests

## Test Results

### Success Indicators

✓ All 30+ tests pass
✓ No database errors
✓ No auth/permission issues
✓ Response schemas valid
✓ Error messages clear

### Common Issues

**Tests fail with "DATABASE_URL not set"**
- Fixtures automatically set `os.environ["DATABASE_URL"]`
- If manually running, set: `export DATABASE_URL="sqlite:///:memory:"`

**WebSocket tests hang or timeout**
- Some tests use `pytest.mark.slow`
- Run with: `pytest tests/ -m "not slow"` to skip
- Or: `pytest tests/test_websocket_integration.py::TestWebSocketConnection::test_websocket_connection_succeeds_with_auth --timeout=10`

**"404 Not Found" on endpoints**
- Endpoint may not be implemented yet
- Test checks for multiple status codes: `assert response.status_code in [200, 404]`
- Review test comments to understand expected vs. actual behavior

**"401 Unauthorized" with valid key**
- Verify fixture creates user in same database instance
- Check `app.dependency_overrides[get_db]` is set
- Review auth logic in `api/auth.py`

## Extending Tests

### Adding a New Test

```python
class TestNewFeature:
    """Test description."""
    
    def test_feature_works(self, client, test_user):
        """Specific test description."""
        user, api_key = test_user
        
        response = client.get(
            "/new/feature/endpoint",
            headers={"X-API-Key": api_key}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "expected_field" in data
```

### Using Database in Tests

```python
def test_with_database(client, test_db, test_user):
    """Test that uses database directly."""
    user, api_key = test_user
    
    # Modify database
    from api.db import some_function
    some_function(test_db, user.id, "some_data")
    test_db.commit()
    
    # Test behavior after modification
    response = client.get("/me", headers={"X-API-Key": api_key})
    assert response.status_code == 200
```

### Adding Fixtures

Add to `conftest.py`:

```python
@pytest.fixture
def my_custom_fixture(test_db):
    """Description of fixture."""
    # Setup
    data = create_test_data(test_db)
    yield data
    # Cleanup happens automatically
```

## Performance Benchmarks

Target latencies (from WebSocket tests):
- API response: < 100ms
- WebSocket connection: < 500ms
- First text chunk: < 500ms
- Chunk streaming: < 500ms between chunks
- Concurrent connections: 5-100+ simultaneous

## Debugging

### Run with Verbose Output

```bash
pytest tests/ -vv -s
```

### Run Single Test

```bash
pytest tests/test_backend_integration.py::TestAuthenticationFlow::test_user_registration_succeeds -v
```

### Show Print Statements

```bash
pytest tests/ -v -s
```

### Drop into Debugger on Failure

```bash
pytest tests/ -v --pdb
```

### Generate HTML Report

```bash
pytest tests/ -v --html=report.html --self-contained-html
```

## CI/CD Integration

### GitHub Actions Example

```yaml
name: Integration Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - run: pip install -r requirements-load-test.txt
      - run: pytest tests/ -v --junitxml=results.xml
      - uses: actions/upload-artifact@v3
        if: failure()
        with:
          name: test-results
          path: results.xml
```

## Coverage

Generate test coverage report:

```bash
pip install pytest-cov
pytest tests/ --cov=api --cov=persona_math --cov-report=html
open htmlcov/index.html
```

## Performance Testing

For load testing beyond unit tests, see:
- `tests/load_test_payments.py` — Locust-based payment endpoint load tests
- `tests/analyze_load_results.py` — Result analysis tool

## Support

For issues or questions:
1. Check test output for error details
2. Review test comments explaining expected behavior
3. Check API endpoint implementation
4. Verify database/auth setup

---

**Last Updated**: June 2026
**Target**: 30+ integration tests covering critical workflows
**Status**: Ready for use
