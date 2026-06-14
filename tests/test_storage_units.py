"""
Unit tests for api/storage.py — Supabase Storage wrapper.

No real Supabase: we drive `StorageManager` with a fake client that records calls,
plus the unconfigured path (client is None → graceful None/False returns).
"""

import api.storage as storage
from api.storage import StorageManager, get_storage_manager, is_storage_available


# ── fakes ────────────────────────────────────────────────────────────────────

class _FakeBucket:
    def __init__(self, recorder, fail=False):
        self._rec = recorder
        self._fail = fail

    def upload(self, path, file_bytes, opts):
        if self._fail:
            raise RuntimeError("upload boom")
        self._rec.append(("upload", path))

    def create_signed_url(self, path, expires_in=3600):
        if self._fail:
            raise RuntimeError("sign boom")
        return {"signedURL": f"https://signed/{path}?exp={expires_in}"}

    def remove(self, paths):
        if self._fail:
            raise RuntimeError("remove boom")
        self._rec.append(("remove", tuple(paths)))


class _FakeStorage:
    def __init__(self, recorder, fail=False):
        self._rec = recorder
        self._fail = fail

    def from_(self, bucket):
        return _FakeBucket(self._rec, self._fail)


class _FakeClient:
    def __init__(self, recorder, fail=False):
        self.storage = _FakeStorage(recorder, fail)


def _manager(fail=False):
    m = StorageManager.__new__(StorageManager)   # bypass __init__ (no env needed)
    m.supabase_url = "https://proj.supabase.co"
    m.service_role_key = "svc"
    m.calls = []
    m.client = _FakeClient(m.calls, fail=fail)
    return m


def _unconfigured():
    m = StorageManager.__new__(StorageManager)
    m.supabase_url = ""
    m.service_role_key = ""
    m.client = None
    return m


# ── is_available ─────────────────────────────────────────────────────────────

def test_is_available_true_false():
    assert _manager().is_available() is True
    assert _unconfigured().is_available() is False


def test_init_without_env_has_no_client(monkeypatch):
    monkeypatch.delenv("SUPABASE_URL", raising=False)
    monkeypatch.delenv("SUPABASE_SERVICE_ROLE_KEY", raising=False)
    m = StorageManager()
    assert m.is_available() is False


# ── uploads (success) ────────────────────────────────────────────────────────

def test_upload_avatar_returns_public_url():
    m = _manager()
    url = m.upload_avatar("usr_1", b"\x89PNG")
    assert url == "https://proj.supabase.co/storage/v1/object/public/user-avatars/avatars/usr_1/profile.png"
    assert ("upload", "avatars/usr_1/profile.png") in m.calls


def test_upload_persona_asset_returns_public_url():
    m = _manager()
    url = m.upload_persona_asset("socrates", "portrait.png", b"img")
    assert "persona-assets/personas/socrates/portrait.png" in url


def test_upload_compiled_config_returns_signed_url():
    m = _manager()
    url = m.upload_compiled_config("usr_1", "socrates", "web", b"{}")
    assert url.startswith("https://signed/users/usr_1/socrates/web/config.json")


def test_get_download_url_signed():
    m = _manager()
    url = m.get_download_url("compiled-configs", "p/x.json", expires_in=60)
    assert "exp=60" in url


# ── delete (success) ─────────────────────────────────────────────────────────

def test_delete_file_true():
    m = _manager()
    assert m.delete_file("user-avatars", "avatars/u/profile.png") is True
    assert ("remove", ("avatars/u/profile.png",)) in m.calls


def test_delete_user_files_true():
    m = _manager()
    assert m.delete_user_files("usr_1") is True


# ── unconfigured → graceful None/False ───────────────────────────────────────

def test_unconfigured_uploads_return_none():
    m = _unconfigured()
    assert m.upload_avatar("u", b"x") is None
    assert m.upload_persona_asset("p", "f.png", b"x") is None
    assert m.upload_compiled_config("u", "p", "web", b"x") is None
    assert m.get_download_url("b", "p") is None


def test_unconfigured_deletes_return_false():
    m = _unconfigured()
    assert m.delete_file("b", "p") is False
    assert m.delete_user_files("u") is False


# ── failure paths → graceful None/False ──────────────────────────────────────

def test_upload_failures_return_none():
    m = _manager(fail=True)
    assert m.upload_avatar("u", b"x") is None
    assert m.upload_persona_asset("p", "f.png", b"x") is None
    assert m.upload_compiled_config("u", "p", "web", b"x") is None
    assert m.get_download_url("b", "p") is None


def test_delete_failures_return_false():
    m = _manager(fail=True)
    assert m.delete_file("b", "p") is False
    assert m.delete_user_files("u") is False


# ── module-level singleton helpers ───────────────────────────────────────────

def test_get_storage_manager_singleton(monkeypatch):
    monkeypatch.setattr(storage, "_storage_manager", None)
    a = get_storage_manager()
    b = get_storage_manager()
    assert a is b


def test_is_storage_available_delegates(monkeypatch):
    monkeypatch.setattr(storage, "_storage_manager", _manager())
    assert is_storage_available() is True
    monkeypatch.setattr(storage, "_storage_manager", _unconfigured())
    assert is_storage_available() is False
