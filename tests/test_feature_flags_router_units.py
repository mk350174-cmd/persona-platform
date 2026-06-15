"""
Unit tests for api/routers/feature_flags.py — called as plain functions.

Synchronous endpoints depending only on (user, db) are invoked directly with a
fake user and seeded `test_db`.
"""

import pytest
from fastapi import HTTPException

from api.routers import feature_flags as ffr
from api.db import create_user


def _user(test_db):
    u, _ = create_user(test_db, "ff@router.com")
    u.role = "admin"
    test_db.commit()
    return u


# ── create / get / list ──────────────────────────────────────────────────────

def test_create_and_get_flag(test_db):
    user = _user(test_db)
    created = ffr.create_flag(name="dark_mode", description="UI", enabled=True,
                              rollout_percentage=50, user=user, db=test_db)
    assert created["name"] == "dark_mode"
    got = ffr.get_flag("dark_mode", user=user, db=test_db)
    assert got["enabled"] is True


def test_create_duplicate_conflicts(test_db):
    user = _user(test_db)
    ffr.create_flag(name="dup", user=user, db=test_db)
    with pytest.raises(HTTPException) as ei:
        ffr.create_flag(name="dup", user=user, db=test_db)
    assert ei.value.status_code == 409


def test_get_missing_flag_404(test_db):
    with pytest.raises(HTTPException) as ei:
        ffr.get_flag("ghost", user=_user(test_db), db=test_db)
    assert ei.value.status_code == 404


def test_list_flags(test_db):
    user = _user(test_db)
    ffr.create_flag(name="on", enabled=True, user=user, db=test_db)
    ffr.create_flag(name="off", enabled=False, user=user, db=test_db)
    out = ffr.list_flags(user=user, db=test_db)
    assert out["total"] >= 2
    on_only = ffr.list_flags(enabled_only=True, user=user, db=test_db)
    assert all(f["enabled"] for f in on_only["flags"])


# ── update / delete ──────────────────────────────────────────────────────────

def test_update_flag(test_db):
    user = _user(test_db)
    ffr.create_flag(name="upd", enabled=False, user=user, db=test_db)
    out = ffr.update_flag("upd", enabled=True, rollout_percentage=100, user=user, db=test_db)
    assert out["enabled"] is True and out["rollout_percentage"] == 100


def test_update_missing_404(test_db):
    with pytest.raises(HTTPException) as ei:
        ffr.update_flag("ghost", enabled=True, user=_user(test_db), db=test_db)
    assert ei.value.status_code == 404


def test_delete_flag(test_db):
    user = _user(test_db)
    ffr.create_flag(name="del", user=user, db=test_db)
    out = ffr.delete_flag("del", user=user, db=test_db)
    assert "deleted" in out["message"]


def test_delete_missing_404(test_db):
    with pytest.raises(HTTPException) as ei:
        ffr.delete_flag("ghost", user=_user(test_db), db=test_db)
    assert ei.value.status_code == 404


# ── stats / evaluate ─────────────────────────────────────────────────────────

def test_flag_statistics(test_db):
    user = _user(test_db)
    ffr.create_flag(name="stat", enabled=True, rollout_percentage=100, user=user, db=test_db)
    out = ffr.get_flag_statistics("stat", hours=24, user=user, db=test_db)
    assert out["flag_name"] == "stat" and out["total"] == 0


def test_flag_statistics_missing_404(test_db):
    with pytest.raises(HTTPException) as ei:
        ffr.get_flag_statistics("ghost", user=_user(test_db), db=test_db)
    assert ei.value.status_code == 404


def test_evaluate_flag_enabled(test_db):
    user = _user(test_db)
    ffr.create_flag(name="eval", enabled=True, rollout_percentage=100, user=user, db=test_db)
    out = ffr.evaluate_flag("eval", tier="pro", user=user, db=test_db)
    assert out["enabled"] is True
    assert out["variant"] == "enabled"


def test_evaluate_flag_missing_404(test_db):
    with pytest.raises(HTTPException) as ei:
        ffr.evaluate_flag("ghost", user=_user(test_db), db=test_db)
    assert ei.value.status_code == 404
