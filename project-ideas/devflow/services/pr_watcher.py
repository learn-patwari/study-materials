import json
from PyQt6.QtCore import QTimer, QObject, pyqtSignal
from db import database as db
from models import pull_request as pr_model
from services import bitbucket_client


class PRWatcher(QObject):
    new_pr_detected = pyqtSignal(dict)  # emits PR dict

    def __init__(self, parent=None):
        super().__init__(parent)
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._poll)

    def start(self):
        interval = int(db.get_setting("pr_poll_interval_secs", "120")) * 1000
        self._timer.start(interval)

    def stop(self):
        self._timer.stop()

    def _poll(self):
        repos_json = db.get_setting("pr_watch_repos", "[]")
        try:
            repos = json.loads(repos_json)
        except Exception:
            repos = [r.strip() for r in repos_json.splitlines() if r.strip()]

        known_ids = {(pr.repo_slug, pr.pr_id) for pr in pr_model.get_all()}

        for repo_slug in repos:
            try:
                open_prs = bitbucket_client.list_open_prs(repo_slug)
            except Exception:
                continue
            for pr_data in open_prs:
                key = (repo_slug, pr_data["id"])
                if key in known_ids:
                    continue
                # Fetch diff
                try:
                    diff = bitbucket_client.get_pr_diff(repo_slug, pr_data["id"])
                except Exception:
                    diff = ""
                pr = pr_model.PullRequest(
                    id=None, repo_slug=repo_slug, pr_id=pr_data["id"],
                    title=pr_data["title"], author=pr_data["author"],
                    source_branch=pr_data["source_branch"], target_branch=pr_data["target_branch"],
                    pr_url=pr_data["links"], diff_text=diff,
                )
                db_id = pr_model.save(pr)
                self.new_pr_detected.emit({"db_id": db_id, "repo": repo_slug, **pr_data})
