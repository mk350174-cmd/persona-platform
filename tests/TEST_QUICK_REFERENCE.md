# Integration Tests — Quick Reference

## Run All Tests

```bash
pytest tests/ -v
```

## Run Specific Suite

```bash
pytest tests/test_backend_integration.py -v     # REST API tests
pytest tests/test_websocket_integration.py -v   # WebSocket tests
```

## Run by Category

```bash
# Authentication
pytest tests/test_backend_integration.py::TestAuthenticationFlow -v

# Personas
pytest tests/test_backend_integration.py::TestPersonaAPIEndpoints -v

# Purchases & Billing
pytest tests/test_backend_integration.py::TestPurchaseAPI -v

# Admin Analytics
pytest tests/test_backend_integration.py::TestAnalyticsAPI -v

# WebSocket Connections
pytest tests/test_websocket_integration.py::TestWebSocketConnection -v

# WebSocket Messaging
pytest tests/test_websocket_integration.py::TestWebSocketMessaging -v

# Error Handling
pytest tests/test_backend_integration.py::TestErrorHandling -v

# End-to-End Workflows
pytest tests/test_backend_integration.py::TestEndToEndWorkflows -v
```

## Skip Slow Tests

```bash
pytest tests/ -v -m "not slow"
```

## Single Test

```bash
pytest tests/test_backend_integration.py::TestAuthenticationFlow::test_user_registration_succeeds -v
```

## Verbose Output

```bash
pytest tests/ -vv -s
```

## With Coverage

```bash
pytest tests/ --cov=api --cov-report=term-missing
```

## Available Fixtures

All automatically provided to tests:

```python
# Database
test_db                                    # In-memory SQLite

# HTTP Client
client                                     # FastAPI TestClient

# Users
test_user                                  # Regular user + API key
authenticated_user_with_wallet             # User with wallet
authenticated_user_with_credits            # User with $100 credit
admin_user                                 # Admin user

# Data
test_persona                               # Free test persona

# WebSocket
ws_client                                  # WebSocket-enabled client
```

## Common Test Patterns

### Authenticated Request

```python
def test_something(client, test_user):
    user, api_key = test_user
    response = client.get(
        "/me",
        headers={"X-API-Key": api_key}
    )
    assert response.status_code == 200
```

### Admin Request

```python
def test_admin_endpoint(client, admin_user):
    admin, admin_key = admin_user
    response = client.get(
        "/analytics/dashboard",
        headers={"X-API-Key": admin_key}
    )
    assert response.status_code == 200
```

### With Database Setup

```python
def test_with_setup(client, test_db, test_user, test_persona):
    user, api_key = test_user
    persona_id, _ = test_persona
    
    from api.db import grant_free_persona
    grant_free_persona(test_db, user.id, persona_id)
    test_db.commit()
    
    response = client.get("/me/purchases", headers={"X-API-Key": api_key})
    assert response.status_code == 200
```

### WebSocket

```python
def test_ws(ws_client, test_user, test_persona):
    user, api_key = test_user
    persona_id, _ = test_persona
    
    with ws_client.websocket_connect(
        f"/ws/chat/{persona_id}?tier=text",
        headers={"Authorization": f"Bearer {api_key}"}
    ) as ws:
        ws.send_json({"type": "message", "text": "Hi"})
        response = ws.receive_json()
        assert response is not None
```

## Test File Layout

```
tests/
├── conftest.py                       # Shared fixtures
├── test_backend_integration.py       # REST API tests (30+ cases)
├── test_websocket_integration.py     # WebSocket tests (20+ cases)
├── test_platform_integration.py      # Existing needle tests
├── INTEGRATION_TESTS.md              # Full documentation
└── TEST_QUICK_REFERENCE.md           # This file
```

## Test Counts by Suite

- **Health checks**: 2 tests
- **Authentication**: 7 tests
- **Persona API**: 8 tests
- **Purchase API**: 9 tests
- **Analytics API**: 6 tests
- **Error handling**: 6 tests
- **End-to-end workflows**: 4 tests
- **WebSocket connection**: 7 tests
- **WebSocket messaging**: 5 tests
- **WebSocket error recovery**: 5 tests
- **WebSocket load**: 3 tests
- **WebSocket latency**: 2 tests

**Total: 64 integration test cases**

## Environment Setup

Automatic (in conftest.py):
```python
os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["STRIPE_SECRET_KEY"] = "sk_test_mock"
```

## Debugging

```bash
# Show all output
pytest tests/test_backend_integration.py -vv -s

# Drop into debugger on failure
pytest tests/test_backend_integration.py --pdb

# Stop on first failure
pytest tests/test_backend_integration.py -x
```

## Expected Status Codes

### Success
- 200 OK — Successful request
- 201 Created — Resource created

### Client Errors
- 400 Bad Request — Invalid input
- 401 Unauthorized — Missing/invalid auth
- 403 Forbidden — Auth valid but not permitted
- 404 Not Found — Resource not found
- 422 Validation Error — Invalid request schema
- 429 Too Many Requests — Rate limited

### Server Errors
- 500 Internal Server Error — Server error
- 502 Bad Gateway — External service error
- 503 Service Unavailable — Service temporarily down

## Test Assertions

```python
# Status code
assert response.status_code == 200
assert response.status_code in [200, 201]

# JSON structure
data = response.json()
assert "field_name" in data
assert isinstance(data["array"], list)
assert len(data["items"]) > 0

# String content
assert "keyword" in response.text

# Headers
assert "application/json" in response.headers["content-type"]
```

## Installation

```bash
pip install -r requirements-load-test.txt
```

Required packages:
- pytest >= 7.0.0
- pytest-asyncio >= 0.21.0
- httpx >= 0.24.0
- websockets >= 12.0
- fastapi >= 0.100.0

---

See **INTEGRATION_TESTS.md** for full documentation.
