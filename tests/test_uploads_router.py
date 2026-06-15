"""
Tests for api/routers/uploads.py

Coverage targets:
  - Lines 32-76: upload_avatar (invalid type, too large, storage unavailable, upload fail, success)
  - Lines 97-159: upload_compiled_config (invalid type, too large, invalid platform, unavailable, fail, success)
  - Lines 175-190: delete_avatar (unavailable, delete fail, success)
  - Line 199: storage_status endpoint
"""

import io
import os
import pytest

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("STRIPE_SECRET_KEY", "sk_test_mock")

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from unittest.mock import MagicMock

from api.db import Base, create_user
from api.main import app, get_db
from api.auth import get_current_user
import api.routers.uploads as uploads_module


# ─────────────────────────────────────────────────────────────────────────────
# FIXTURES
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture
def test_db(tmp_path):
    db_file = tmp_path / "uploads_test.db"
    engine = create_engine(
        f"sqlite:///{db_file}",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    session = SessionLocal()
    yield session
    session.close()


@pytest.fixture
def test_user(test_db):
    user, full_key = create_user(test_db, "upload_test@example.com")
    return user, full_key


@pytest.fixture
def client(test_db, test_user):
    user, full_key = test_user

    def override_get_db():
        yield test_db

    def override_get_current_user():
        return user

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user
    yield TestClient(app)
    app.dependency_overrides.clear()


def _make_storage_mock(is_available=True, avatar_url=None, config_url=None, delete_ok=True):
    """Create a mock StorageManager."""
    mock = MagicMock()
    mock.is_available.return_value = is_available
    mock.upload_avatar.return_value = avatar_url
    mock.upload_compiled_config.return_value = config_url
    mock.delete_file.return_value = delete_ok
    return mock


# ─────────────────────────────────────────────────────────────────────────────
# AVATAR UPLOAD TESTS (lines 32-76)
# ─────────────────────────────────────────────────────────────────────────────

class TestAvatarUpload:
    def test_invalid_file_type_returns_400(self, client, monkeypatch):
        """Line 32-36: invalid content_type → 400."""
        monkeypatch.setattr(
            uploads_module, "get_storage_manager",
            lambda: _make_storage_mock(is_available=True),
        )
        files = {"file": ("test.gif", io.BytesIO(b"fake gif data"), "image/gif")}
        resp = client.post("/uploads/avatar", files=files)
        assert resp.status_code == 400
        assert "Invalid file type" in resp.json()["detail"]

    def test_file_too_large_returns_413(self, client, monkeypatch):
        """Lines 39-45: file > 5MB → 413."""
        monkeypatch.setattr(
            uploads_module, "get_storage_manager",
            lambda: _make_storage_mock(is_available=True),
        )
        large_data = b"x" * (5 * 1024 * 1024 + 1)  # 5MB + 1 byte
        files = {"file": ("big.jpg", io.BytesIO(large_data), "image/jpeg")}
        resp = client.post("/uploads/avatar", files=files)
        assert resp.status_code == 413

    def test_storage_unavailable_returns_503(self, client, monkeypatch):
        """Lines 48-53: storage not available → 503."""
        monkeypatch.setattr(
            uploads_module, "get_storage_manager",
            lambda: _make_storage_mock(is_available=False),
        )
        files = {"file": ("avatar.png", io.BytesIO(b"fake png"), "image/png")}
        resp = client.post("/uploads/avatar", files=files)
        assert resp.status_code == 503

    def test_upload_fails_returns_500(self, client, monkeypatch, test_db):
        """Lines 56-61: storage returns None URL → 500."""
        monkeypatch.setattr(
            uploads_module, "get_storage_manager",
            lambda: _make_storage_mock(is_available=True, avatar_url=None),
        )
        files = {"file": ("avatar.jpg", io.BytesIO(b"fake jpeg"), "image/jpeg")}
        resp = client.post("/uploads/avatar", files=files)
        assert resp.status_code == 500

    def test_upload_success_returns_url(self, client, monkeypatch, test_db):
        """Lines 62-80: successful upload returns avatar_url."""
        avatar_url = "https://storage.example.com/avatars/user123/profile.png"
        monkeypatch.setattr(
            uploads_module, "get_storage_manager",
            lambda: _make_storage_mock(is_available=True, avatar_url=avatar_url),
        )
        files = {"file": ("avatar.webp", io.BytesIO(b"fake webp data"), "image/webp")}
        resp = client.post("/uploads/avatar", files=files)
        assert resp.status_code == 200
        data = resp.json()
        assert data["avatar_url"] == avatar_url
        assert "size_bytes" in data
        assert data["message"] == "Avatar uploaded successfully"

    def test_upload_png_accepted(self, client, monkeypatch):
        """PNG MIME type is accepted (image/png)."""
        avatar_url = "https://storage.example.com/avatars/user/profile.png"
        monkeypatch.setattr(
            uploads_module, "get_storage_manager",
            lambda: _make_storage_mock(is_available=True, avatar_url=avatar_url),
        )
        files = {"file": ("avatar.png", io.BytesIO(b"png data"), "image/png")}
        resp = client.post("/uploads/avatar", files=files)
        assert resp.status_code == 200


# ─────────────────────────────────────────────────────────────────────────────
# COMPILED CONFIG UPLOAD TESTS (lines 97-159)
# ─────────────────────────────────────────────────────────────────────────────

class TestCompiledConfigUpload:
    def test_invalid_content_type_returns_400(self, client, monkeypatch):
        """Lines 97-101: non-JSON content type → 400."""
        monkeypatch.setattr(
            uploads_module, "get_storage_manager",
            lambda: _make_storage_mock(is_available=True),
        )
        files = {"file": ("config.txt", io.BytesIO(b'{"k":"v"}'), "text/plain")}
        resp = client.post("/uploads/compiled-config/persona_abc?platform=ios", files=files)
        assert resp.status_code == 400
        assert "JSON" in resp.json()["detail"]

    def test_file_too_large_returns_413(self, client, monkeypatch):
        """Lines 103-109: file > 10MB → 413."""
        monkeypatch.setattr(
            uploads_module, "get_storage_manager",
            lambda: _make_storage_mock(is_available=True),
        )
        large_data = b"x" * (10 * 1024 * 1024 + 1)
        files = {"file": ("config.json", io.BytesIO(large_data), "application/json")}
        resp = client.post("/uploads/compiled-config/persona_abc?platform=android", files=files)
        assert resp.status_code == 413

    def test_invalid_platform_returns_400(self, client, monkeypatch):
        """Lines 112-118: invalid platform → 400."""
        monkeypatch.setattr(
            uploads_module, "get_storage_manager",
            lambda: _make_storage_mock(is_available=True),
        )
        files = {"file": ("config.json", io.BytesIO(b'{"k":"v"}'), "application/json")}
        resp = client.post("/uploads/compiled-config/persona_abc?platform=raspberry", files=files)
        assert resp.status_code == 400
        assert "Invalid platform" in resp.json()["detail"]

    def test_storage_unavailable_returns_503(self, client, monkeypatch):
        """Lines 121-126: storage unavailable → 503."""
        monkeypatch.setattr(
            uploads_module, "get_storage_manager",
            lambda: _make_storage_mock(is_available=False),
        )
        files = {"file": ("config.json", io.BytesIO(b'{"k":"v"}'), "application/json")}
        resp = client.post("/uploads/compiled-config/persona_abc?platform=ios", files=files)
        assert resp.status_code == 503

    def test_upload_fails_returns_500(self, client, monkeypatch):
        """Lines 134-139: upload_compiled_config returns None → 500."""
        monkeypatch.setattr(
            uploads_module, "get_storage_manager",
            lambda: _make_storage_mock(is_available=True, config_url=None),
        )
        files = {"file": ("config.json", io.BytesIO(b'{"k":"v"}'), "application/json")}
        resp = client.post("/uploads/compiled-config/persona_abc?platform=web", files=files)
        assert resp.status_code == 500

    def test_upload_success_returns_download_url(self, client, monkeypatch):
        """Lines 140-166: successful upload returns download_url."""
        download_url = "https://storage.example.com/signed/config.json?token=abc"
        monkeypatch.setattr(
            uploads_module, "get_storage_manager",
            lambda: _make_storage_mock(is_available=True, config_url=download_url),
        )
        files = {"file": ("config.json", io.BytesIO(b'{"persona":"test"}'), "application/json")}
        resp = client.post("/uploads/compiled-config/persona_socrates?platform=android", files=files)
        assert resp.status_code == 200
        data = resp.json()
        assert data["download_url"] == download_url
        assert data["persona_id"] == "persona_socrates"
        assert data["platform"] == "android"
        assert data["expires_in_seconds"] == 3600
        assert "size_bytes" in data

    @pytest.mark.parametrize("platform", ["ios", "android", "web", "windows", "macos"])
    def test_all_valid_platforms_accepted(self, client, monkeypatch, platform):
        """All valid platforms pass validation."""
        download_url = f"https://storage.example.com/config_{platform}.json"
        monkeypatch.setattr(
            uploads_module, "get_storage_manager",
            lambda: _make_storage_mock(is_available=True, config_url=download_url),
        )
        files = {"file": ("config.json", io.BytesIO(b'{}'), "application/json")}
        resp = client.post(f"/uploads/compiled-config/persona_p?platform={platform}", files=files)
        assert resp.status_code == 200


# ─────────────────────────────────────────────────────────────────────────────
# DELETE AVATAR TESTS (lines 175-190)
# ─────────────────────────────────────────────────────────────────────────────

class TestDeleteAvatar:
    def test_storage_unavailable_returns_503(self, client, monkeypatch):
        """Lines 175-180: storage unavailable → 503."""
        monkeypatch.setattr(
            uploads_module, "get_storage_manager",
            lambda: _make_storage_mock(is_available=False),
        )
        resp = client.delete("/uploads/avatar")
        assert resp.status_code == 503

    def test_delete_success(self, client, monkeypatch, test_db, test_user):
        """Lines 183-188: successful delete."""
        monkeypatch.setattr(
            uploads_module, "get_storage_manager",
            lambda: _make_storage_mock(is_available=True, delete_ok=True),
        )
        resp = client.delete("/uploads/avatar")
        assert resp.status_code == 200
        assert resp.json()["message"] == "Avatar deleted"

    def test_delete_fails_returns_500(self, client, monkeypatch):
        """Lines 190-193: delete_file returns False → 500."""
        monkeypatch.setattr(
            uploads_module, "get_storage_manager",
            lambda: _make_storage_mock(is_available=True, delete_ok=False),
        )
        resp = client.delete("/uploads/avatar")
        assert resp.status_code == 500


# ─────────────────────────────────────────────────────────────────────────────
# STORAGE STATUS TESTS (line 199)
# ─────────────────────────────────────────────────────────────────────────────

class TestStorageStatus:
    def test_storage_status_available(self, client, monkeypatch):
        """Line 199: storage_status returns availability."""
        monkeypatch.setattr(uploads_module, "is_storage_available", lambda: True)
        resp = client.get("/uploads/status")
        assert resp.status_code == 200
        data = resp.json()
        assert data["storage_available"] is True
        assert data["service"] == "Supabase Storage"

    def test_storage_status_unavailable(self, client, monkeypatch):
        """Line 199: storage unavailable shown in status."""
        monkeypatch.setattr(uploads_module, "is_storage_available", lambda: False)
        resp = client.get("/uploads/status")
        assert resp.status_code == 200
        data = resp.json()
        assert data["storage_available"] is False
