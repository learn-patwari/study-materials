from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QFileDialog
from PyQt6.QtCore import QUrl
from models import document as doc_model
from pathlib import Path
import tempfile
import os


MERMAID_HTML = """<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>body{{ background:#0f1420; color:#e8ecf0; margin:0; padding:16px; }}</style>
<script>{mermaid_js}</script>
</head>
<body>
<div class="mermaid">
{diagram}
</div>
<script>mermaid.initialize({{ startOnLoad:true, theme:'dark' }});</script>
</body>
</html>"""


class DiagramPanel(QWidget):
    def __init__(self, ticket_id: int, parent=None):
        super().__init__(parent)
        self._ticket_id = ticket_id
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)

        top = QHBoxLayout()
        top.addWidget(QLabel("Architecture Diagram"))
        top.addStretch()
        export_btn = QPushButton("💾 Export draw.io")
        export_btn.setObjectName("secondary")
        export_btn.clicked.connect(self._export_drawio)
        top.addWidget(export_btn)
        self._confluence_label = QLabel("")
        self._confluence_label.setStyleSheet("color: #4a90d9;")
        top.addWidget(self._confluence_label)
        layout.addLayout(top)

        from PyQt6.QtWebEngineWidgets import QWebEngineView
        self._view = QWebEngineView()
        layout.addWidget(self._view)

    def load(self):
        diagram = doc_model.get_diagram(self._ticket_id)
        if not diagram or not diagram["mermaid_src"]:
            self._view.setHtml("<body style='background:#0f1420;color:#8a9bb0;padding:20px'>No diagram generated yet.</body>")
            return

        if diagram.get("confluence_page_url"):
            self._confluence_label.setText(f"🔗 Confluence: {diagram['confluence_page_url']}")

        mermaid_js_path = Path(__file__).parent.parent / "assets" / "mermaid.min.js"
        if mermaid_js_path.exists():
            mermaid_js = mermaid_js_path.read_text()
        else:
            mermaid_js = "// mermaid.js not found"

        html = MERMAID_HTML.format(mermaid_js=mermaid_js, diagram=diagram["mermaid_src"])
        self._view.setHtml(html)

    def showEvent(self, event):
        super().showEvent(event)
        self.load()

    def _export_drawio(self):
        diagram = doc_model.get_diagram(self._ticket_id)
        if not diagram or not diagram["drawio_xml"]:
            return
        path, _ = QFileDialog.getSaveFileName(self, "Export draw.io", "", "draw.io files (*.drawio *.xml)")
        if path:
            Path(path).write_text(diagram["drawio_xml"])
