from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QListWidget, QListWidgetItem, QSplitter, QInputDialog, QMessageBox
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from models import sprint as sprint_model
from models import task as task_model
from services import jira_client, ai_service
from ui.timeline_view import TimelineView
from db import database as db


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


class SprintPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._sprint_data = None
        self._tasks = []
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

        left_layout.addWidget(QLabel("Dev Tasks"))
        self._dev_list = QListWidget()
        left_layout.addWidget(self._dev_list)

        left_layout.addWidget(QLabel("Integration Tests"))
        self._integ_list = QListWidget()
        left_layout.addWidget(self._integ_list)

        left_layout.addWidget(QLabel("VOC Tickets"))
        self._voc_list = QListWidget()
        left_layout.addWidget(self._voc_list)

        voc_btn = QPushButton("+ Link VOC Ticket")
        voc_btn.setObjectName("secondary")
        voc_btn.clicked.connect(self._link_voc)
        left_layout.addWidget(voc_btn)

        splitter.addWidget(left)

        self._timeline = TimelineView()
        splitter.addWidget(self._timeline)
        splitter.setSizes([320, 700])
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
        self._tasks = []
        for t in data.get("tasks", []):
            task = task_model.Task(
                id=None, ticket_id=None,
                title=t.get("summary", ""),
                assignee=t.get("assignee", ""),
                estimated_hrs=float(t.get("story_points", 0)),
                task_type=t.get("type", "dev"),
                status=t.get("status", "todo"),
                start_date=data.get("startDate", ""),
                end_date=data.get("endDate", ""),
            )
            saved = task_model.save(task)
            self._tasks.append(task)
        sprint = sprint_model.get_latest()
        self._populate_sprint(sprint)

    def _populate_sprint(self, sprint):
        if not sprint:
            return
        self._sprint_data = sprint
        self._sprint_lbl.setText(f"Sprint: {sprint.name}  ({sprint.dev_days} dev days / {sprint.test_days} test days)")
        self._status_lbl.setText("")

        self._dev_list.clear()
        self._integ_list.clear()

        for t in self._tasks:
            if t.task_type == "integration_test":
                item = QListWidgetItem(f"  {t.title}  Est: {t.estimated_hrs}h")
                self._integ_list.addItem(item)
            else:
                status_icon = {"todo": "🔵", "in_progress": "🟡", "done": "🟢"}.get(t.status, "⚪")
                item = QListWidgetItem(f"{status_icon} {t.title}  Est: {t.estimated_hrs}h  {t.status}")
                self._dev_list.addItem(item)

        voc_links = sprint_model.get_voc_links(sprint.id) if sprint.id else []
        self._voc_list.clear()
        for v in voc_links:
            item = QListWidgetItem(f"🔴 {v['voc_jira_key']}  → Logged: {v.get('logged_hrs', 0)}h  {v.get('notes', '')}")
            self._voc_list.addItem(item)

        self._timeline.render_gantt(sprint, self._tasks)

    def _gen_integration_tests(self):
        tasks = self._tasks
        if not tasks:
            QMessageBox.information(self, "No Tasks", "Load sprint tasks first.")
            return
        self._status_lbl.setText("Generating integration tests...")
        self._integ_thread = _IntegTestThread(tasks)
        self._integ_thread.done.connect(self._on_integ_done)
        self._integ_thread.error.connect(lambda e: self._status_lbl.setText(f"Error: {e}"))
        self._integ_thread.start()

    def _on_integ_done(self, tests: list):
        self._status_lbl.setText(f"Generated {len(tests)} integration test tasks.")
        self._integ_list.clear()
        for t in tests:
            task = task_model.Task(
                id=None, ticket_id=None,
                title=t.get("title", ""),
                estimated_hrs=float(t.get("estimated_hrs", 2)),
                task_type="integration_test",
            )
            task_model.save(task)
            self._integ_list.addItem(QListWidgetItem(f"  {task.title}  Est: {task.estimated_hrs}h"))

    def _link_voc(self):
        if not self._sprint_data or not self._sprint_data.id:
            QMessageBox.information(self, "No Sprint", "Load a sprint first.")
            return
        key, ok = QInputDialog.getText(self, "Link VOC Ticket", "VOC Jira key (e.g. VOC-22):")
        if not ok or not key.strip():
            return
        notes, ok2 = QInputDialog.getText(self, "Notes", "Notes (optional):")
        sprint_model.save_voc_link(self._sprint_data.id, key.strip(), notes=notes if ok2 else "")
        sprint = sprint_model.get_latest()
        self._populate_sprint(sprint)
