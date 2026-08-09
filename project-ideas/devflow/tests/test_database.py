import pytest
import db.database as database


def test_schema_initializes():
    conn = database.get_connection()
    tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
    assert "settings" in tables
    assert "tickets" in tables
    assert "tasks" in tables
    assert "documents" in tables


def test_get_set_setting():
    database.set_setting("test_key", "hello")
    assert database.get_setting("test_key") == "hello"


def test_get_setting_default():
    assert database.get_setting("nonexistent_key", "default_val") == "default_val"


def test_get_setting_missing_returns_empty():
    assert database.get_setting("totally_missing") == ""


def test_set_setting_overwrite():
    database.set_setting("key1", "first")
    database.set_setting("key1", "second")
    assert database.get_setting("key1") == "second"


def test_get_all_settings():
    database.set_setting("a", "1")
    database.set_setting("b", "2")
    settings = database.get_all_settings()
    assert settings["a"] == "1"
    assert settings["b"] == "2"


def test_fetchone_returns_none_for_missing():
    result = database.fetchone("SELECT * FROM settings WHERE key = ?", ("__missing__",))
    assert result is None


def test_fetchall_returns_list():
    database.set_setting("x", "1")
    database.set_setting("y", "2")
    rows = database.fetchall("SELECT * FROM settings")
    assert len(rows) >= 2
