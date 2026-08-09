from PyQt6.QtWidgets import (
    QDialog, QHBoxLayout, QVBoxLayout, QListWidget, QStackedWidget,
    QLabel, QLineEdit, QTextEdit, QPushButton, QFormLayout, QComboBox,
    QSpinBox, QTimeEdit, QWidget, QMessageBox
)
from PyQt6.QtCore import Qt, QTime
from db import database as db
from services import jira_client


class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.setMinimumSize(720, 560)
        self._build_ui()
        self._load()

    def _build_ui(self):
        root = QHBoxLayout(self)
        self.nav = QListWidget()
        self.nav.setFixedWidth(160)
        sections = ["Jira", "Confluence", "Bitbucket", "AI", "Document", "Sprint", "Test Runner", "PR Watcher"]
        for s in sections:
            self.nav.addItem(s)
        self.nav.currentRowChanged.connect(self._switch)
        root.addWidget(self.nav)

        right = QVBoxLayout()
        self.stack = QStackedWidget()
        right.addWidget(self.stack)

        btns = QHBoxLayout()
        btns.addStretch()
        cancel = QPushButton("Cancel"); cancel.setObjectName("secondary"); cancel.clicked.connect(self.reject)
        save = QPushButton("💾 Save"); save.clicked.connect(self._save)
        btns.addWidget(cancel); btns.addWidget(save)
        right.addLayout(btns)
        root.addLayout(right)

        self.stack.addWidget(self._jira_page())
        self.stack.addWidget(self._simple_page("Confluence", [
            ("confluence_url", "Confluence URL"), ("confluence_token", "Token (masked)", True),
            ("confluence_parent_page_id", "Parent Page ID"), ("confluence_space_key", "Space Key"),
        ]))
        self.stack.addWidget(self._simple_page("Bitbucket", [
            ("bitbucket_url", "Bitbucket URL"), ("bitbucket_token", "Token (masked)", True),
            ("jira_board_id", "Jira Board ID (for sprint)"),
        ]))
        self.stack.addWidget(self._ai_page())
        self.stack.addWidget(self._doc_page())
        self.stack.addWidget(self._sprint_page())
        self.stack.addWidget(self._simple_page("Test Runner", [
            ("test_run_command", "Test run command (e.g. coverage run -m pytest && coverage report)"),
        ]))
        self.stack.addWidget(self._pr_watcher_page())
        self.nav.setCurrentRow(0)

    def _switch(self, idx):
        self.stack.setCurrentIndex(idx)

    # ── pages ──────────────────────────────────────────────────────────────

    def _jira_page(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        form = QFormLayout()
        self._fields = getattr(self, "_fields", {})

        self._fields["jira_url"] = QLineEdit()
        form.addRow("Jira URL:", self._fields["jira_url"])
        self._fields["jira_token"] = QLineEdit(); self._fields["jira_token"].setEchoMode(QLineEdit.EchoMode.Password)
        form.addRow("Token:", self._fields["jira_token"])
        layout.addLayout(form)

        proj_row = QHBoxLayout()
        self._fields["jira_default_project"] = QComboBox()
        load_proj = QPushButton("🔄 Load Projects"); load_proj.setObjectName("secondary")
        load_proj.clicked.connect(self._load_projects)
        proj_row.addWidget(QLabel("Default Project:")); proj_row.addWidget(self._fields["jira_default_project"])
        proj_row.addWidget(load_proj)
        layout.addLayout(proj_row)

        type_row = QHBoxLayout()
        load_types = QPushButton("🔄 Load Issue Types"); load_types.setObjectName("secondary")
        load_types.clicked.connect(self._load_issue_types)
        type_row.addWidget(load_types); type_row.addStretch()
        layout.addLayout(type_row)

        type_form = QFormLayout()
        for key, label in [("jira_issue_type_srs", "SRS type"), ("jira_issue_type_sad", "SAD/Arch type"),
                            ("jira_issue_type_bug", "Bug type"), ("jira_issue_type_improvement", "Improvement type")]:
            self._fields[key] = QComboBox(); self._fields[key].setEditable(True)
            type_form.addRow(f"{label}:", self._fields[key])
        layout.addLayout(type_form)
        layout.addStretch()
        return w

    def _simple_page(self, title: str, fields: list) -> QWidget:
        w = QWidget(); form = QFormLayout(w)
        self._fields = getattr(self, "_fields", {})
        for item in fields:
            key, label = item[0], item[1]
            masked = len(item) > 2 and item[2]
            le = QLineEdit()
            if masked:
                le.setEchoMode(QLineEdit.EchoMode.Password)
            self._fields[key] = le
            form.addRow(f"{label}:", le)
        return w

    def _ai_page(self) -> QWidget:
        w = QWidget(); form = QFormLayout(w)
        self._fields = getattr(self, "_fields", {})
        for key, label, masked in [
            ("ai_base_url", "Base URL", False),
            ("ai_api_key", "API Key", True),
            ("ai_model", "Model (e.g. gpt-4o)", False),
        ]:
            le = QLineEdit()
            if masked: le.setEchoMode(QLineEdit.EchoMode.Password)
            self._fields[key] = le
            form.addRow(f"{label}:", le)
        return w

    def _doc_page(self) -> QWidget:
        w = QWidget(); layout = QVBoxLayout(w)
        layout.addWidget(QLabel("Jira description template (AI will fill each section):"))
        self._fields = getattr(self, "_fields", {})
        self._fields["doc_template"] = QTextEdit()
        self._fields["doc_template"].setPlaceholderText("## Background\n\n## Scope\n\n## Acceptance Criteria\n\n## Dependencies")
        layout.addWidget(self._fields["doc_template"])
        return w

    def _sprint_page(self) -> QWidget:
        w = QWidget(); form = QFormLayout(w)
        self._fields = getattr(self, "_fields", {})
        self._fields["sprint_dev_days"] = QSpinBox(); self._fields["sprint_dev_days"].setRange(1, 30); self._fields["sprint_dev_days"].setValue(8)
        self._fields["sprint_test_days"] = QSpinBox(); self._fields["sprint_test_days"].setRange(1, 30); self._fields["sprint_test_days"].setValue(2)
        self._fields["task_auto_close_time"] = QTimeEdit(); self._fields["task_auto_close_time"].setDisplayFormat("HH:mm")
        form.addRow("Dev days per sprint:", self._fields["sprint_dev_days"])
        form.addRow("Test days per sprint:", self._fields["sprint_test_days"])
        form.addRow("Auto-close overdue at:", self._fields["task_auto_close_time"])
        return w

    def _pr_watcher_page(self) -> QWidget:
        w = QWidget(); layout = QVBoxLayout(w)
        self._fields = getattr(self, "_fields", {})
        layout.addWidget(QLabel("Watched repos (one PROJECT/repo per line):"))
        self._fields["pr_watch_repos_text"] = QTextEdit()
        layout.addWidget(self._fields["pr_watch_repos_text"])
        form = QFormLayout()
        self._fields["pr_poll_interval_secs"] = QSpinBox(); self._fields["pr_poll_interval_secs"].setRange(30, 3600); self._fields["pr_poll_interval_secs"].setValue(120)
        form.addRow("Poll interval (seconds):", self._fields["pr_poll_interval_secs"])
        layout.addLayout(form)
        return w

    # ── load / save ────────────────────────────────────────────────────────

    def _load(self):
        self._fields = getattr(self, "_fields", {})
        s = db.get_all_settings()
        simple_keys = ["jira_url", "confluence_url", "confluence_parent_page_id", "confluence_space_key",
                       "bitbucket_url", "jira_board_id", "ai_base_url", "ai_model",
                       "test_run_command"]
        masked_keys = ["jira_token", "confluence_token", "bitbucket_token", "ai_api_key"]
        for key in simple_keys + masked_keys:
            if key in self._fields:
                self._fields[key].setText(s.get(key, ""))

        combo_keys = ["jira_issue_type_srs", "jira_issue_type_sad", "jira_issue_type_bug", "jira_issue_type_improvement"]
        defaults = {"jira_issue_type_srs": "Story", "jira_issue_type_sad": "SAD", "jira_issue_type_bug": "Bug", "jira_issue_type_improvement": "Improvement"}
        for key in combo_keys:
            if key in self._fields:
                val = s.get(key, defaults.get(key, ""))
                cb: QComboBox = self._fields[key]
                if cb.findText(val) < 0:
                    cb.addItem(val)
                cb.setCurrentText(val)

        proj = s.get("jira_default_project", "")
        if proj and "jira_default_project" in self._fields:
            cb = self._fields["jira_default_project"]
            if cb.findText(proj) < 0:
                cb.addItem(proj)
            cb.setCurrentText(proj)

        if "doc_template" in self._fields:
            self._fields["doc_template"].setPlainText(s.get("doc_template", "## Background\n\n## Scope\n\n## Acceptance Criteria\n\n## Dependencies"))

        if "sprint_dev_days" in self._fields:
            self._fields["sprint_dev_days"].setValue(int(s.get("sprint_dev_days", "8")))
            self._fields["sprint_test_days"].setValue(int(s.get("sprint_test_days", "2")))

        if "task_auto_close_time" in self._fields:
            t = s.get("task_auto_close_time", "23:59").split(":")
            self._fields["task_auto_close_time"].setTime(QTime(int(t[0]), int(t[1])))

        if "pr_watch_repos_text" in self._fields:
            import json
            repos = s.get("pr_watch_repos", "[]")
            try:
                self._fields["pr_watch_repos_text"].setPlainText("\n".join(json.loads(repos)))
            except Exception:
                self._fields["pr_watch_repos_text"].setPlainText(repos)

        if "pr_poll_interval_secs" in self._fields:
            self._fields["pr_poll_interval_secs"].setValue(int(s.get("pr_poll_interval_secs", "120")))

    def _save(self):
        import json
        for key in ["jira_url", "jira_token", "confluence_url", "confluence_token",
                    "confluence_parent_page_id", "confluence_space_key",
                    "bitbucket_url", "bitbucket_token", "jira_board_id",
                    "ai_base_url", "ai_api_key", "ai_model", "test_run_command"]:
            if key in self._fields:
                db.set_setting(key, self._fields[key].text().strip())

        for key in ["jira_issue_type_srs", "jira_issue_type_sad", "jira_issue_type_bug", "jira_issue_type_improvement"]:
            if key in self._fields:
                db.set_setting(key, self._fields[key].currentText().strip())

        if "jira_default_project" in self._fields:
            db.set_setting("jira_default_project", self._fields["jira_default_project"].currentText().strip())

        if "doc_template" in self._fields:
            db.set_setting("doc_template", self._fields["doc_template"].toPlainText())

        if "sprint_dev_days" in self._fields:
            db.set_setting("sprint_dev_days", str(self._fields["sprint_dev_days"].value()))
            db.set_setting("sprint_test_days", str(self._fields["sprint_test_days"].value()))

        if "task_auto_close_time" in self._fields:
            db.set_setting("task_auto_close_time", self._fields["task_auto_close_time"].time().toString("HH:mm"))

        if "pr_watch_repos_text" in self._fields:
            repos = [r.strip() for r in self._fields["pr_watch_repos_text"].toPlainText().splitlines() if r.strip()]
            db.set_setting("pr_watch_repos", json.dumps(repos))
            db.set_setting("pr_poll_interval_secs", str(self._fields["pr_poll_interval_secs"].value()))

        self.accept()

    def _load_projects(self):
        try:
            projects = jira_client.fetch_projects()
            cb: QComboBox = self._fields["jira_default_project"]
            cb.clear()
            for p in projects:
                cb.addItem(f"{p['key']} — {p['name']}", p["key"])
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Could not load projects: {e}")

    def _load_issue_types(self):
        try:
            types = jira_client.fetch_issue_types()
            for key in ["jira_issue_type_srs", "jira_issue_type_sad", "jira_issue_type_bug", "jira_issue_type_improvement"]:
                cb: QComboBox = self._fields[key]
                current = cb.currentText()
                cb.clear()
                for t in types:
                    cb.addItem(t["name"])
                if current:
                    idx = cb.findText(current)
                    if idx >= 0:
                        cb.setCurrentIndex(idx)
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Could not load issue types: {e}")
