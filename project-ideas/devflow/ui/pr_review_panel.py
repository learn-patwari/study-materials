from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QListWidget, QListWidgetItem, QTextEdit, QSplitter, QScrollArea,
    QFrame, QCheckBox, QMessageBox
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from models import pull_request as pr_model
from services import ai_service, bitbucket_client


class _ReviewThread(QThread):
    done = pyqtSignal(list)
    error = pyqtSignal(str)

    def __init__(self, diff_text, pr_title):
        super().__init__()
        self._diff = diff_text
        self._title = pr_title

    def run(self):
        try:
            self.done.emit(ai_service.generate_pr_review(self._diff, self._title))
        except Exception as e:
            self.error.emit(str(e))


class _PostThread(QThread):
    done = pyqtSignal()
    error = pyqtSignal(str)

    def __init__(self, pr, comments):
        super().__init__()
        self._pr = pr
        self._comments = comments

    def run(self):
        try:
            for c in self._comments:
                bitbucket_client.post_pr_inline_comment(
                    self._pr.repo_slug, self._pr.pr_id,
                    c["file_path"], c["line_num"], c["comment"]
                )
                pr_model.mark_comment_posted(c["id"])
            pr_model.update_status(self._pr.id, "posted")
            self.done.emit()
        except Exception as e:
            self.error.emit(str(e))


class _CommentCard(QFrame):
    def __init__(self, comment: dict, parent=None):
        super().__init__(parent)
        self._comment = comment
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setStyleSheet("QFrame { background:#1a2133; border:1px solid #2a3a55; border-radius:4px; margin:2px; }")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 6, 8, 6)

        loc = QLabel(f"<b>{comment.get('file_path', '')}:{comment.get('line_num', '')}</b>")
        loc.setStyleSheet("color:#4a90d9;")
        layout.addWidget(loc)

        self._text = QTextEdit()
        self._text.setPlainText(comment.get("comment", ""))
        self._text.setMaximumHeight(80)
        layout.addWidget(self._text)

        btns = QHBoxLayout()
        self._approve_cb = QCheckBox("✓ Approve")
        self._approve_cb.setChecked(comment.get("approved", 0) == 1)
        self._approve_cb.stateChanged.connect(self._on_approve)
        dismiss_btn = QPushButton("✗ Dismiss")
        dismiss_btn.setObjectName("danger")
        dismiss_btn.setFixedWidth(80)
        dismiss_btn.clicked.connect(self._dismiss)
        btns.addWidget(self._approve_cb)
        btns.addStretch()
        btns.addWidget(dismiss_btn)
        layout.addLayout(btns)

    def _on_approve(self, state):
        approved = 1 if state == Qt.CheckState.Checked.value else 0
        pr_model.approve_comment(self._comment["id"], approved)

    def _dismiss(self):
        pr_model.approve_comment(self._comment["id"], -1)
        self.hide()

    def get_text(self):
        return self._text.toPlainText()


class PRReviewPanel(QWidget):
    badge_update = pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._current_pr = None
        self._comment_cards: list[_CommentCard] = []
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)

        top = QHBoxLayout()
        top.addWidget(QLabel("PR Review"))
        top.addStretch()
        self._badge_lbl = QLabel("")
        self._badge_lbl.setStyleSheet("color: #e05050; font-weight: bold;")
        top.addWidget(self._badge_lbl)
        layout.addLayout(top)

        splitter = QSplitter(Qt.Orientation.Horizontal)

        self._pr_list = QListWidget()
        self._pr_list.setMaximumWidth(280)
        self._pr_list.itemClicked.connect(self._on_pr_selected)
        splitter.addWidget(self._pr_list)

        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(8, 0, 0, 0)

        pr_hdr = QHBoxLayout()
        self._pr_title_lbl = QLabel("Select a PR")
        self._pr_title_lbl.setStyleSheet("font-weight: bold; font-size: 13px;")
        pr_hdr.addWidget(self._pr_title_lbl)
        pr_hdr.addStretch()
        gen_btn = QPushButton("⚡ Generate Review")
        gen_btn.clicked.connect(self._generate_review)
        pr_hdr.addWidget(gen_btn)
        right_layout.addLayout(pr_hdr)

        self._meta_lbl = QLabel("")
        self._meta_lbl.setStyleSheet("color: #8a9bb0;")
        right_layout.addWidget(self._meta_lbl)

        diff_lbl = QLabel("DIFF")
        diff_lbl.setStyleSheet("color:#8a9bb0; font-size:11px; margin-top:6px;")
        right_layout.addWidget(diff_lbl)

        self._diff_view = QTextEdit()
        self._diff_view.setReadOnly(True)
        self._diff_view.setMaximumHeight(200)
        self._diff_view.setStyleSheet("background:#0f1420; color:#e8ecf0; font-family:monospace; font-size:11px;")
        right_layout.addWidget(self._diff_view)

        comments_lbl = QLabel("REVIEW COMMENTS")
        comments_lbl.setStyleSheet("color:#8a9bb0; font-size:11px; margin-top:6px;")
        right_layout.addWidget(comments_lbl)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        self._comments_container = QWidget()
        self._comments_layout = QVBoxLayout(self._comments_container)
        self._comments_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self._comments_layout.setSpacing(4)
        scroll.setWidget(self._comments_container)
        right_layout.addWidget(scroll)

        self._status_lbl = QLabel("")
        self._status_lbl.setStyleSheet("color: #8a9bb0;")
        right_layout.addWidget(self._status_lbl)

        post_btn = QPushButton("📤 Post Approved Comments to Bitbucket")
        post_btn.setStyleSheet("background-color: #3ab06a; padding: 6px 16px;")
        post_btn.clicked.connect(self._post_approved)
        right_layout.addWidget(post_btn)

        splitter.addWidget(right)
        splitter.setSizes([280, 700])
        layout.addWidget(splitter)

    def showEvent(self, event):
        super().showEvent(event)
        self._refresh_list()

    def _refresh_list(self):
        self._pr_list.clear()
        prs = pr_model.get_all()
        new_count = sum(1 for p in prs if p.status == "new")
        self._badge_lbl.setText(f"🔔 {new_count} new" if new_count else "")
        self.badge_update.emit(new_count)

        current_repo = None
        for p in prs:
            if p.repo_slug != current_repo:
                header = QListWidgetItem(p.repo_slug)
                header.setFlags(Qt.ItemFlag.NoItemFlags)
                header.setForeground(Qt.GlobalColor.gray)
                self._pr_list.addItem(header)
                current_repo = p.repo_slug
            status_icon = {"new": "🔵", "reviewing": "🔵", "pending_approval": "🟡", "posted": "🟢", "dismissed": "⚫"}.get(p.status, "⚪")
            item = QListWidgetItem(f"  {status_icon} PR #{p.pr_id} — {p.title[:40]}")
            item.setData(Qt.ItemDataRole.UserRole, p)
            self._pr_list.addItem(item)

    def _on_pr_selected(self, item: QListWidgetItem):
        pr = item.data(Qt.ItemDataRole.UserRole)
        if not pr:
            return
        self._current_pr = pr
        self._pr_title_lbl.setText(f"PR #{pr.pr_id} — {pr.title}")
        self._meta_lbl.setText(f"{pr.repo_slug}  ·  by {pr.author}  ·  {pr.target_branch}←{pr.source_branch}")
        self._diff_view.setPlainText(pr.diff_text or "(no diff)")
        self._load_comments()
        if pr.status == "new":
            pr_model.update_status(pr.id, "reviewing")

    def _load_comments(self):
        for card in self._comment_cards:
            card.deleteLater()
        self._comment_cards.clear()

        if not self._current_pr:
            return
        comments = pr_model.get_comments(self._current_pr.id)
        for c in comments:
            if c.get("approved") == -1:
                continue
            card = _CommentCard(c)
            self._comments_layout.addWidget(card)
            self._comment_cards.append(card)

    def _generate_review(self):
        if not self._current_pr:
            return
        self._status_lbl.setText("Generating review...")
        self._review_thread = _ReviewThread(self._current_pr.diff_text or "", self._current_pr.title)
        self._review_thread.done.connect(self._on_review_done)
        self._review_thread.error.connect(lambda e: self._status_lbl.setText(f"Error: {e}"))
        self._review_thread.start()

    def _on_review_done(self, comments: list):
        self._status_lbl.setText(f"{len(comments)} review comments generated.")
        pr_model.save_comments(self._current_pr.id, comments)
        self._load_comments()

    def _post_approved(self):
        if not self._current_pr:
            return
        comments = pr_model.get_comments(self._current_pr.id)
        approved = [c for c in comments if c.get("approved") == 1]
        if not approved:
            QMessageBox.information(self, "Nothing to Post", "Approve at least one comment first.")
            return
        self._status_lbl.setText(f"Posting {len(approved)} comments...")
        self._post_thread = _PostThread(self._current_pr, approved)
        self._post_thread.done.connect(self._on_post_done)
        self._post_thread.error.connect(lambda e: self._status_lbl.setText(f"Error: {e}"))
        self._post_thread.start()

    def _on_post_done(self):
        self._status_lbl.setText("✓ Comments posted to Bitbucket.")
        self._refresh_list()
