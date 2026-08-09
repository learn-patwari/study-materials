from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QTreeWidget, QTreeWidgetItem, QListWidget, QListWidgetItem,
    QSplitter, QInputDialog, QMessageBox
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from models import sprint as sprint_model
from models import task as task_model
from models import ticket as ticket_model
from services import jira_client, ai_service
from ui.timeline_view import TimelineView
from db import database as db
import datetime


class _SprintFetcher(QThread):
    done = pyqtSignal(object)
    error = pyqtSignal(str)

    def run(self):
        try:
            self.done.emit(jira_client.fetch_active_sprint_tasks())
        except Exception as e:
            self.error.emit(str(e))


class _IntegTestThread(QThread):
    done = pyqtSignal(list)
    error = pyqtSignal(str)

    def __init__(self, tasks):
        super().__init__()
        self._tasks = tasks

    def run(self):
        try:
            result = ai_service.generate_integration_tests(self._tasks)
            self.done.emit(result)
        except Exception as e:
            self.error.emit(str(e))


def _schedule_tasks(tasks, sprint_start: str, dev_days: int):
    """Assign sequential start/end dates to tasks within dev window."""
    try:
        base = datetime.date.fromisoformat(sprint_start[:10])
    except Exception:
        base = datetime.date.today()

    day_cursor = 0
    for t in tasks:
        dur_days = max(1, round((t.estimated_hrs or 4) / 8))
        t.start_date = (base + datetime.timedelta(days=day_cursor)).isoformat()
        t.end_date = (base + datetime.timedelta(days=min(day_cursor + dur_days - 1, dev_days - 1))).isoformat()
        day_cursor = min(day_cursor + dur_days, dev_days - 1)


class SprintPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._sprint_data = None
        self._tasks = []        # flat list of all tasks (Task objects)
        self._groups = []       # list of {ticket, tasks} dicts for grouped view
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        top = QHBoxLayout()
        self._sprint_lbl = QLabel("Sprint: (not loaded)")
        self._sprint_lbl.setStyleSheet("font-weight: bold; font-size: 14px;")
        top.addWidget(self._sprint_lbl)
        top.addStretch()
        load_btn = QPushButton("🔄 Load Sprint")
        load_btn.clicked.connect(self._load_sprint)
        integ_btn = QPushButton("⚡ Gen Integration Tests")
        integ_btn.setObjectName("secondary")
        integ_btn.clicked.connect(self._gen_integration_tests)
        top.addWidget(load_btn)
        top.addWidget(integ_btn)
        layout.addLayout(top)

        self._status_lbl = QLabel("")
        self._status_lbl.setStyleSheet("color: #8a9bb0;")
        layout.addWidget(self._status_lbl)

        splitter = QSplitter(Qt.Orientation.Horizontal)

        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(4)

        # SRS tickets + sub-tasks tree
        srs_lbl = QLabel("SRS Tasks")
        srs_lbl.setStyleSheet("font-weight:bold; color:#8a9bb0; padding:4px 0;")
        left_layout.addWidget(srs_lbl)

        self._tree = QTreeWidget()
        self._tree.setHeaderLabels(["Task", "Est", "Status"])
        self._tree.setColumnWidth(0, 200)
        self._tree.setColumnWidth(1, 40)
        self._tree.setColumnWidth(2, 70)
        self._tree.setAlternatingRowColors(True)
        left_layout.addWidget(self._tree)

        # Integration tests
        integ_lbl = QLabel("Integration Tests")
        integ_lbl.setStyleSheet("font-weight:bold; color:#8a9bb0; padding:4px 0;")
        left_layout.addWidget(integ_lbl)
        self._integ_list = QListWidget()
        self._integ_list.setMaximumHeight(120)
        left_layout.addWidget(self._integ_list)

        # VOC tickets
        voc_lbl = QLabel("VOC Tickets")
        voc_lbl.setStyleSheet("font-weight:bold; color:#8a9bb0; padding:4px 0;")
        left_layout.addWidget(voc_lbl)
        self._voc_list = QListWidget()
        self._voc_list.setMaximumHeight(100)
        left_layout.addWidget(self._voc_list)

        voc_btn = QPushButton("+ Link VOC Ticket")
        voc_btn.setObjectName("secondary")
        voc_btn.clicked.connect(self._link_voc)
        left_layout.addWidget(voc_btn)

        left.setMinimumWidth(320)
        splitter.addWidget(left)

        self._timeline = TimelineView()
        splitter.addWidget(self._timeline)
        splitter.setSizes([340, 680])
        layout.addWidget(splitter)

    def showEvent(self, event):
        super().showEvent(event)
        sprint = sprint_model.get_latest()
        if sprint:
            self._populate_sprint(sprint)

    def _load_sprint(self):
        self._status_lbl.setText("Loading sprint from Jira...")
        self._fetcher = _SprintFetcher()
        self._fetcher.done.connect(self._on_sprint_loaded)
        self._fetcher.error.connect(lambda e: self._status_lbl.setText(f"Error: {e}"))
        self._fetcher.start()

    def _on_sprint_loaded(self, data):
        if not data:
            self._status_lbl.setText("No active sprint found.")
            return
        sprint_model.save(sprint_model.Sprint(
            id=None,
            jira_sprint_id=str(data.get("id", "")),
            name=data.get("name", ""),
            start_date=data.get("startDate", ""),
            end_date=data.get("endDate", ""),
            dev_days=int(db.get_setting("sprint_dev_days", "8")),
            test_days=int(db.get_setting("sprint_test_days", "2")),
        ))
        sprint = sprint_model.get_latest()
        self._populate_sprint(sprint)

    def _populate_sprint(self, sprint):
        if not sprint:
            return
        self._sprint_data = sprint
        self._sprint_lbl.setText(
            f"Sprint: {sprint.name}  ({sprint.dev_days} dev days / {sprint.test_days} test days)"
        )
        self._status_lbl.setText("")

        # Load all local SRS tickets and their tasks
        all_tickets = ticket_model.get_all()
        self._groups = []
        self._tasks = []

        for ticket in all_tickets:
            ticket_tasks = task_model.get_by_ticket(ticket.id)
            dev_tasks = [t for t in ticket_tasks if t.task_type != "integration_test"]
            if dev_tasks:
                _schedule_tasks(dev_tasks, sprint.start_date or "", sprint.dev_days or 8)
                self._groups.append({"ticket": ticket, "tasks": dev_tasks})
                self._tasks.extend(dev_tasks)

        # Add integration test tasks from DB (no ticket parent)
        integ_tasks = [t for t in (task_model.get_by_ticket(None) if False else []) if t.task_type == "integration_test"]
        self._tasks.extend(integ_tasks)

        self._refresh_tree()

        voc_links = sprint_model.get_voc_links(sprint.id) if sprint.id else []
        self._voc_list.clear()
        for v in voc_links:
            item = QListWidgetItem(f"🔴 {v['voc_jira_key']}  → Logged: {v.get('logged_hrs', 0)}h  {v.get('notes', '')}")
            self._voc_list.addItem(item)

        self._timeline.render_gantt(sprint, self._groups)

    def _refresh_tree(self):
        self._tree.clear()
        status_icon = {"todo": "🔵", "in_progress": "🟡", "done": "🟢"}
        total_hrs = 0.0

        for group in self._groups:
            ticket = group["ticket"]
            tasks = group["tasks"]
            grp_hrs = sum(t.estimated_hrs or 0 for t in tasks)
            total_hrs += grp_hrs

            parent_item = QTreeWidgetItem([
                f"{ticket.jira_key} — {ticket.title[:45]}",
                f"{grp_hrs:.0f}h",
                ticket.status,
            ])
            parent_item.setExpanded(True)
            font = parent_item.font(0)
            font.setBold(True)
            parent_item.setFont(0, font)
            self._tree.addTopLevelItem(parent_item)

            for t in tasks:
                icon = status_icon.get(t.status, "⚪")
                child = QTreeWidgetItem([
                    f"  {icon} {t.title[:50]}",
                    f"{t.estimated_hrs or 0:.0f}h",
                    t.status,
                ])
                parent_item.addChild(child)

        if self._groups:
            summary = QTreeWidgetItem([f"Total estimate: {total_hrs:.1f}h", "", ""])
            summary.setDisabled(True)
            self._tree.addTopLevelItem(summary)

    def _gen_integration_tests(self):
        if not self._tasks:
            QMessageBox.information(self, "No Tasks", "Load sprint tasks first.")
            return
        self._status_lbl.setText("Generating integration tests...")
        task_dicts = [{"title": t.title, "estimated_hrs": t.estimated_hrs} for t in self._tasks]
        self._integ_thread = _IntegTestThread(task_dicts)
        self._integ_thread.done.connect(self._on_integ_done)
        self._integ_thread.error.connect(lambda e: self._status_lbl.setText(f"Error: {e}"))
        self._integ_thread.start()

    def _on_integ_done(self, tests: list):
        self._status_lbl.setText(f"Generated {len(tests)} integration test tasks.")
        self._integ_list.clear()
        sprint = self._sprint_data
        integ_tasks = []
        for t in tests:
            task = task_model.Task(
                id=None, ticket_id=None,
                title=t.get("title", ""),
                estimated_hrs=float(t.get("estimated_hrs", 2)),
                task_type="integration_test",
                start_date=sprint.start_date if sprint else "",
                end_date=sprint.end_date if sprint else "",
            )
            task_model.save(task)
            integ_tasks.append(task)
            self._integ_list.addItem(QListWidgetItem(f"  {task.title}  Est: {task.estimated_hrs}h"))
        self._tasks.extend(integ_tasks)
        if sprint:
            self._timeline.render_gantt(sprint, self._groups)

    def _link_voc(self):
        if not self._sprint_data or not self._sprint_data.id:
            QMessageBox.information(self, "No Sprint", "Load a sprint first.")
            return
        key, ok = QInputDialog.getText(self, "Link VOC Ticket", "VOC Jira key (e.g. VOC-22):")
        if not ok or not key.strip():
            return
        notes, ok2 = QInputDialog.getText(self, "Notes", "Notes (optional):")
        sprint_model.save_voc_link(self._sprint_data.id, key.strip(), task_id=None, notes=notes if ok2 else "", hrs=0.0)
        sprint = sprint_model.get_latest()
        self._populate_sprint(sprint)
