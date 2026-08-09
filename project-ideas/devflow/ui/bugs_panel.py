from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QListWidget, QListWidgetItem, QTextEdit, QSplitter, QFileDialog,
    QScrollArea, QFrame, QMessageBox
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from services import jira_client, ai_service, code_reader, test_runner, code_editor
from models import ticket as ticket_model
from db import database as db
import json


class _FetchThread(QThread):
    done = pyqtSignal(list)
    error = pyqtSignal(str)

    def __init__(self, mode: str):
        super().__init__()
        self._mode = mode

    def run(self):
        try:
            if self._mode == "improvements":
                items = jira_client.fetch_improvements()
            else:
                items = jira_client.fetch_bugs()
            self.done.emit(items)
        except Exception as e:
            self.error.emit(str(e))


class _AnalyseThread(QThread):
    done = pyqtSignal(dict)
    error = pyqtSignal(str)

    def __init__(self, description, codebase_path):
        super().__init__()
        self._desc = description
        self._path = codebase_path

    def run(self):
        try:
            summary = code_reader.ingest("local", self._path)
            result = ai_service.analyze_bug(self._desc, summary)
            self.done.emit(result)
        except Exception as e:
            self.error.emit(str(e))


class _SafetyThread(QThread):
    done = pyqtSignal(dict, list)
    error = pyqtSignal(str)

    def __init__(self, fix_plan, codebase_path):
        super().__init__()
        self._fix_plan = fix_plan
        self._path = codebase_path

    def run(self):
        try:
            baseline = test_runner.run_tests()
            related = [f["file"] for f in self._fix_plan if "file" in f]
            impacts = ai_service.predict_test_impact(self._fix_plan, related, self._path)
            self.done.emit(baseline, impacts)
        except Exception as e:
            self.error.emit(str(e))


class _ApplyThread(QThread):
    done = pyqtSignal(dict)
    error = pyqtSignal(str)

    def __init__(self, fix_plan, codebase_path):
        super().__init__()
        self._fix_plan = fix_plan
        self._path = codebase_path

    def run(self):
        try:
            files = [f["file"] for f in self._fix_plan if "file" in f]
            backup_dir = code_editor.backup_files(files, self._path)
            code_editor.apply_fix(self._fix_plan, self._path)
            result = test_runner.run_tests()
            result["backup_dir"] = backup_dir
            self.done.emit(result)
        except Exception as e:
            self.error.emit(str(e))


class BugsPanel(QWidget):
    def __init__(self, mode: str = "bugs", parent=None):
        super().__init__(parent)
        self._mode = mode  # "bugs" or "improvements"
        self._current_item = None
        self._analysis = None
        self._codebase_path = ""
        self._fix_plan = []
        self._backup_dir = None
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 6, 12, 12)
        layout.setSpacing(6)

        top = QHBoxLayout()
        top.addStretch()
        refresh_btn = QPushButton("🔄 Refresh")
        refresh_btn.clicked.connect(self._fetch)
        top.addWidget(refresh_btn)
        layout.addLayout(top)

        splitter = QSplitter(Qt.Orientation.Horizontal)

        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(0, 0, 0, 0)

        self._item_list = QListWidget()
        self._item_list.itemClicked.connect(self._on_item_selected)
        left_layout.addWidget(self._item_list)
        left.setMaximumWidth(280)
        splitter.addWidget(left)

        right = QWidget()
        self._right_layout = QVBoxLayout(right)
        self._right_layout.setContentsMargins(8, 0, 0, 0)
        self._right_layout.setSpacing(6)

        self._title_lbl = QLabel("Select a ticket")
        self._title_lbl.setStyleSheet("font-weight: bold; font-size: 13px;")
        self._right_layout.addWidget(self._title_lbl)

        desc_lbl = QLabel("Jira Description:")
        desc_lbl.setStyleSheet("color:#8a9bb0; font-size:11px;")
        self._right_layout.addWidget(desc_lbl)

        self._desc_view = QTextEdit()
        self._desc_view.setReadOnly(True)
        self._desc_view.setMaximumHeight(100)
        self._right_layout.addWidget(self._desc_view)

        code_row = QHBoxLayout()
        code_lbl = QLabel("Codebase:")
        code_lbl.setStyleSheet("color:#8a9bb0;")
        self._code_path_lbl = QLabel("(not set)")
        self._code_path_lbl.setStyleSheet("color:#e8ecf0;")
        browse_btn = QPushButton("📁")
        browse_btn.setFixedWidth(32)
        browse_btn.clicked.connect(self._browse_codebase)
        code_row.addWidget(code_lbl)
        code_row.addWidget(self._code_path_lbl, 1)
        code_row.addWidget(browse_btn)
        self._right_layout.addLayout(code_row)

        self._analyse_btn = QPushButton("🔍 Analyse Bug")
        self._analyse_btn.clicked.connect(self._analyse)
        self._right_layout.addWidget(self._analyse_btn)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        self._analysis_widget = QWidget()
        self._analysis_layout = QVBoxLayout(self._analysis_widget)
        self._analysis_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        scroll.setWidget(self._analysis_widget)
        self._right_layout.addWidget(scroll)

        self._status_lbl = QLabel("")
        self._status_lbl.setStyleSheet("color:#8a9bb0;")
        self._right_layout.addWidget(self._status_lbl)

        splitter.addWidget(right)
        splitter.setSizes([280, 700])
        layout.addWidget(splitter)

    def showEvent(self, event):
        super().showEvent(event)
        self._fetch()

    def _fetch(self):
        self._status_lbl.setText("Fetching from Jira...")
        self._fetcher = _FetchThread(self._mode)
        self._fetcher.done.connect(self._on_fetched)
        self._fetcher.error.connect(self._on_fetch_error)
        self._fetcher.start()

    def _on_fetched(self, items: list):
        self._status_lbl.setText("")
        self._item_list.clear()
        icon = "🔴" if self._mode == "bugs" else "🟡"
        for b in items:
            item = QListWidgetItem(f"{icon} {b['key']}  {b['summary'][:50]}")
            item.setData(Qt.ItemDataRole.UserRole, b)
            self._item_list.addItem(item)

    def _on_fetch_error(self, msg: str):
        self._load_from_db()

    def _load_from_db(self):
        from db import database as db
        rows = db.fetchall("SELECT jira_key, title, description, root_cause, fix_plan_json, status FROM bug_analyses ORDER BY id DESC")
        self._item_list.clear()
        icon = "🔴" if self._mode == "bugs" else "🟡"
        for r in rows:
            item = QListWidgetItem(f"{icon} {r['jira_key']}  {r['title'][:50]}")
            item.setData(Qt.ItemDataRole.UserRole, {
                "key": r["jira_key"], "summary": r["title"],
                "description": r["description"] or "",
            })
            self._item_list.addItem(item)
        self._status_lbl.setText("(loaded from local cache — Jira unavailable)")

    def _on_item_selected(self, item: QListWidgetItem):
        data = item.data(Qt.ItemDataRole.UserRole)
        if not data:
            return
        self._current_item = data
        self._analysis = None
        self._fix_plan = []
        self._title_lbl.setText(f"{data['key']} — {data['summary']}")
        self._desc_view.setPlainText(data.get("description", ""))
        self._clear_analysis()

    def _browse_codebase(self):
        folder = QFileDialog.getExistingDirectory(self, "Choose codebase folder")
        if folder:
            self._codebase_path = folder
            self._code_path_lbl.setText(folder)

    def _analyse(self):
        if not self._current_item:
            return
        if not self._codebase_path:
            QMessageBox.warning(self, "No Codebase", "Choose a codebase folder first.")
            return
        self._status_lbl.setText("Analysing...")
        self._clear_analysis()
        desc = self._current_item.get("description", "") or self._current_item.get("summary", "")
        self._analyse_thread = _AnalyseThread(desc, self._codebase_path)
        self._analyse_thread.done.connect(self._on_analysis_done)
        self._analyse_thread.error.connect(lambda e: self._status_lbl.setText(f"Error: {e}"))
        self._analyse_thread.start()

    def _on_analysis_done(self, result: dict):
        self._status_lbl.setText("")
        self._analysis = result
        self._fix_plan = result.get("fix_plan", [])

        self._add_section("ROOT CAUSE", result.get("root_cause", "(none)"))

        affected = result.get("affected_files", [])
        if affected:
            text = "\n".join(f"• {f.get('file','?')}:{f.get('lines','?')}  {f.get('reason','')}" for f in affected)
            self._add_section("AFFECTED FILES", text)

        if self._fix_plan:
            plan_text = "\n".join(f"{i+1}. {p.get('file','?')}\n   {p.get('change','')}" for i, p in enumerate(self._fix_plan))
            self._add_section("FIX PLAN", plan_text)

        safety_btn = QPushButton("⚠ Check Test Safety")
        safety_btn.setObjectName("secondary")
        safety_btn.clicked.connect(self._check_safety)
        self._analysis_layout.addWidget(safety_btn)

    def _check_safety(self):
        if not self._fix_plan:
            return
        self._status_lbl.setText("Running test baseline + predicting impact...")
        self._safety_thread = _SafetyThread(self._fix_plan, self._codebase_path)
        self._safety_thread.done.connect(self._on_safety_done)
        self._safety_thread.error.connect(lambda e: self._status_lbl.setText(f"Error: {e}"))
        self._safety_thread.start()

    def _on_safety_done(self, baseline: dict, impacts: list):
        self._status_lbl.setText(f"Baseline: {baseline.get('passed',0)} passed / {baseline.get('failed',0)} failed")
        at_risk = [i for i in impacts if i.get("risk") == "may_fail"]
        if at_risk:
            warn_text = "\n".join(f"⚠ {i.get('test_file','')}::{i.get('test_name','')}  — {i.get('reason','')}" for i in at_risk)
            self._add_section("⚠ TEST SAFETY WARNING", warn_text, color="#f0a030")

        confirm_btn = QPushButton("✅ Confirm & Apply Fix")
        confirm_btn.setStyleSheet("background-color: #3ab06a; padding: 6px 16px;")
        confirm_btn.clicked.connect(self._confirm_apply)
        self._analysis_layout.addWidget(confirm_btn)

    def _confirm_apply(self):
        if not self._fix_plan:
            return
        reply = QMessageBox.question(self, "Apply Fix", "Apply the fix plan to the codebase?",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply != QMessageBox.StandardButton.Yes:
            return
        self._status_lbl.setText("Applying fix and running tests...")
        self._apply_thread = _ApplyThread(self._fix_plan, self._codebase_path)
        self._apply_thread.done.connect(self._on_applied)
        self._apply_thread.error.connect(lambda e: self._status_lbl.setText(f"Error: {e}"))
        self._apply_thread.start()

    def _on_applied(self, result: dict):
        self._backup_dir = result.get("backup_dir")
        failed = result.get("failed", 0)
        passed = result.get("passed", 0)
        if failed:
            msg = f"Fix applied but {failed} test(s) failed."
            self._status_lbl.setText(msg)
            revert_btn = QPushButton("↩ Revert Changes")
            revert_btn.setObjectName("danger")
            revert_btn.clicked.connect(self._revert)
            self._analysis_layout.addWidget(revert_btn)
            QMessageBox.warning(self, "Tests Failed", msg + "\nYou can revert the changes.")
        else:
            self._status_lbl.setText(f"✓ Fix applied, all {passed} tests green.")
            QMessageBox.information(self, "Success", f"Fix applied. {passed} tests passed.")

    def _revert(self):
        if not self._backup_dir:
            return
        try:
            code_editor.revert(self._backup_dir, self._codebase_path)
            self._status_lbl.setText("Changes reverted.")
            QMessageBox.information(self, "Reverted", "Codebase restored from backup.")
        except Exception as e:
            QMessageBox.critical(self, "Revert Error", str(e))

    def _add_section(self, title: str, text: str, color: str = None):
        lbl = QLabel(title)
        lbl.setStyleSheet(f"color:{'#8a9bb0' if not color else color}; font-size:11px; font-weight:bold; margin-top:8px;")
        self._analysis_layout.addWidget(lbl)
        box = QTextEdit()
        box.setPlainText(text)
        box.setReadOnly(True)
        box.setMaximumHeight(100)
        self._analysis_layout.addWidget(box)

    def _clear_analysis(self):
        while self._analysis_layout.count():
            item = self._analysis_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
