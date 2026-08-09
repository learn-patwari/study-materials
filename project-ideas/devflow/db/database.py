import sqlite3
import os
from pathlib import Path

_DB_PATH = Path.home() / ".devflow" / "devflow.db"
_conn: sqlite3.Connection | None = None


def get_connection() -> sqlite3.Connection:
    global _conn
    if _conn is None:
        p = Path(_DB_PATH)
        p.parent.mkdir(parents=True, exist_ok=True)
        _conn = sqlite3.connect(str(p), check_same_thread=False)
        _conn.row_factory = sqlite3.Row
        _conn.execute("PRAGMA foreign_keys = ON")
        _init_schema()
    return _conn


def _init_schema():
    schema_path = Path(__file__).parent / "schema.sql"
    sql = schema_path.read_text()
    _conn.executescript(sql)
    _conn.commit()


def execute(sql: str, params: tuple = ()) -> sqlite3.Cursor:
    return get_connection().execute(sql, params)


def executemany(sql: str, params_seq) -> sqlite3.Cursor:
    return get_connection().executemany(sql, params_seq)


def commit():
    get_connection().commit()


def fetchone(sql: str, params: tuple = ()) -> sqlite3.Row | None:
    return execute(sql, params).fetchone()


def fetchall(sql: str, params: tuple = ()) -> list[sqlite3.Row]:
    return execute(sql, params).fetchall()


def get_setting(key: str, default: str = "") -> str:
    row = fetchone("SELECT value FROM settings WHERE key = ?", (key,))
    return row["value"] if row else default


def set_setting(key: str, value: str):
    execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (key, value))
    commit()


def get_all_settings() -> dict:
    rows = fetchall("SELECT key, value FROM settings")
    return {r["key"]: r["value"] for r in rows}
