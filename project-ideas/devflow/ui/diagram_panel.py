from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QFileDialog, QTextEdit, QApplication
)
from PyQt6.QtCore import Qt
from models import document as doc_model
from pathlib import Path


class DiagramPanel(QWidget):
    def __init__(self, ticket_id: int, parent=None):
        super().__init__(parent)
        self._ticket_id = ticket_id
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)

        top = QHBoxLayout()
        top.addWidget(QLabel("Architecture Diagram  (Mermaid source)"))
        top.addStretch()

        copy_btn = QPushButton("📋 Copy")
        copy_btn.setObjectName("secondary")
        copy_btn.setToolTip("Copy Mermaid source — paste at mermaid.live to visualise")
        copy_btn.clicked.connect(self._copy_source)
        top.addWidget(copy_btn)

        export_btn = QPushButton("💾 Export draw.io")
        export_btn.setObjectName("secondary")
        export_btn.clicked.connect(self._export_drawio)
        top.addWidget(export_btn)

        self._confluence_label = QLabel("")
        self._confluence_label.setStyleSheet("color: #4a90d9;")
        top.addWidget(self._confluence_label)
        layout.addLayout(top)

        self._hint = QLabel(
            '💡 Paste the source below at <a href="https://mermaid.live">mermaid.live</a> to see the rendered diagram.'
        )
        self._hint.setOpenExternalLinks(True)
        self._hint.setStyleSheet("color: #8a9bb0; font-size: 11px; padding: 4px 0;")
        layout.addWidget(self._hint)

        self._view = QTextEdit()
        self._view.setReadOnly(True)
        self._view.setStyleSheet(
            "background:#0d1218; color:#c9d1d9; font-family:Consolas,monospace; font-size:12px;"
            "border:1px solid #2a3a55; border-radius:4px; padding:8px;"
        )
        self._view.setPlaceholderText("No diagram generated yet — use the Description tab to generate content.")
        layout.addWidget(self._view)

    def load(self):
        diagram = doc_model.get_diagram(self._ticket_id)
        if not diagram or not diagram["mermaid_src"]:
            self._view.setPlainText("")
            return

        if diagram.get("confluence_page_url"):
            self._confluence_label.setText(f"🔗 {diagram['confluence_page_url']}")

        self._view.setPlainText(diagram["mermaid_src"])

    def showEvent(self, event):
        super().showEvent(event)
        self.load()

    def _copy_source(self):
        text = self._view.toPlainText()
        if text:
            QApplication.clipboard().setText(text)

    def _export_drawio(self):
        diagram = doc_model.get_diagram(self._ticket_id)
        if not diagram or not diagram["drawio_xml"]:
            return
        path, _ = QFileDialog.getSaveFileName(self, "Export draw.io", "", "draw.io files (*.drawio *.xml)")
        if path:
            Path(path).write_text(diagram["drawio_xml"])
