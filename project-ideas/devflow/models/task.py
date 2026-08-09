from dataclasses import dataclass
from typing import Optional
from db import database as db


@dataclass
class Task:
    id: Optional[int]
    ticket_id: int
    title: str
    jira_task_key: str = ""
    assignee: str = ""
    status: str = "todo"
    estimated_hrs: float = 0.0
    task_type: str = "dev"
    start_date: str = ""
    end_date: str = ""


def save(t: Task) -> int:
    if t.id:
        db.execute(
            "UPDATE tasks SET title=?,jira_task_key=?,assignee=?,status=?,estimated_hrs=?,task_type=?,start_date=?,end_date=? WHERE id=?",
            (t.title, t.jira_task_key, t.assignee, t.status, t.estimated_hrs, t.task_type, t.start_date, t.end_date, t.id),
        )
        db.commit()
        return t.id
    cur = db.execute(
        "INSERT INTO tasks (ticket_id,title,jira_task_key,assignee,status,estimated_hrs,task_type,start_date,end_date) VALUES (?,?,?,?,?,?,?,?,?)",
        (t.ticket_id, t.title, t.jira_task_key, t.assignee, t.status, t.estimated_hrs, t.task_type, t.start_date, t.end_date),
    )
    db.commit()
    return cur.lastrowid


def get_by_ticket(ticket_id: int) -> list[Task]:
    rows = db.fetchall("SELECT * FROM tasks WHERE ticket_id=? ORDER BY id", (ticket_id,))
    return [_row(r) for r in rows]


def get_overdue() -> list[Task]:
    rows = db.fetchall(
        "SELECT * FROM tasks WHERE status != 'done' AND end_date != '' AND end_date < date('now')"
    )
    return [_row(r) for r in rows]


def get_due_today() -> list[Task]:
    rows = db.fetchall(
        "SELECT * FROM tasks WHERE status != 'done' AND end_date = date('now')"
    )
    return [_row(r) for r in rows]


def update_status(task_id: int, status: str):
    db.execute("UPDATE tasks SET status=? WHERE id=?", (status, task_id))
    db.commit()


def delete(task_id: int):
    db.execute("DELETE FROM tasks WHERE id=?", (task_id,))
    db.commit()


def _row(r) -> Task:
    return Task(
        id=r["id"], ticket_id=r["ticket_id"], title=r["title"],
        jira_task_key=r["jira_task_key"] or "", assignee=r["assignee"] or "",
        status=r["status"], estimated_hrs=r["estimated_hrs"] or 0.0,
        task_type=r["task_type"] or "dev",
        start_date=r["start_date"] or "", end_date=r["end_date"] or "",
    )
