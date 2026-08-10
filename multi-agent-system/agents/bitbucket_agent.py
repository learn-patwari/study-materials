from datetime import datetime
from typing import Optional

import requests

from core.memory import SQLiteMemory
from utils.config import Settings
from utils.errors import AgentError, graceful


class BitbucketAgent:
    def __init__(self, settings: Settings, memory: SQLiteMemory):
        if not all([settings.bitbucket_username, settings.bitbucket_app_password, settings.bitbucket_workspace]):
            raise AgentError(
                "Bitbucket not configured — set BITBUCKET_USERNAME, BITBUCKET_APP_PASSWORD, BITBUCKET_WORKSPACE"
            )
        self._base = settings.bitbucket_base_url.rstrip("/")
        self._auth = (settings.bitbucket_username, settings.bitbucket_app_password)
        self._workspace = settings.bitbucket_workspace
        self._repos = settings.bitbucket_repos
        self._memory = memory
        self._session = requests.Session()
        self._session.auth = self._auth
        self._session.headers.update({"Accept": "application/json"})

    @graceful("Bitbucket")
    def fetch_open_prs(self, repos: Optional[list] = None) -> dict:
        run_id = self._memory.start_run("bitbucket")
        try:
            repo_list = repos or self._repos
            by_repo = {}

            for repo in repo_list:
                resp = self._session.get(
                    f"{self._base}/repositories/{self._workspace}/{repo}/pullrequests",
                    params={"state": "OPEN", "pagelen": 50},
                    timeout=15,
                )
                if resp.status_code == 404:
                    by_repo[repo] = {"error": f"repo '{repo}' not found"}
                    continue
                resp.raise_for_status()
                prs = resp.json().get("values", [])

                me_resp = self._session.get(f"{self._base}/user", timeout=10)
                me_uuid = me_resp.json().get("uuid", "") if me_resp.ok else ""

                authored, review_requested = [], []
                for pr in prs:
                    entry = {
                        "id": pr["id"],
                        "title": pr["title"],
                        "repo": repo,
                        "branch": pr.get("source", {}).get("branch", {}).get("name", ""),
                        "target": pr.get("destination", {}).get("branch", {}).get("name", ""),
                        "reviewers": [r.get("display_name", "") for r in pr.get("reviewers", [])],
                        "status": pr.get("state", ""),
                        "url": pr.get("links", {}).get("html", {}).get("href", ""),
                        "updated": pr.get("updated_on", ""),
                    }
                    author_uuid = pr.get("author", {}).get("uuid", "")
                    reviewer_uuids = [r.get("uuid", "") for r in pr.get("reviewers", [])]
                    if author_uuid == me_uuid:
                        authored.append(entry)
                    elif me_uuid and me_uuid in reviewer_uuids:
                        review_requested.append(entry)

                by_repo[repo] = {"authored": authored, "review_requested": review_requested}

            result = {"by_repo": by_repo, "fetched_at": datetime.utcnow().isoformat()}
            self._memory.set("bitbucket.last_prs", result, "bitbucket")
            self._memory.end_run(run_id, "done", f"Fetched PRs for {len(repo_list)} repos")
            return result

        except Exception as exc:
            self._memory.end_run(run_id, "error", str(exc))
            raise

    @graceful("Bitbucket")
    def inspect_repo_for_bug(self, repo_slug: str, search_terms: list) -> dict:
        found_files = []
        terms_lower = [t.lower() for t in search_terms]

        def walk_dir(path: str, depth: int):
            if depth > 3 or len(found_files) >= 3:
                return
            resp = self._session.get(
                f"{self._base}/repositories/{self._workspace}/{repo_slug}/src/HEAD/{path}",
                timeout=15,
            )
            if not resp.ok:
                return
            data = resp.json()
            for entry in data.get("values", []):
                if len(found_files) >= 3:
                    break
                epath = entry.get("path", "")
                etype = entry.get("type", "")
                if etype == "commit_directory":
                    walk_dir(epath + "/", depth + 1)
                elif etype == "commit_file":
                    name_lower = epath.lower()
                    if any(t in name_lower for t in terms_lower):
                        file_resp = self._session.get(
                            f"{self._base}/repositories/{self._workspace}/{repo_slug}/src/HEAD/{epath}",
                            timeout=15,
                        )
                        if file_resp.ok:
                            lines = file_resp.text.splitlines()[:60]
                            found_files.append({
                                "path": epath,
                                "content_snippet": "\n".join(lines),
                                "url": f"https://bitbucket.org/{self._workspace}/{repo_slug}/src/HEAD/{epath}",
                            })

        walk_dir("", 0)
        return {
            "repo": repo_slug,
            "search_terms": search_terms,
            "found_files": found_files,
        }
