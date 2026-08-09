from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTextEdit,
    QPushButton, QScrollArea, QFrame, QSizePolicy
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from services import ai_service
from models import ticket as ticket_model
from db import database as db


class _AIThread(QThread):
    response = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(self, fn, *args):
        super().__init__()
        self._fn = fn
        self._args = args

    def run(self):
        try:
            result = self._fn(*self._args)
            self.response.emit(result)
        except Exception as e:
            self.error.emit(str(e))


class RequirementChat(QWidget):
    elaboration_complete = pyqtSignal()

    def __init__(self, ticket_id: int, parent=None):
        super().__init__(parent)
        self._ticket_id = ticket_id
        self._history: list[dict] = []
        self._elaboration_started = False
        self._build_ui()
        self._load_ticket()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        # SRS preview
        srs_label = QLabel("SRS CONTENT")
        srs_label.setObjectName("section_title")
        layout.addWidget(srs_label)
        self._srs_view = QTextEdit()
        self._srs_view.setReadOnly(True)
        self._srs_view.setMaximumHeight(100)
        self._srs_view.setStyleSheet("color: #8a9bb0; background-color: #0f1420;")
        layout.addWidget(self._srs_view)

        # Description input
        desc_label = QLabel("YOUR DESCRIPTION")
        desc_label.setObjectName("section_title")
        layout.addWidget(desc_label)
        self._desc_input = QTextEdit()
        self._desc_input.setPlaceholderText("Describe the requirement in your own words...")
        self._desc_input.setMaximumHeight(80)
        layout.addWidget(self._desc_input)

        send_btn = QPushButton("Send to AI ▶")
        send_btn.clicked.connect(self._start_elaboration)
        layout.addWidget(send_btn, alignment=Qt.AlignmentFlag.AlignRight)

        # Chat area
        chat_label = QLabel("AI CHAT")
        chat_label.setObjectName("section_title")
        layout.addWidget(chat_label)

        self._chat_area = QScrollArea()
        self._chat_area.setWidgetResizable(True)
        chat_inner = QWidget()
        self._chat_layout = QVBoxLayout(chat_inner)
        self._chat_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self._chat_area.setWidget(chat_inner)
        layout.addWidget(self._chat_area)

        # Reply row
        reply_row = QHBoxLayout()
        from PyQt6.QtWidgets import QLineEdit
        self._reply_input = QLineEdit()
        self._reply_input.setPlaceholderText("Type your answer...")
        self._reply_input.returnPressed.connect(self._send_reply)
        reply_row.addWidget(self._reply_input)
        reply_btn = QPushButton("Send")
        reply_btn.clicked.connect(self._send_reply)
        reply_row.addWidget(reply_btn)
        layout.addLayout(reply_row)

        # Generate button (hidden until elaboration complete)
        self._gen_btn = QPushButton("⚡ Generate All")
        self._gen_btn.setStyleSheet("font-size: 15px; padding: 10px 24px;")
        self._gen_btn.hide()
        layout.addWidget(self._gen_btn, alignment=Qt.AlignmentFlag.AlignCenter)

    def _load_ticket(self):
        t = ticket_model.get_by_id(self._ticket_id)
        if t:
            self._srs_view.setPlainText(t.srs_content or "")
            if t.description:
                self._desc_input.setPlainText(t.description)
        # Load existing chat history
        rows = db.fetchall("SELECT role, content FROM chat_messages WHERE ticket_id=? ORDER BY id", (self._ticket_id,))
        for r in rows:
            self._add_bubble(r["role"], r["content"])
            self._history.append({"role": r["role"], "content": r["content"]})

    def _start_elaboration(self):
        desc = self._desc_input.toPlainText().strip()
        if not desc:
            return
        # Save description
        t = ticket_model.get_by_id(self._ticket_id)
        if t:
            t.description = desc
            ticket_model.save(t)

        self._add_bubble("user", desc)
        self._history.append({"role": "user", "content": desc})
        self._save_message("user", desc)

        srs = t.srs_content if t else ""
        self._elaboration_started = True
        self._run_ai(ai_service.start_elaboration, srs, desc)

    def _send_reply(self):
        text = self._reply_input.text().strip()
        if not text:
            return
        self._reply_input.clear()
        self._add_bubble("user", text)
        self._history.append({"role": "user", "content": text})
        self._save_message("user", text)
        self._run_ai(ai_service.continue_elaboration, list(self._history))

    def _run_ai(self, fn, *args):
        self._thread = _AIThread(fn, *args)
        self._thread.response.connect(self._on_ai_response)
        self._thread.error.connect(lambda e: self._add_bubble("assistant", f"Error: {e}"))
        self._thread.start()

    def _on_ai_response(self, text: str):
        if "ELABORATION_COMPLETE" in text:
            self._add_bubble("assistant", "✓ I have enough information. Click Generate All to proceed.")
            self._gen_btn.show()
            self.elaboration_complete.emit()
        else:
            self._add_bubble("assistant", text)
            self._history.append({"role": "assistant", "content": text})
            self._save_message("assistant", text)

    def _add_bubble(self, role: str, text: str):
        bubble = QLabel(text)
        bubble.setWordWrap(True)
        bubble.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        if role == "assistant":
            bubble.setStyleSheet("background-color: #1a2133; border-left: 3px solid #4a90d9; padding: 8px 12px; border-radius: 2px; color: #e8ecf0;")
        else:
            bubble.setStyleSheet("background-color: #2a3a55; padding: 8px 12px; border-radius: 4px; color: #e8ecf0; margin-left: 40px;")
        self._chat_layout.addWidget(bubble)

    def _save_message(self, role: str, content: str):
        db.execute("INSERT INTO chat_messages (ticket_id,role,content) VALUES (?,?,?)",
                   (self._ticket_id, role, content))
        db.commit()

    def connect_generate(self, slot):
        self._gen_btn.clicked.connect(slot)

    def get_history(self) -> list[dict]:
        return self._history

