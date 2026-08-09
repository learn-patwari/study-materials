from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QComboBox,
    QScrollArea, QFrame
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from db import database as db
from models import task as task_model
from services import jira_client
from ui.style import status_pill_style
import datetime


class _BugFetcher(QThread):
    done = pyqtSignal(dict)
    error = pyqtSignal(str)

    def __init__(self, project_key: str, period_days):
        super().__init__()
        self.project_key = project_key
        self.period_days = period_days

    def run(self):
        try:
            counts = jira_client.fetch_bug_counts(self.project_key, self.period_days)
            self.done.emit(counts)
        except Exception as e:
            self.error.emit(str(e))


class DashboardPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # Header
        header = QHBoxLayout()
        title = QLabel("Dashboard")
        title.setStyleSheet("font-size: 18px; font-weight: bold;")
        header.addWidget(title)
        header.addStretch()
        now = QLabel(datetime.datetime.now().strftime("%Y-%m-%d  %H:%M"))
        now.setStyleSheet("color: #8a9bb0;")
        header.addWidget(now)
        layout.addLayout(header)

        # Alerts section
        alerts_label = QLabel("🚨  ALERTS")
        alerts_label.setObjectName("section_title")
        layout.addWidget(alerts_label)
        self._alerts_frame = QVBoxLayout()
        alerts_widget = QWidget()
        alerts_widget.setLayout(self._alerts_frame)
        layout.addWidget(alerts_widget)

        # Bug counter
        bc_label = QLabel("BUG COUNTER")
        bc_label.setObjectName("section_title")
        layout.addWidget(bc_label)
        bc_row = QHBoxLayout()
        self._proj_combo = QComboBox()
        self._proj_combo.setFixedWidth(180)
        bc_row.addWidget(QLabel("Project:"))
        bc_row.addWidget(self._proj_combo)

        self._period_combo = QComboBox()
        for label, val in [("Last 7 days", 7), ("Last 30 days", 30), ("Last 90 days", 90), ("All time", None)]:
            self._period_combo.addItem(label, val)
        self._period_combo.setCurrentIndex(1)
        bc_row.addWidget(QLabel("Period:"))
        bc_row.addWidget(self._period_combo)

        refresh_btn = QPushButton("🔄 Refresh"); refresh_btn.setObjectName("secondary")
        refresh_btn.clicked.connect(self._refresh_bugs)
        bc_row.addWidget(refresh_btn)
        bc_row.addStretch()
        layout.addLayout(bc_row)

        self._bug_tiles = QHBoxLayout()
        for attr, label in [("_tile_total", "Total"), ("_tile_open", "Open"),
                             ("_tile_inprog", "In Progress"), ("_tile_resolved", "Resolved")]:
            tile = self._make_tile(label, "—")
            setattr(self, attr, tile[1])
            self._bug_tiles.addWidget(tile[0])
        self._bug_tiles.addStretch()
        layout.addLayout(self._bug_tiles)

        # Today's tasks
        today_label = QLabel("TODAY'S TASKS")
        today_label.setObjectName("section_title")
        layout.addWidget(today_label)
        self._tasks_layout = QVBoxLayout()
        tasks_widget = QWidget()
        tasks_widget.setLayout(self._tasks_layout)
        layout.addWidget(tasks_widget)

        layout.addStretch()
        self._populate_projects()
        self.refresh()

    def _make_tile(self, label: str, value: str):
        frame = QFrame()
        frame.setObjectName("panel")
        frame.setFixedSize(130, 80)
        inner = QVBoxLayout(frame)
        val_lbl = QLabel(value)
        val_lbl.setStyleSheet("font-size: 28px; font-weight: bold; color: #4a90d9;")
        val_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl = QLabel(label)
        lbl.setStyleSheet("color: #8a9bb0; font-size: 11px;")
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        inner.addWidget(val_lbl)
        inner.addWidget(lbl)
        return frame, val_lbl

    def _populate_projects(self):
        self._proj_combo.clear()
        proj = db.get_setting("jira_default_project", "")
        if proj:
            self._proj_combo.addItem(proj.split("—")[0].strip(), proj.split("—")[0].strip())

    def refresh(self):
        self._refresh_alerts()
        self._refresh_today_tasks()

    def _refresh_alerts(self):
        while self._alerts_frame.count():
            item = self._alerts_frame.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        overdue = task_model.get_overdue()
        due_today = task_model.get_due_today()

        if not overdue and not due_today:
            ok = QLabel("✓  No overdue or due-today tasks")
            ok.setStyleSheet("color: #3ab06a; padding: 8px;")
            self._alerts_frame.addWidget(ok)
            return

        for t in overdue:
            lbl = QLabel(f"🔴  OVERDUE — {t.jira_task_key or ''} · {t.title}  (due {t.end_date})")
            lbl.setObjectName("alert_red")
            lbl.setWordWrap(True)
            self._alerts_frame.addWidget(lbl)

        for t in due_today:
            close_time = db.get_setting("task_auto_close_time", "23:59")
            lbl = QLabel(f"🟡  DUE TODAY — {t.jira_task_key or ''} · {t.title}  (closes at {close_time})")
            lbl.setObjectName("alert_amber")
            lbl.setWordWrap(True)
            self._alerts_frame.addWidget(lbl)

    def _refresh_today_tasks(self):
        while self._tasks_layout.count():
            item = self._tasks_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        due_today = task_model.get_due_today()
        if not due_today:
            lbl = QLabel("No tasks due today.")
            lbl.setStyleSheet("color: #8a9bb0;")
            self._tasks_layout.addWidget(lbl)
            return

        for t in due_today:
            row = QHBoxLayout()
            check = QLabel("☐" if t.status != "done" else "☑")
            check.setFixedWidth(20)
            row.addWidget(check)
            info = QLabel(f"{t.jira_task_key or ''}  ·  {t.title}  (est {t.estimated_hrs}h)")
            row.addWidget(info)
            pill = QLabel(t.status.replace("_", " ").title())
            pill.setStyleSheet(status_pill_style(t.status))
            row.addWidget(pill)
            row.addStretch()
            w = QWidget(); w.setLayout(row)
            self._tasks_layout.addWidget(w)

    def _refresh_bugs(self):
        proj = self._proj_combo.currentData() or self._proj_combo.currentText()
        if not proj:
            return
        period = self._period_combo.currentData()
        self._fetcher = _BugFetcher(proj, period)
        self._fetcher.done.connect(self._on_bug_counts)
        self._fetcher.error.connect(lambda e: None)
        self._fetcher.start()

    def _on_bug_counts(self, counts: dict):
        self._tile_total.setText(str(counts.get("total", 0)))
        self._tile_open.setText(str(counts.get("open", 0)))
        self._tile_inprog.setText(str(counts.get("in_progress", 0)))
        self._tile_resolved.setText(str(counts.get("resolved", 0)))
