"""
Pytest configuration and shared fixtures for all integration tests.

Fixtures provided:
- test_db: Function-scoped SQLite in-memory database
- client: Test HTTP client with FastAPI TestClient
- test_user: User created in test DB with API key
- authenticated_user_with_wallet: User with wallet setup
- admin_user: User with admin role
- test_persona: Free persona from catalog
- ws_client: WebSocket client wrapper

All fixtures automatically clean up after use.
"""

import sys
import os
from pathlib import Path

# Set test environment before importing app modules
# CRITICAL: Must use os.environ[] directly (not setdefault) to override defaults
os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["STRIPE_SECRET_KEY"] = "sk_test_mock"

# Add repo root to sys.path so tests can import api, needle, persona_math, persona_mcp
repo_root = Path(__file__).parent.parent
sys.path.insert(0, str(repo_root))

# Configure pytest
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from api.db import Base
from api.main import app, get_db


def pytest_configure(config):
    """Configure pytest markers."""
    config.addinivalue_line("markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')")
    config.addinivalue_line("markers", "integration: marks tests as integration tests")
    config.addinivalue_line("markers", "websocket: marks tests as WebSocket tests")
    config.addinivalue_line("markers", "load: marks tests as load tests")


@pytest.fixture
def test_db(tmp_path):
    """Create test database (file-based SQLite for proper session isolation).

    Uses tmp_path because in-memory SQLite (`:memory:`) creates a fresh database
    per connection — `create_all` runs on one connection, the session lands on
    another, and the tables appear to vanish. File-based SQLite shares state
    across connections, while still being per-test (tmp_path is function-scoped).
    """
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


@pytest.fixture(autouse=True)
def _reset_rate_limit_state():
    """Clear per-API-key rate-limit state between tests.

    api/middleware/rate_limiter.py keeps `_rate_limit_state` as a module-level
    dict; without this reset, /auth/register's 5/hour cap is exhausted partway
    through the suite and unrelated tests start failing with 429.
    Also clear slowapi limiter state (uses MemoryStorage keyed by IP).
    """
    from api.middleware.rate_limiter import _rate_limit_state
    from api.main import limiter

    _rate_limit_state.clear()

    # Clear slowapi MemoryStorage (dict-like: limiter._storage.storage)
    try:
        if hasattr(limiter, '_storage') and hasattr(limiter._storage, 'storage'):
            limiter._storage.storage.clear()
    except (AttributeError, TypeError):
        pass  # Ignore if storage doesn't exist or can't be cleared

    yield

    _rate_limit_state.clear()
    try:
        if hasattr(limiter, '_storage') and hasattr(limiter._storage, 'storage'):
            limiter._storage.storage.clear()
    except (AttributeError, TypeError):
        pass  # Ignore if storage doesn't exist or can't be cleared
