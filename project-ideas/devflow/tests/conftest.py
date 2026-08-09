import sys
import os
import tempfile
import pytest

# Ensure project root is on path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Headless Qt — must be set before any Qt import
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault(
    "QTWEBENGINE_CHROMIUM_FLAGS",
    "--no-sandbox --disable-gpu --in-process-gpu --disable-gpu-compositing "
    "--disable-gl-drawing-for-tests --disable-gpu-vsync"
)
os.environ.setdefault("QTWEBENGINE_DISABLE_SANDBOX", "1")

try:
    from PyQt6.QtCore import Qt
    from PyQt6.QtWidgets import QApplication
    QApplication.setAttribute(Qt.ApplicationAttribute.AA_ShareOpenGLContexts)
except Exception:
    pass


@pytest.fixture
def tmp_dir(tmp_path):
    return tmp_path


@pytest.fixture(autouse=True)
def isolated_db(request, monkeypatch, tmp_path):
    """Redirect the DB to a temp file for every test (skipped for ui tests)."""
    if "test_ui" in request.fspath.basename:
        yield
        return
    db_path = str(tmp_path / "test.db")
    import db.database as database
    monkeypatch.setattr(database, "_DB_PATH", db_path)
    monkeypatch.setattr(database, "_conn", None)
    yield
    if database._conn:
        database._conn.close()
        database._conn = None
