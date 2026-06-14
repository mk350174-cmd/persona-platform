"""
Unit tests for api/email_service.py — Resend wrappers + HTML templates.

The module reads RESEND_API_KEY at import time into a module global, so we patch
`api.email_service.RESEND_API_KEY` directly to exercise both the dev-skip path
and the real-send path (with a stubbed `resend` module).
"""

import sys
import types

import pytest

import api.email_service as es


@pytest.fixture
def fake_resend(monkeypatch):
    """Install a stub `resend` module that records the last send() payload."""
    mod = types.ModuleType("resend")
    mod.api_key = None
    sent = {}

    class _Emails:
        @staticmethod
        def send(payload):
            sent["payload"] = payload
            return {"id": "email_123"}

    mod.Emails = _Emails
    monkeypatch.setitem(sys.modules, "resend", mod)
    return sent


# ── dev-skip path (no API key) ───────────────────────────────────────────────

def test_verification_email_skipped_without_key(monkeypatch):
    monkeypatch.setattr(es, "RESEND_API_KEY", "")
    assert es.send_verification_email("a@b.com", "tok") is True


def test_password_reset_skipped_without_key(monkeypatch):
    monkeypatch.setattr(es, "RESEND_API_KEY", "")
    assert es.send_password_reset_email("a@b.com", "tok") is True


def test_purchase_receipt_skipped_without_key(monkeypatch):
    monkeypatch.setattr(es, "RESEND_API_KEY", "")
    assert es.send_purchase_receipt_email("a@b.com", "Socrates", 9.99) is True


# ── real-send path (key present, resend stubbed) ─────────────────────────────

def test_verification_email_sends(monkeypatch, fake_resend):
    monkeypatch.setattr(es, "RESEND_API_KEY", "re_test")
    assert es.send_verification_email("user@x.com", "tok123") is True
    payload = fake_resend["payload"]
    assert payload["to"] == ["user@x.com"]
    assert "tok123" in payload["text"]
    assert "Verify" in payload["subject"]


def test_password_reset_email_sends(monkeypatch, fake_resend):
    monkeypatch.setattr(es, "RESEND_API_KEY", "re_test")
    assert es.send_password_reset_email("user@x.com", "rtok") is True
    assert "rtok" in fake_resend["payload"]["text"]


def test_purchase_receipt_email_sends(monkeypatch, fake_resend):
    monkeypatch.setattr(es, "RESEND_API_KEY", "re_test")
    assert es.send_purchase_receipt_email("user@x.com", "Plato", 19.0,
                                          download_url="http://dl") is True
    assert "Plato" in fake_resend["payload"]["subject"]


# ── send failure → False ─────────────────────────────────────────────────────

def test_send_failure_returns_false(monkeypatch):
    monkeypatch.setattr(es, "RESEND_API_KEY", "re_test")

    mod = types.ModuleType("resend")

    class _Boom:
        @staticmethod
        def send(payload):
            raise RuntimeError("resend down")

    mod.Emails = _Boom
    mod.api_key = None
    monkeypatch.setitem(sys.modules, "resend", mod)
    assert es.send_verification_email("user@x.com", "tok") is False
    assert es.send_password_reset_email("user@x.com", "tok") is False
    assert es.send_purchase_receipt_email("user@x.com", "P", 1.0) is False


# ── HTML templates (pure) ────────────────────────────────────────────────────

def test_verification_html_contains_url():
    html = es._verification_html("http://verify/abc")
    assert "http://verify/abc" in html
    assert "Verify Email" in html


def test_password_reset_html_contains_url():
    html = es._password_reset_html("http://reset/xyz")
    assert "http://reset/xyz" in html
    assert "Reset Password" in html


def test_purchase_receipt_html_with_and_without_download():
    with_dl = es._purchase_receipt_html("Socrates", 9.99, "http://dl")
    assert "Download Config" in with_dl
    assert "Socrates" in with_dl
    assert "9.99" in with_dl

    without_dl = es._purchase_receipt_html("Socrates", 9.99, None)
    assert "Download Config" not in without_dl
