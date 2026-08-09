import sys
import os
import tempfile
import pytest

# Ensure project root is on path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@pytest.fixture
def tmp_dir(tmp_path):
    return tmp_path


@pytest.fixture(autouse=True)
def isolated_db(monkeypatch, tmp_path):
    """Redirect the DB to a temp file for every test."""
    db_path = str(tmp_path / "test.db")
    import db.database as database
    monkeypatch.setattr(database, "_DB_PATH", db_path)
    monkeypatch.setattr(database, "_conn", None)
    yield
    if database._conn:
        database._conn.close()
        database._conn = None
