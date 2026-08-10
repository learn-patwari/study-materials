import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Optional


class SQLiteMemory:
    def __init__(self, db_path: str = "~/.pattu/memory.db"):
        path = Path(db_path).expanduser()
        path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(path), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._init_schema()

    def _init_schema(self) -> None:
        self._conn.executescript("""
            CREATE TABLE IF NOT EXISTS messages (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                session    TEXT    NOT NULL,
                role       TEXT    NOT NULL,
                content    TEXT    NOT NULL,
                agent      TEXT    DEFAULT 'pattu',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS memory (
                key        TEXT PRIMARY KEY,
                value      TEXT NOT NULL,
                agent      TEXT NOT NULL,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS agent_runs (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                agent_name TEXT    NOT NULL,
                status     TEXT    NOT NULL,
                summary    TEXT,
                started_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                ended_at   DATETIME
            );
        """)
        self._conn.commit()

    # ── Conversation history ──────────────────────────────────────────────────

    def save_message(self, session: str, role: str, content: str, agent: str = "pattu") -> None:
        if not isinstance(content, str):
            content = json.dumps(content)
        self._conn.execute(
            "INSERT INTO messages (session, role, content, agent) VALUES (?,?,?,?)",
            (session, role, content, agent),
        )
        self._conn.commit()

    def get_history(self, session: str, limit: int = 50) -> list[dict]:
        rows = self._conn.execute(
            "SELECT role, content FROM messages WHERE session=? ORDER BY id DESC LIMIT ?",
            (session, limit),
        ).fetchall()
        return [{"role": r["role"], "content": r["content"]} for r in reversed(rows)]

    # ── Key-value store ───────────────────────────────────────────────────────

    def set(self, key: str, value: Any, agent: str) -> None:
        self._conn.execute(
            "INSERT OR REPLACE INTO memory (key, value, agent, updated_at) VALUES (?,?,?,?)",
            (key, json.dumps(value), agent, datetime.utcnow().isoformat()),
        )
        self._conn.commit()

    def get(self, key: str, default: Any = None) -> Any:
        row = self._conn.execute(
            "SELECT value FROM memory WHERE key=?", (key,)
        ).fetchone()
        if row is None:
            return default
        return json.loads(row["value"])

    def get_updated_at(self, key: str) -> Optional[datetime]:
        row = self._conn.execute(
            "SELECT updated_at FROM memory WHERE key=?", (key,)
        ).fetchone()
        if row is None:
            return None
        return datetime.fromisoformat(row["updated_at"])

    def get_all_by_agent(self, agent: str) -> dict:
        rows = self._conn.execute(
            "SELECT key, value FROM memory WHERE agent=?", (agent,)
        ).fetchall()
        return {r["key"]: json.loads(r["value"]) for r in rows}

    # ── Agent run log ─────────────────────────────────────────────────────────

    def start_run(self, agent_name: str) -> int:
        cur = self._conn.execute(
            "INSERT INTO agent_runs (agent_name, status) VALUES (?,?)",
            (agent_name, "running"),
        )
        self._conn.commit()
        return cur.lastrowid

    def end_run(self, run_id: int, status: str, summary: str = "") -> None:
        self._conn.execute(
            "UPDATE agent_runs SET status=?, summary=?, ended_at=? WHERE id=?",
            (status, summary, datetime.utcnow().isoformat(), run_id),
        )
        self._conn.commit()

    def recent_runs(self, limit: int = 10) -> list[dict]:
        rows = self._conn.execute(
            "SELECT * FROM agent_runs ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()
        return [dict(r) for r in rows]

    def close(self) -> None:
        self._conn.close()
