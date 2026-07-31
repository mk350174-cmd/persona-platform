from api.feature_flags import is_enabled


def test_flag_off_by_default(monkeypatch):
    monkeypatch.delenv("FEATURE_NEW_CHAT_UI", raising=False)
    assert is_enabled("new_chat_ui") is False


def test_flag_on_via_env_var(monkeypatch):
    monkeypatch.setenv("FEATURE_NEW_CHAT_UI", "1")
    assert is_enabled("new_chat_ui") is True


def test_flag_accepts_true_yes_on(monkeypatch):
    for value in ("true", "yes", "on", "TRUE"):
        monkeypatch.setenv("FEATURE_X", value)
        assert is_enabled("x") is True


def test_flag_rejects_garbage_value(monkeypatch):
    monkeypatch.setenv("FEATURE_X", "maybe")
    assert is_enabled("x") is False
