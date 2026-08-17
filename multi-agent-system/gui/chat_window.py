from datetime import datetime

from PyQt6.QtCore import Qt, QThread, QObject, pyqtSignal
from PyQt6.QtGui import QFont, QPixmap
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

from core.memory import SQLiteMemory
from core.orchestrator import Orchestrator
from gui import theme
from gui.assets import asset_exists, asset_path
from gui.mascot_states import MascotState, state_for_tool
from utils.config import Settings

TOOL_LABELS = {
    "run_jira_agent": "⚙ Checking Jira...",
    "run_bitbucket_agent": "⚙ Checking Bitbucket...",
    "bitbucket_inspect_repo": "⚙ Inspecting repo...",
    "confluence_create_page": "⚙ Creating Confluence page...",
    "confluence_list_pages": "⚙ Listing Confluence pages...",
    "recall_memory": "⚙ Reading memory...",
}

DAILY_BRIEF_QUERY = (
    "Give me my daily brief: check all my Jira tickets, open Bitbucket PRs, "
    "and if there are any bugs, inspect the relevant repos and suggest fixes."
)


class WorkerSignals(QObject):
    token = pyqtSignal(str)
    # Raw tool name plus the label to display. The mascot keys off the name, so
    # it can't be collapsed into the pretty string.
    tool_call = pyqtSignal(str, str)
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
                label = TOOL_LABELS.get(name, f"⚙ Running {name}...")
                self.signals.tool_call.emit(name, label)

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
        layout.setSpacing(8)

        label = QLabel(text)
        label.setWordWrap(True)
        label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        label.setFont(QFont(theme.FONT_FAMILY, theme.FONT_SIZE_PT))

        if role == "user":
            label.setStyleSheet(theme.BUBBLE_USER_STYLE)
            layout.addStretch()
            layout.addWidget(label)
        elif role in ("status", "error"):
            label.setStyleSheet(
                theme.BUBBLE_ERROR_STYLE if role == "error" else theme.BUBBLE_STATUS_STYLE
            )
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addStretch()
            layout.addWidget(label)
            layout.addStretch()
        else:  # pattu
            avatar = self._make_avatar()
            if avatar is not None:
                layout.addWidget(avatar, 0, Qt.AlignmentFlag.AlignTop)
            label.setStyleSheet(theme.BUBBLE_PATTU_STYLE)
            layout.addWidget(label)
            layout.addStretch()

        self.setStyleSheet("border:none;")
        self._label = label

    @staticmethod
    def _make_avatar() -> QLabel | None:
        if not asset_exists("icons", "profile.png"):
            return None
        size = theme.AVATAR_SIZE
        avatar = QLabel()
        avatar.setFixedSize(size, size)
        avatar.setPixmap(
            QPixmap(asset_path("icons", "profile.png")).scaled(
                size,
                size,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
        )
        return avatar

    def append_text(self, text: str) -> None:
        self._label.setText(self._label.text() + text)


class ChatWindow(QWidget):
    # Emitted whenever Pattu's activity changes. app.py connects this to the
    # mascot, so the chat window never needs to know the mascot exists.
    mascot_state = pyqtSignal(object)

    def __init__(self, settings: Settings):
        super().__init__()
        self._settings = settings
        self._memory = SQLiteMemory(settings.memory_db_path)
        self._orchestrator = Orchestrator(settings, self._memory)
        self._worker: ChatWorker | None = None
        self._current_bubble: MessageBubble | None = None
        self._is_daily_brief = False

        self.setWindowTitle("Pattu")
        self.setMinimumSize(480, 600)
        self.resize(520, 680)
        self.setStyleSheet(theme.WINDOW_STYLE)

        self._build_ui()
        self._restore_geometry()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self._status = QLabel("  Pattu  ·  Ready")
        self._status.setStyleSheet(theme.STATUS_BAR_STYLE)
        root.addWidget(self._status)

        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setStyleSheet(theme.SCROLL_AREA_STYLE)

        self._messages_widget = QWidget()
        self._messages_widget.setStyleSheet(theme.MESSAGES_STYLE)
        self._messages_layout = QVBoxLayout(self._messages_widget)
        self._messages_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self._messages_layout.setSpacing(6)
        self._messages_layout.setContentsMargins(12, 12, 12, 12)
        self._scroll.setWidget(self._messages_widget)
        root.addWidget(self._scroll, 1)

        input_row = QHBoxLayout()
        input_row.setContentsMargins(12, 8, 12, 12)
        input_row.setSpacing(8)

        self._input = QLineEdit()
        self._input.setPlaceholderText("Ask Pattu anything...")
        self._input.setStyleSheet(theme.INPUT_STYLE)
        self._input.returnPressed.connect(self._send)
        input_row.addWidget(self._input, 1)

        send_btn = QPushButton("Send")
        send_btn.setStyleSheet(theme.BUTTON_PRIMARY_STYLE)
        send_btn.clicked.connect(self._send)
        input_row.addWidget(send_btn)

        brief_btn = QPushButton("Daily Brief")
        brief_btn.setStyleSheet(theme.BUTTON_SECONDARY_STYLE)
        brief_btn.clicked.connect(self.run_daily_brief)
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

    # ── Sending ───────────────────────────────────────────────────────────────

    def _send(self) -> None:
        text = self._input.text().strip()
        if not text or self._worker is not None:
            return
        self._input.clear()
        self._add_bubble("user", text)
        self._is_daily_brief = False
        self._run_query(text)

    def run_daily_brief(self) -> None:
        if self._worker is not None:
            return
        self._add_bubble("user", DAILY_BRIEF_QUERY)
        self._is_daily_brief = True
        self._run_query(DAILY_BRIEF_QUERY)

    def _run_query(self, query: str) -> None:
        self._current_bubble = None
        self._update_status("Pattu  ·  Thinking...")
        self.mascot_state.emit(MascotState.THINKING)

        self._worker = ChatWorker(self._orchestrator, query)
        self._worker.signals.tool_call.connect(self._on_tool_call)
        self._worker.signals.token.connect(self._on_token)
        self._worker.signals.finished.connect(self._on_finished)
        self._worker.signals.error.connect(self._on_error)
        self._worker.start()

    # ── Worker callbacks ──────────────────────────────────────────────────────

    def _on_tool_call(self, name: str, label: str) -> None:
        self._add_bubble("status", label)
        self._current_bubble = None
        self.mascot_state.emit(state_for_tool(name))

    def _on_token(self, text: str) -> None:
        if self._current_bubble is None:
            self._current_bubble = self._add_bubble("pattu", "")
            self.mascot_state.emit(MascotState.EXPLAINING)
        self._current_bubble.append_text(text)
        self._scroll_to_bottom()

    def _on_finished(self) -> None:
        self._worker = None
        self._current_bubble = None
        self._update_status(f"Pattu  ·  Last run {datetime.now().strftime('%I:%M %p')}")
        self.mascot_state.emit(
            MascotState.CELEBRATING if self._is_daily_brief else MascotState.SUCCESS
        )
        self._is_daily_brief = False

    def _on_error(self, msg: str) -> None:
        self._add_bubble("error", f"⚠ Error: {msg}")
        self._worker = None
        self._current_bubble = None
        self._is_daily_brief = False
        self._update_status("Pattu  ·  Error")
        self.mascot_state.emit(MascotState.IDLE)

    def _update_status(self, text: str) -> None:
        self._status.setText(f"  {text}")

    # ── Window ────────────────────────────────────────────────────────────────

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
