from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QListWidget, QListWidgetItem, QSplitter,
    QScrollArea, QMessageBox, QInputDialog
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from db import database as db
from models import ticket as ticket_model
from services import jira_client
from ui.style import status_pill_style


def _local_tickets_as_items() -> list[dict]:
    """Convert locally stored tickets to the same dict shape Jira returns."""
    tickets = ticket_model.get_all()
    return [
        {
            "key": t.jira_key,
            "summary": t.title,
            "description": t.srs_content or t.description or "",
            "status": t.status,
            "_local": True,
        }
        for t in tickets
    ]


class _SRSFetcher(QThread):
    done = pyqtSignal(list)
    error = pyqtSignal(str)

    def run(self):
        try:
            proj = db.get_setting("jira_default_project", "").split("—")[0].strip()
            jira_items = jira_client.fetch_srs_list(proj)
            # Merge: local tickets not already returned by Jira come first
            jira_keys = {i["key"] for i in jira_items}
            local_only = [i for i in _local_tickets_as_items() if i["key"] not in jira_keys]
            self.done.emit(local_only + jira_items)
        except Exception:
            # Jira unavailable — fall back to local DB only
            self.done.emit(_local_tickets_as_items())


class SRSPanel(QWidget):
    ticket_selected = pyqtSignal(int)  # emits local DB ticket id

    def __init__(self, parent=None):
        super().__init__(parent)
        self._srs_items: list[dict] = []
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        splitter = QSplitter(Qt.Orientation.Horizontal)

        # Left — SRS list
        left = QWidget()
        ll = QVBoxLayout(left)
        ll.setContentsMargins(12, 12, 6, 12)

        top_row = QHBoxLayout()
        top_row.addWidget(QLabel("SRS"))
        top_row.addStretch()
        refresh_btn = QPushButton("🔄 Refresh")
        refresh_btn.setObjectName("secondary")
        refresh_btn.clicked.connect(self._load_srs)
        top_row.addWidget(refresh_btn)
        ll.addLayout(top_row)

        self._list = QListWidget()
        self._list.itemClicked.connect(self._on_select)
        ll.addWidget(self._list)

        new_btn = QPushButton("+ New Ticket")
        new_btn.setObjectName("secondary")
        new_btn.clicked.connect(self._new_ticket)
        ll.addWidget(new_btn)

        left.setMinimumWidth(240)
        left.setMaximumWidth(300)
        splitter.addWidget(left)

        # Right — preview
        right = QWidget()
        rl = QVBoxLayout(right)
        rl.setContentsMargins(6, 12, 12, 12)
        self._right_label = QLabel("Select an SRS ticket from the list.")
        self._right_label.setWordWrap(True)
        self._right_label.setStyleSheet("color: #8a9bb0;")
        rl.addWidget(self._right_label)

        self._detail_container = QScrollArea()
        self._detail_container.setWidgetResizable(True)
        self._detail_container.hide()
        rl.addWidget(self._detail_container)

        splitter.addWidget(right)
        splitter.setSizes([260, 700])

        layout.addWidget(splitter)
        self._load_srs()

    def _load_srs(self):
        self._list.clear()
        self._fetcher = _SRSFetcher()
        self._fetcher.done.connect(self._on_srs_loaded)
        self._fetcher.error.connect(lambda e: self._right_label.setText(f"Error: {e}"))
        self._fetcher.start()

    def _on_srs_loaded(self, items: list[dict]):
        self._srs_items = items
        self._list.clear()
        status_icon = {
            "draft": "⚪", "ready": "🔵", "in_progress": "🟡",
            "posted": "🟢", "done": "🟢",
        }
        for item in items:
            icon = status_icon.get(item.get("status", ""), "⚪")
            lbl = f"{icon} {item['key']}  {item['summary'][:45]}"
            list_item = QListWidgetItem(lbl)
            list_item.setData(Qt.ItemDataRole.UserRole, item)
            self._list.addItem(list_item)
        if not items:
            self._right_label.setText("No tickets found. Configure Jira in Settings or run seed_data.py.")

    def _on_select(self, item: QListWidgetItem):
        data = item.data(Qt.ItemDataRole.UserRole)
        existing = ticket_model.get_by_jira_key(data["key"])
        if existing:
            ticket_id = existing.id
        else:
            t = ticket_model.Ticket(
                id=None, jira_key=data["key"], title=data["summary"],
                srs_content=data.get("description", ""),
            )
            ticket_id = ticket_model.save(t)
        self.ticket_selected.emit(ticket_id)
        self._show_detail(ticket_id)

    def _new_ticket(self):
        key, ok = QInputDialog.getText(self, "New Ticket", "Jira key (e.g. PROJ-120):")
        if not ok or not key.strip():
            return
        title, ok2 = QInputDialog.getText(self, "New Ticket", "Title:")
        if not ok2 or not title.strip():
            return
        existing = ticket_model.get_by_jira_key(key.strip())
        if existing:
            QMessageBox.information(self, "Exists", f"{key} already exists — opening it.")
            self._show_detail(existing.id)
            return
        t = ticket_model.Ticket(id=None, jira_key=key.strip(), title=title.strip())
        ticket_id = ticket_model.save(t)
        self._load_srs()
        self._show_detail(ticket_id)

    def _show_detail(self, ticket_id: int):
        from ui.ticket_detail import TicketDetailPanel
        self._right_label.hide()
        detail = TicketDetailPanel(ticket_id)
        self._detail_container.setWidget(detail)
        self._detail_container.show()
