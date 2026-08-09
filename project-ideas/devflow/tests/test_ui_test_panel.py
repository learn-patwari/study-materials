import pytest
from unittest.mock import patch
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt
from ui.test_panel import TestPanel
from models import ticket as ticket_model
from models import document as doc_model
from models.ticket import Ticket


@pytest.fixture(scope="session")
def qapp():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def ticket(isolated_db):
    ticket_model.save(Ticket(id=None, jira_key="TP-1", title="Test panel ticket"))
    return ticket_model.get_by_jira_key("TP-1")


def test_test_panel_renders(qapp, ticket):
    panel = TestPanel(ticket.id)
    panel.show()
    assert panel.isVisible()
    panel.close()


def test_test_panel_shows_file_count(qapp, ticket):
    doc_model.save_test_files(ticket.id, [
        {"filename": "test_a.py", "content": "def test_a(): pass"},
        {"filename": "test_b.py", "content": "def test_b(): pass"},
    ])
    panel = TestPanel(ticket.id)
    panel.load()
    assert "2" in panel._count_lbl.text()
    panel.close()


def test_test_panel_list_populated(qapp, ticket):
    doc_model.save_test_files(ticket.id, [
        {"filename": "test_x.py", "content": "x"},
        {"filename": "test_y.py", "content": "y"},
        {"filename": "test_z.py", "content": "z"},
    ])
    panel = TestPanel(ticket.id)
    panel.load()
    assert panel._list.count() == 3
    panel.close()


def test_test_panel_preview_on_select(qapp, ticket):
    doc_model.save_test_files(ticket.id, [
        {"filename": "test_preview.py", "content": "def test_foo(): assert True"},
    ])
    panel = TestPanel(ticket.id)
    panel.load()
    panel._list.setCurrentRow(0)
    item = panel._list.currentItem()
    panel._on_select(item)
    assert "test_foo" in panel._preview.toPlainText()
    panel.close()


def test_test_panel_coverage_display(qapp, ticket):
    panel = TestPanel(ticket.id)
    panel._on_coverage_done({"passed": 10, "failed": 2, "coverage_pct": 78.0})
    text = panel._cov_lbl.text()
    assert "10" in text
    assert "2" in text
    assert "78" in text
    panel.close()


def test_test_panel_coverage_error_display(qapp, ticket):
    panel = TestPanel(ticket.id)
    panel._on_coverage_done({"error": "Command not found"})
    assert "Error" in panel._cov_lbl.text()
    panel.close()


def test_test_panel_empty_state(qapp, ticket):
    panel = TestPanel(ticket.id)
    panel.load()
    assert "0" in panel._count_lbl.text()
    assert panel._list.count() == 0
    panel.close()
