import threading
from datetime import datetime

from PyQt6.QtCore import Qt, QThread, pyqtSignal, QObject
from PyQt6.QtGui import QFont, QKeySequence, QShortcut
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from core.orchestrator import Orchestrator
from utils.config import Settings
from core.memory import SQLiteMemory


class WorkerSignals(QObject):
    token = pyqtSignal(str)
    tool_call = pyqtSignal(str)
    finished = pyqtSignal()
    error = pyqtSignal(str)


class ChatWorker(QThread):
    def __init__(self, orchestrator: Orchestrator, message: str):
        super().__init__()
        self._orc = orchestrator
        self._msg = message
        self.signals = WorkerSignals()

    def run(self):
        try:
            def on_tool(name, _args):
                label = {
                    "run_jira_agent": "⚙ Checking Jira...",
                    "run_bitbucket_agent": "⚙ Checking Bitbucket...",
                    "bitbucket_inspect_repo": "⚙ Inspecting repo...",
                    "confluence_create_page": "⚙ Creating Confluence page...",
                    "confluence_list_pages": "⚙ Listing Confluence pages...",
                    "recall_memory": "⚙ Reading memory...",
                }.get(name, f"⚙ Running {name}...")
                self.signals.tool_call.emit(label)

            for chunk in self._orc.stream_chat(self._msg, on_tool_call=on_tool):
                self.signals.token.emit(chunk)
            self.signals.finished.emit()
        except Exception as exc:
            self.signals.error.emit(str(exc))


class MessageBubble(QFrame):
    def __init__(self, text: str, role: str):
        super().__init__()
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)

        label = QLabel(text)
        label.setWordWrap(True)
        label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        label.setFont(QFont("Segoe UI", 10))

        if role == "user":
            label.setStyleSheet(
                "background:#0078D4; color:white; border-radius:10px; padding:8px 12px;"
            )
            layout.addStretch()
            layout.addWidget(label)
        elif role == "status":
            label.setStyleSheet("color:#888; font-style:italic; padding:2px 8px;")
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addStretch()
            layout.addWidget(label)
            layout.addStretch()
        else:  # pattu
            label.setStyleSheet(
                "background:#2D2D2D; color:#E0E0E0; border-radius:10px; padding:8px 12px;"
            )
            layout.addWidget(label)
            layout.addStretch()

        self.setStyleSheet("border:none;")
        self._label = label

    def append_text(self, text: str) -> None:
        self._label.setText(self._label.text() + text)


class ChatWindow(QWidget):
    def __init__(self, settings: Settings):
        super().__init__()
        self._settings = settings
        self._memory = SQLiteMemory(settings.memory_db_path)
        self._orchestrator = Orchestrator(settings, self._memory)
        self._worker: ChatWorker | None = None
        self._current_bubble: MessageBubble | None = None

        self.setWindowTitle("Pattu")
        self.setMinimumSize(480, 600)
        self.resize(520, 680)
        self.setStyleSheet("background:#1A1A1A;")

        self._build_ui()
        self._restore_geometry()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Status bar
        self._status = QLabel("  Pattu  ·  Ready")
        self._status.setStyleSheet(
            "background:#111; color:#888; padding:6px 12px; font-size:11px;"
        )
        root.addWidget(self._status)

        # Scroll area
        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setStyleSheet("border:none; background:#1A1A1A;")

        self._messages_widget = QWidget()
        self._messages_widget.setStyleSheet("background:#1A1A1A;")
        self._messages_layout = QVBoxLayout(self._messages_widget)
        self._messages_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self._messages_layout.setSpacing(6)
        self._messages_layout.setContentsMargins(12, 12, 12, 12)
        self._scroll.setWidget(self._messages_widget)
        root.addWidget(self._scroll, 1)

        # Input row
        input_row = QHBoxLayout()
        input_row.setContentsMargins(12, 8, 12, 12)
        input_row.setSpacing(8)

        self._input = QLineEdit()
        self._input.setPlaceholderText("Ask Pattu anything...")
        self._input.setStyleSheet(
            "background:#2A2A2A; color:#E0E0E0; border:1px solid #444;"
            "border-radius:8px; padding:8px 12px; font-size:13px;"
        )
        self._input.returnPressed.connect(self._send)
        input_row.addWidget(self._input, 1)

        send_btn = QPushButton("Send")
        send_btn.setStyleSheet(
            "background:#0078D4; color:white; border-radius:8px; padding:8px 16px; font-weight:bold;"
        )
        send_btn.clicked.connect(self._send)
        input_row.addWidget(send_btn)

        brief_btn = QPushButton("Daily Brief")
        brief_btn.setStyleSheet(
            "background:#444; color:#E0E0E0; border-radius:8px; padding:8px 12px;"
        )
        brief_btn.clicked.connect(self._daily_brief)
        input_row.addWidget(brief_btn)

        root.addLayout(input_row)

        self._add_bubble("pattu", "Hi Akshay! I'm Pattu. What can I help you with today?")

    def _add_bubble(self, role: str, text: str) -> MessageBubble:
        bubble = MessageBubble(text, role)
        self._messages_layout.addWidget(bubble)
        self._scroll_to_bottom()
        return bubble

    def _scroll_to_bottom(self) -> None:
        bar = self._scroll.verticalScrollBar()
        bar.setValue(bar.maximum())

    def _send(self) -> None:
        text = self._input.text().strip()
        if not text or self._worker is not None:
            return
        self._input.clear()
        self._add_bubble("user", text)
        self._run_query(text)

    def _daily_brief(self) -> None:
        if self._worker is not None:
            return
        query = (
            "Give me my daily brief: check all my Jira tickets, open Bitbucket PRs, "
            "and if there are any bugs, inspect the relevant repos and suggest fixes."
        )
        self._add_bubble("user", query)
        self._run_query(query)

    def _run_query(self, query: str) -> None:
        self._current_bubble = None
        self._update_status("Pattu  ·  Thinking...")

        self._worker = ChatWorker(self._orchestrator, query)
        self._worker.signals.tool_call.connect(self._on_tool_call)
        self._worker.signals.token.connect(self._on_token)
        self._worker.signals.finished.connect(self._on_finished)
        self._worker.signals.error.connect(self._on_error)
        self._worker.start()

    def _on_tool_call(self, label: str) -> None:
        self._add_bubble("status", label)
        self._current_bubble = None

    def _on_token(self, text: str) -> None:
        if self._current_bubble is None:
            self._current_bubble = self._add_bubble("pattu", "")
        self._current_bubble.append_text(text)
        self._scroll_to_bottom()

    def _on_finished(self) -> None:
        self._worker = None
        self._current_bubble = None
        self._update_status(f"Pattu  ·  Last run {datetime.now().strftime('%I:%M %p')}")

    def _on_error(self, msg: str) -> None:
        self._add_bubble("status", f"⚠ Error: {msg}")
        self._worker = None
        self._current_bubble = None
        self._update_status("Pattu  ·  Error")

    def _update_status(self, text: str) -> None:
        self._status.setText(f"  {text}")

    def toggle(self) -> None:
        if self.isVisible():
            self._save_geometry()
            self.hide()
        else:
            self._restore_geometry()
            self.show()
            self.raise_()
            self.activateWindow()
            self._input.setFocus()

    def _save_geometry(self) -> None:
        self._memory.set("gui.chat_x", self.x(), "pattu")
        self._memory.set("gui.chat_y", self.y(), "pattu")

    def _restore_geometry(self) -> None:
        x = self._memory.get("gui.chat_x")
        y = self._memory.get("gui.chat_y")
        if x is not None and y is not None:
            self.move(int(x), int(y))

    def closeEvent(self, event) -> None:
        self._save_geometry()
        event.ignore()
        self.hide()
