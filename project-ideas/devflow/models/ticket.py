from dataclasses import dataclass, field
from typing import Optional
from db import database as db


@dataclass
class Ticket:
    id: Optional[int]
    jira_key: str
    title: str
    srs_content: str = ""
    description: str = ""
    status: str = "draft"
    code_source: str = ""
    source_type: str = "local"
    created_at: str = ""


def save(t: Ticket) -> int:
    if t.id:
        db.execute(
            "UPDATE tickets SET jira_key=?,title=?,srs_content=?,description=?,status=?,code_source=?,source_type=? WHERE id=?",
            (t.jira_key, t.title, t.srs_content, t.description, t.status, t.code_source, t.source_type, t.id),
        )
        db.commit()
        return t.id
    cur = db.execute(
        "INSERT INTO tickets (jira_key,title,srs_content,description,status,code_source,source_type) VALUES (?,?,?,?,?,?,?)",
        (t.jira_key, t.title, t.srs_content, t.description, t.status, t.code_source, t.source_type),
    )
    db.commit()
    return cur.lastrowid


def get_all() -> list[Ticket]:
    rows = db.fetchall("SELECT * FROM tickets ORDER BY created_at DESC")
    return [_row_to_ticket(r) for r in rows]


def get_by_id(ticket_id: int) -> Optional[Ticket]:
    row = db.fetchone("SELECT * FROM tickets WHERE id=?", (ticket_id,))
    return _row_to_ticket(row) if row else None


def get_by_jira_key(key: str) -> Optional[Ticket]:
    row = db.fetchone("SELECT * FROM tickets WHERE jira_key=?", (key,))
    return _row_to_ticket(row) if row else None


def update_status(ticket_id: int, status: str):
    db.execute("UPDATE tickets SET status=? WHERE id=?", (status, ticket_id))
    db.commit()


def _row_to_ticket(r) -> Ticket:
    return Ticket(
        id=r["id"], jira_key=r["jira_key"], title=r["title"],
        srs_content=r["srs_content"] or "", description=r["description"] or "",
        status=r["status"], code_source=r["code_source"] or "",
        source_type=r["source_type"] or "local", created_at=r["created_at"] or "",
    )
