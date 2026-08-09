from dataclasses import dataclass
from typing import Optional
from db import database as db


@dataclass
class Sprint:
    id: Optional[int]
    jira_sprint_id: str
    name: str
    start_date: str = ""
    end_date: str = ""
    dev_days: int = 8
    test_days: int = 2


def save(s: Sprint) -> int:
    existing = db.fetchone("SELECT id FROM sprints WHERE jira_sprint_id=?", (s.jira_sprint_id,))
    if existing:
        db.execute(
            "UPDATE sprints SET name=?,start_date=?,end_date=?,dev_days=?,test_days=? WHERE id=?",
            (s.name, s.start_date, s.end_date, s.dev_days, s.test_days, existing["id"]),
        )
        db.commit()
        return existing["id"]
    cur = db.execute(
        "INSERT INTO sprints (jira_sprint_id,name,start_date,end_date,dev_days,test_days) VALUES (?,?,?,?,?,?)",
        (s.jira_sprint_id, s.name, s.start_date, s.end_date, s.dev_days, s.test_days),
    )
    db.commit()
    return cur.lastrowid


def get_latest() -> Optional[Sprint]:
    row = db.fetchone("SELECT * FROM sprints ORDER BY fetched_at DESC LIMIT 1")
    return _row(row) if row else None


def _row(r) -> Sprint:
    return Sprint(id=r["id"], jira_sprint_id=r["jira_sprint_id"], name=r["name"],
                  start_date=r["start_date"] or "", end_date=r["end_date"] or "",
                  dev_days=r["dev_days"] or 8, test_days=r["test_days"] or 2)


def save_voc_link(sprint_id: int, voc_key: str, task_id: Optional[int], notes: str, hrs: float):
    db.execute(
        "INSERT INTO voc_links (sprint_id,voc_jira_key,linked_task_id,notes,logged_hrs) VALUES (?,?,?,?,?)",
        (sprint_id, voc_key, task_id, notes, hrs),
    )
    db.commit()


def get_voc_links(sprint_id: int) -> list[dict]:
    rows = db.fetchall("SELECT * FROM voc_links WHERE sprint_id=?", (sprint_id,))
    return [{"id": r["id"], "voc_jira_key": r["voc_jira_key"],
             "linked_task_id": r["linked_task_id"], "notes": r["notes"] or "",
             "logged_hrs": r["logged_hrs"] or 0.0} for r in rows]
