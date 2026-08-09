from dataclasses import dataclass
from typing import Optional
from db import database as db


@dataclass
class Document:
    id: Optional[int]
    ticket_id: int
    doc_type: str
    content: str = ""
    approved_at: str = ""
    posted_at: str = ""


def save(d: Document) -> int:
    existing = db.fetchone(
        "SELECT id FROM documents WHERE ticket_id=? AND doc_type=?", (d.ticket_id, d.doc_type)
    )
    if existing:
        db.execute(
            "UPDATE documents SET content=?,approved_at=?,posted_at=? WHERE id=?",
            (d.content, d.approved_at, d.posted_at, existing["id"]),
        )
        db.commit()
        return existing["id"]
    cur = db.execute(
        "INSERT INTO documents (ticket_id,doc_type,content,approved_at,posted_at) VALUES (?,?,?,?,?)",
        (d.ticket_id, d.doc_type, d.content, d.approved_at, d.posted_at),
    )
    db.commit()
    return cur.lastrowid


def get(ticket_id: int, doc_type: str) -> Optional[Document]:
    row = db.fetchone(
        "SELECT * FROM documents WHERE ticket_id=? AND doc_type=?", (ticket_id, doc_type)
    )
    if not row:
        return None
    return Document(id=row["id"], ticket_id=row["ticket_id"], doc_type=row["doc_type"],
                    content=row["content"] or "", approved_at=row["approved_at"] or "",
                    posted_at=row["posted_at"] or "")


def save_test_files(ticket_id: int, files: list[dict]):
    db.execute("DELETE FROM test_files WHERE ticket_id=?", (ticket_id,))
    db.executemany(
        "INSERT INTO test_files (ticket_id,filename,content) VALUES (?,?,?)",
        [(ticket_id, f["filename"], f["content"]) for f in files],
    )
    db.commit()


def get_test_files(ticket_id: int) -> list[dict]:
    rows = db.fetchall("SELECT * FROM test_files WHERE ticket_id=?", (ticket_id,))
    return [{"id": r["id"], "filename": r["filename"], "content": r["content"] or "",
             "coverage_pct": r["coverage_pct"]} for r in rows]


def save_diagram(ticket_id: int, mermaid_src: str, drawio_xml: str, confluence_url: str = ""):
    existing = db.fetchone("SELECT id FROM diagrams WHERE ticket_id=?", (ticket_id,))
    if existing:
        db.execute(
            "UPDATE diagrams SET mermaid_src=?,drawio_xml=?,confluence_page_url=? WHERE ticket_id=?",
            (mermaid_src, drawio_xml, confluence_url, ticket_id),
        )
    else:
        db.execute(
            "INSERT INTO diagrams (ticket_id,mermaid_src,drawio_xml,confluence_page_url) VALUES (?,?,?,?)",
            (ticket_id, mermaid_src, drawio_xml, confluence_url),
        )
    db.commit()


def get_diagram(ticket_id: int) -> Optional[dict]:
    row = db.fetchone("SELECT * FROM diagrams WHERE ticket_id=?", (ticket_id,))
    if not row:
        return None
    return {"mermaid_src": row["mermaid_src"] or "", "drawio_xml": row["drawio_xml"] or "",
            "confluence_page_url": row["confluence_page_url"] or ""}
