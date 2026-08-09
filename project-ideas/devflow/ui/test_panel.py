from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QListWidget, QListWidgetItem, QTextEdit, QSplitter, QFileDialog, QMessageBox
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from pathlib import Path
from models import document as doc_model
from services import test_runner


class _RunnerThread(QThread):
    done = pyqtSignal(dict)

    def run(self):
        self.done.emit(test_runner.run_tests())


class TestPanel(QWidget):
    def __init__(self, ticket_id: int, parent=None):
        super().__init__(parent)
        self._ticket_id = ticket_id
        self._files: list[dict] = []
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)

        top = QHBoxLayout()
        self._count_lbl = QLabel("Test Files  🔢 0 files")
        self._count_lbl.setStyleSheet("font-weight: bold;")
        top.addWidget(self._count_lbl)
        top.addStretch()
        run_btn = QPushButton("▶ Run Coverage")
        run_btn.setObjectName("secondary")
        run_btn.clicked.connect(self._run_coverage)
        self._cov_lbl = QLabel("")
        self._cov_lbl.setStyleSheet("color: #3ab06a;")
        save_all_btn = QPushButton("💾 Save All")
        save_all_btn.clicked.connect(self._save_all)
        top.addWidget(run_btn); top.addWidget(self._cov_lbl); top.addWidget(save_all_btn)
        layout.addLayout(top)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        self._list = QListWidget()
        self._list.itemClicked.connect(self._on_select)
        splitter.addWidget(self._list)

        self._preview = QTextEdit()
        self._preview.setReadOnly(True)
        self._preview.setPlaceholderText("Select a file to preview...")
        splitter.addWidget(self._preview)
        splitter.setSizes([220, 600])
        layout.addWidget(splitter)

    def load(self):
        self._files = doc_model.get_test_files(self._ticket_id)
        self._list.clear()
        for f in self._files:
            item = QListWidgetItem(f["filename"])
            item.setData(Qt.ItemDataRole.UserRole, f)
            self._list.addItem(item)
        self._count_lbl.setText(f"Test Files  🔢 {len(self._files)} files")

    def showEvent(self, event):
        super().showEvent(event)
        self.load()

    def _on_select(self, item: QListWidgetItem):
        f = item.data(Qt.ItemDataRole.UserRole)
        self._preview.setPlainText(f.get("content", ""))

    def _run_coverage(self):
        self._cov_lbl.setText("Running...")
        self._runner = _RunnerThread()
        self._runner.done.connect(self._on_coverage_done)
        self._runner.start()

    def _on_coverage_done(self, result: dict):
        if result.get("error"):
            self._cov_lbl.setText(f"Error: {result['error']}")
            return
        cov = result.get("coverage_pct")
        passed, failed = result.get("passed", 0), result.get("failed", 0)
        text = f"✓ {passed} passed"
        if failed:
            text += f"  ✗ {failed} failed"
        if cov is not None:
            text += f"  Coverage: {cov:.0f}%"
        self._cov_lbl.setText(text)

    def _save_all(self):
        if not self._files:
            return
        folder = QFileDialog.getExistingDirectory(self, "Choose output folder")
        if not folder:
            return
        for f in self._files:
            out = Path(folder) / f["filename"]
            out.write_text(f.get("content", ""))
        QMessageBox.information(self, "Saved", f"Saved {len(self._files)} files to {folder}")
