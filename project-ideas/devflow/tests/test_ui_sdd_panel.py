import pytest
from PyQt6.QtWidgets import QApplication
from ui.sdd_panel import SDDPanel
from models import ticket as ticket_model
from models import document as doc_model
from models.ticket import Ticket
from models.document import Document


@pytest.fixture(scope="session")
def qapp():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def ticket(isolated_db):
    ticket_model.save(Ticket(id=None, jira_key="SDD-1", title="SDD test"))
    return ticket_model.get_by_jira_key("SDD-1")


def test_sdd_panel_renders(qapp, ticket):
    panel = SDDPanel(ticket.id)
    panel.show()
    assert panel.isVisible()
    panel.close()


def test_sdd_panel_loads_content(qapp, ticket):
    doc_model.save(Document(id=None, ticket_id=ticket.id, doc_type="sdd", content="## Architecture\nSome design doc."))
    panel = SDDPanel(ticket.id)
    panel.load()
    assert "Architecture" in panel._editor.toPlainText()
    panel.close()


def test_sdd_panel_empty_when_no_doc(qapp, ticket):
    panel = SDDPanel(ticket.id)
    panel.load()
    assert panel._editor.toPlainText() == ""
    panel.close()


def test_sdd_panel_save(qapp, ticket):
    panel = SDDPanel(ticket.id)
    panel._editor.setPlainText("New SDD content")
    panel._save()
    doc = doc_model.get(ticket.id, "sdd")
    assert doc is not None
    assert doc.content == "New SDD content"
    panel.close()


def test_sdd_panel_overwrite_on_save(qapp, ticket):
    doc_model.save(Document(id=None, ticket_id=ticket.id, doc_type="sdd", content="old"))
    panel = SDDPanel(ticket.id)
    panel.load()
    panel._editor.setPlainText("updated content")
    panel._save()
    doc = doc_model.get(ticket.id, "sdd")
    assert doc.content == "updated content"
    panel.close()
