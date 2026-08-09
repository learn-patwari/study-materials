from dataclasses import dataclass
from typing import Optional
from db import database as db


@dataclass
class PullRequest:
    id: Optional[int]
    repo_slug: str
    pr_id: int
    title: str
    author: str = ""
    source_branch: str = ""
    target_branch: str = ""
    pr_url: str = ""
    diff_text: str = ""
    status: str = "new"


def save(pr: PullRequest) -> int:
    existing = db.fetchone(
        "SELECT id FROM pull_requests WHERE repo_slug=? AND pr_id=?", (pr.repo_slug, pr.pr_id)
    )
    if existing:
        return existing["id"]
    cur = db.execute(
        "INSERT INTO pull_requests (repo_slug,pr_id,title,author,source_branch,target_branch,pr_url,diff_text,status) VALUES (?,?,?,?,?,?,?,?,?)",
        (pr.repo_slug, pr.pr_id, pr.title, pr.author, pr.source_branch, pr.target_branch, pr.pr_url, pr.diff_text, pr.status),
    )
    db.commit()
    return cur.lastrowid


def get_all() -> list[PullRequest]:
    rows = db.fetchall("SELECT * FROM pull_requests ORDER BY created_at DESC")
    return [_row(r) for r in rows]


def update_status(pr_db_id: int, status: str):
    db.execute("UPDATE pull_requests SET status=? WHERE id=?", (status, pr_db_id))
    db.commit()


def update_diff(pr_db_id: int, diff_text: str):
    db.execute("UPDATE pull_requests SET diff_text=? WHERE id=?", (diff_text, pr_db_id))
    db.commit()


def save_comments(pr_db_id: int, comments: list[dict]):
    db.execute("DELETE FROM pr_review_comments WHERE pr_id=?", (pr_db_id,))
    db.executemany(
        "INSERT INTO pr_review_comments (pr_id,file_path,line_num,comment) VALUES (?,?,?,?)",
        [(pr_db_id, c.get("file_path", ""), c.get("line_num", 0), c.get("comment", "")) for c in comments],
    )
    db.commit()


def get_comments(pr_db_id: int) -> list[dict]:
    rows = db.fetchall("SELECT * FROM pr_review_comments WHERE pr_id=?", (pr_db_id,))
    return [{"id": r["id"], "file_path": r["file_path"], "line_num": r["line_num"],
             "comment": r["comment"], "approved": r["approved"]} for r in rows]


def approve_comment(comment_id: int, approved: int):
    db.execute("UPDATE pr_review_comments SET approved=? WHERE id=?", (approved, comment_id))
    db.commit()


def mark_comment_posted(comment_id: int):
    db.execute("UPDATE pr_review_comments SET posted_at=datetime('now') WHERE id=?", (comment_id,))
    db.commit()


def _row(r) -> PullRequest:
    return PullRequest(
        id=r["id"], repo_slug=r["repo_slug"], pr_id=r["pr_id"], title=r["title"],
        author=r["author"] or "", source_branch=r["source_branch"] or "",
        target_branch=r["target_branch"] or "", pr_url=r["pr_url"] or "",
        diff_text=r["diff_text"] or "", status=r["status"],
    )
