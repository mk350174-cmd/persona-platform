import sys
import os
import tempfile

# Make persona_math importable — it lives in the parent repo directory
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# Use an isolated temp file so tests never touch hpep_studio.db
_tmp_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
_tmp_db.close()
os.environ["STUDIO_DATABASE_URL"] = f"sqlite:///{_tmp_db.name}"

import pytest

@pytest.fixture(autouse=True, scope="session")
def disable_rate_limiting():
    try:
        from api.main import limiter
        limiter.enabled = False
        yield
        limiter.enabled = True
    except Exception:
        yield

def pytest_sessionfinish(session, exitstatus):
    try:
        os.unlink(_tmp_db.name)
    except OSError:
        pass
