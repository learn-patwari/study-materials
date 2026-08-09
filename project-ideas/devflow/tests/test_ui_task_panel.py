import pytest
from unittest.mock import patch
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt
from ui.task_panel import TaskPanel
from models import ticket as ticket_model
from models import task as task_model
from models.ticket import Ticket
from models.task import Task


@pytest.fixture(scope="session")
def qapp():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def ticket(isolated_db):
    ticket_model.save(Ticket(id=None, jira_key="UI-1", title="UI test ticket"))
    return ticket_model.get_by_jira_key("UI-1")


def test_task_panel_renders(qapp, ticket):
    panel = TaskPanel(ticket.id)
    panel.show()
    assert panel.isVisible()
    panel.close()


def test_task_panel_loads_tasks(qapp, ticket):
    task_model.save(Task(id=None, ticket_id=ticket.id, title="Write unit tests", estimated_hrs=4.0))
    task_model.save(Task(id=None, ticket_id=ticket.id, title="Code review", estimated_hrs=2.0))
    panel = TaskPanel(ticket.id)
    panel.load()
    assert panel._table.rowCount() == 2
    panel.close()


def test_task_panel_add_row(qapp, ticket):
    panel = TaskPanel(ticket.id)
    panel.load()
    initial_rows = panel._table.rowCount()
    panel._add_row()
    assert panel._table.rowCount() == initial_rows + 1
    panel.close()


def test_task_panel_total_estimate(qapp, ticket):
    task_model.save(Task(id=None, ticket_id=ticket.id, title="A", estimated_hrs=3.0))
    task_model.save(Task(id=None, ticket_id=ticket.id, title="B", estimated_hrs=5.5))
    panel = TaskPanel(ticket.id)
    panel.load()
    assert "8.5" in panel._total_lbl.text()
    panel.close()


def test_task_panel_delete_row(qapp, ticket):
    task_model.save(Task(id=None, ticket_id=ticket.id, title="DeleteMe", estimated_hrs=1.0))
    panel = TaskPanel(ticket.id)
    panel.load()
    assert panel._table.rowCount() >= 1
    panel._table.selectRow(0)
    panel._delete_selected()
    # Row count should decrease
    panel.close()


def test_task_panel_save_persists(qapp, ticket):
    panel = TaskPanel(ticket.id)
    panel.load()
    panel._add_row()
    # Set title in the new row
    panel._table.item(panel._table.rowCount() - 1, 0).setText("Saved Task")
    panel._save_all()
    tasks = task_model.get_by_ticket(ticket.id)
    titles = [t.title for t in tasks]
    assert "Saved Task" in titles
    panel.close()
