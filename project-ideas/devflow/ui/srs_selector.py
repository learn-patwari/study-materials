from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QListWidget, QListWidgetItem, QSplitter, QTextEdit, QLineEdit,
    QScrollArea, QFrame, QMessageBox
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from db import database as db
from models import ticket as ticket_model
from services import jira_client
from ui.style import status_pill_style


class _SRSFetcher(QThread):
    done = pyqtSignal(list)
    error = pyqtSignal(str)

    def run(self):
        try:
            proj = db.get_setting("jira_default_project", "").split("—")[0].strip()
            items = jira_client.fetch_srs_list(proj)
            self.done.emit(items)
        except Exception as e:
            self.error.emit(str(e))


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

        self._desc_preview = QTextEdit()
        self._desc_preview.setReadOnly(True)
        self._desc_preview.hide()
        rl.addWidget(self._desc_preview)

        self._open_btn = QPushButton("Open Ticket →")
        self._open_btn.hide()
        self._open_btn.clicked.connect(self._open_selected)
        rl.addWidget(self._open_btn, alignment=Qt.AlignmentFlag.AlignRight)
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
        for item in items:
            lbl = f"{item['key']}  {item['summary'][:50]}"
            list_item = QListWidgetItem(lbl)
            list_item.setData(Qt.ItemDataRole.UserRole, item)
            self._list.addItem(list_item)

    def _on_select(self, item: QListWidgetItem):
        data = item.data(Qt.ItemDataRole.UserRole)
        self._current = data
        self._desc_preview.setPlainText(data.get("description", "") or "(no description)")
        self._right_label.setText(f"{data['key']} — {data['summary']}")
        self._desc_preview.show()
        self._open_btn.show()

    def _open_selected(self):
        if not hasattr(self, "_current"):
            return
        data = self._current
        existing = ticket_model.get_by_jira_key(data["key"])
        if existing:
            self.ticket_selected.emit(existing.id)
        else:
            t = ticket_model.Ticket(
                id=None, jira_key=data["key"], title=data["summary"],
                srs_content=data.get("description", ""),
            )
            tid = ticket_model.save(t)
            self.ticket_selected.emit(tid)
