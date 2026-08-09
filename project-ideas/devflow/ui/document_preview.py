from PyQt6.QtWidgets import QWidget, QVBoxLayout, QTextEdit, QLabel


class DocumentPreview(QWidget):
    def __init__(self, title: str = "Preview", parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        lbl = QLabel(title)
        lbl.setStyleSheet("color: #8a9bb0; font-size: 11px;")
        layout.addWidget(lbl)
        self._view = QTextEdit()
        self._view.setReadOnly(True)
        layout.addWidget(self._view)

    def set_content(self, text: str):
        self._view.setPlainText(text)

    def clear(self):
        self._view.clear()
