import pytest
from models import ticket as ticket_model
from models import task as task_model
from models import document as doc_model
from models import sprint as sprint_model
from models.ticket import Ticket
from models.task import Task
from models.document import Document
from models.sprint import Sprint


# ── Ticket model ─────────────────────────────────────────────────────

def test_ticket_save_and_get():
    t = Ticket(id=None, jira_key="TEST-1", title="Test ticket", srs_content="Some SRS")
    ticket_model.save(t)
    fetched = ticket_model.get_by_jira_key("TEST-1")
    assert fetched is not None
    assert fetched.title == "Test ticket"
    assert fetched.status == "draft"


def test_ticket_get_by_id():
    t = Ticket(id=None, jira_key="TEST-2", title="Another")
    ticket_model.save(t)
    fetched_by_key = ticket_model.get_by_jira_key("TEST-2")
    fetched_by_id = ticket_model.get_by_id(fetched_by_key.id)
    assert fetched_by_id.jira_key == "TEST-2"


def test_ticket_get_all():
    ticket_model.save(Ticket(id=None, jira_key="T-10", title="A"))
    ticket_model.save(Ticket(id=None, jira_key="T-11", title="B"))
    all_tickets = ticket_model.get_all()
    keys = {t.jira_key for t in all_tickets}
    assert "T-10" in keys
    assert "T-11" in keys


def test_ticket_update_status():
    ticket_model.save(Ticket(id=None, jira_key="T-20", title="Status test"))
    t = ticket_model.get_by_jira_key("T-20")
    ticket_model.update_status(t.id, "ready")
    updated = ticket_model.get_by_id(t.id)
    assert updated.status == "ready"


def test_ticket_update_by_id():
    ticket_model.save(Ticket(id=None, jira_key="T-30", title="First"))
    t = ticket_model.get_by_jira_key("T-30")
    updated = Ticket(id=t.id, jira_key="T-30", title="Updated")
    ticket_model.save(updated)
    result = ticket_model.get_by_jira_key("T-30")
    assert result.title == "Updated"
    all_t = [x for x in ticket_model.get_all() if x.jira_key == "T-30"]
    assert len(all_t) == 1


# ── Task model ────────────────────────────────────────────────────────

def _make_ticket(key="TK-1"):
    ticket_model.save(Ticket(id=None, jira_key=key, title="parent"))
    return ticket_model.get_by_jira_key(key)


def test_task_save_and_get():
    parent = _make_ticket("TK-1")
    task = Task(id=None, ticket_id=parent.id, title="Write tests", estimated_hrs=3.0)
    task_model.save(task)
    tasks = task_model.get_by_ticket(parent.id)
    assert len(tasks) == 1
    assert tasks[0].title == "Write tests"
    assert tasks[0].estimated_hrs == 3.0


def test_task_default_status_is_todo():
    parent = _make_ticket("TK-2")
    task_model.save(Task(id=None, ticket_id=parent.id, title="T"))
    tasks = task_model.get_by_ticket(parent.id)
    assert tasks[0].status == "todo"


def test_task_delete():
    parent = _make_ticket("TK-3")
    task_model.save(Task(id=None, ticket_id=parent.id, title="DeleteMe"))
    tasks = task_model.get_by_ticket(parent.id)
    tid = tasks[0].id
    task_model.delete(tid)
    assert task_model.get_by_ticket(parent.id) == []


def test_task_multiple_per_ticket():
    parent = _make_ticket("TK-4")
    task_model.save(Task(id=None, ticket_id=parent.id, title="A"))
    task_model.save(Task(id=None, ticket_id=parent.id, title="B"))
    task_model.save(Task(id=None, ticket_id=parent.id, title="C"))
    assert len(task_model.get_by_ticket(parent.id)) == 3


# ── Document model ────────────────────────────────────────────────────

def test_document_save_and_get():
    parent = _make_ticket("DK-1")
    doc = Document(id=None, ticket_id=parent.id, doc_type="sdd", content="Design doc content")
    doc_model.save(doc)
    fetched = doc_model.get(parent.id, "sdd")
    assert fetched is not None
    assert fetched.content == "Design doc content"


def test_document_upsert_same_type():
    parent = _make_ticket("DK-2")
    doc_model.save(Document(id=None, ticket_id=parent.id, doc_type="sdd", content="v1"))
    doc_model.save(Document(id=None, ticket_id=parent.id, doc_type="sdd", content="v2"))
    fetched = doc_model.get(parent.id, "sdd")
    assert fetched.content == "v2"


def test_document_get_returns_none_for_missing():
    parent = _make_ticket("DK-3")
    assert doc_model.get(parent.id, "formatted_desc") is None


def test_test_files_save_and_get():
    parent = _make_ticket("DK-4")
    files = [
        {"filename": "test_a.py", "content": "def test_a(): pass"},
        {"filename": "test_b.py", "content": "def test_b(): pass"},
    ]
    doc_model.save_test_files(parent.id, files)
    fetched = doc_model.get_test_files(parent.id)
    assert len(fetched) == 2
    names = {f["filename"] for f in fetched}
    assert "test_a.py" in names
    assert "test_b.py" in names


def test_diagram_save_and_get():
    parent = _make_ticket("DK-5")
    doc_model.save_diagram(parent.id, "graph LR; A-->B", "<xml/>")
    diagram = doc_model.get_diagram(parent.id)
    assert diagram["mermaid_src"] == "graph LR; A-->B"
    assert diagram["drawio_xml"] == "<xml/>"


def test_diagram_confluence_url():
    parent = _make_ticket("DK-6")
    doc_model.save_diagram(parent.id, "graph LR; A-->B", "<xml/>", "https://confluence/page/1")
    diagram = doc_model.get_diagram(parent.id)
    assert diagram["confluence_page_url"] == "https://confluence/page/1"


# ── Sprint model ──────────────────────────────────────────────────────

def test_sprint_save_and_get_latest():
    s = Sprint(id=None, jira_sprint_id="SP-1", name="Sprint 1",
               start_date="2026-08-01", end_date="2026-08-14", dev_days=8, test_days=2)
    sprint_model.save(s)
    latest = sprint_model.get_latest()
    assert latest is not None
    assert latest.name == "Sprint 1"
    assert latest.dev_days == 8


def test_sprint_voc_link():
    s = Sprint(id=None, jira_sprint_id="SP-2", name="Sprint 2",
               start_date="2026-08-01", end_date="2026-08-14", dev_days=8, test_days=2)
    sprint_model.save(s)
    latest = sprint_model.get_latest()
    sprint_model.save_voc_link(latest.id, "VOC-10", task_id=None, notes="perf issue", hrs=0.0)
    links = sprint_model.get_voc_links(latest.id)
    assert len(links) == 1
    assert links[0]["voc_jira_key"] == "VOC-10"
    assert links[0]["notes"] == "perf issue"
