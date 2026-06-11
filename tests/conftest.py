"""
Pytest configuration and shared fixtures for all integration tests.

Fixtures provided:
- test_db: Session-scoped SQLite in-memory database
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


def pytest_configure(config):
    """Configure pytest markers."""
    config.addinivalue_line("markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')")
    config.addinivalue_line("markers", "integration: marks tests as integration tests")
    config.addinivalue_line("markers", "websocket: marks tests as WebSocket tests")
    config.addinivalue_line("markers", "load: marks tests as load tests")
