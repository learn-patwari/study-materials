from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QTextEdit
from models import document as doc_model


class SDDPanel(QWidget):
    def __init__(self, ticket_id: int, parent=None):
        super().__init__(parent)
        self._ticket_id = ticket_id
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)

        top = QHBoxLayout()
        top.addWidget(QLabel("Software Design Document"))
        top.addStretch()
        save_btn = QPushButton("💾 Save"); save_btn.clicked.connect(self._save)
        top.addWidget(save_btn)
        layout.addLayout(top)

        self._editor = QTextEdit()
        self._editor.setPlaceholderText("SDD will appear here after generation...")
        layout.addWidget(self._editor)

    def load(self):
        doc = doc_model.get(self._ticket_id, "sdd")
        self._editor.setPlainText(doc.content if doc else "")

    def showEvent(self, event):
        super().showEvent(event)
        self.load()

    def _save(self):
        doc_model.save(doc_model.Document(None, self._ticket_id, "sdd", self._editor.toPlainText()))
