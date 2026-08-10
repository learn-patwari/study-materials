import re
from datetime import datetime

import requests

from core.memory import SQLiteMemory
from utils.config import Settings
from utils.errors import AgentError, graceful


class ConfluenceAgent:
    def __init__(self, settings: Settings, memory: SQLiteMemory):
        if not all([settings.confluence_base_url, settings.confluence_username, settings.confluence_password]):
            raise AgentError(
                "Confluence not configured — set CONFLUENCE_BASE_URL, CONFLUENCE_USERNAME, CONFLUENCE_PASSWORD"
            )
        self._base = settings.confluence_base_url.rstrip("/") + "/wiki/rest/api"
        self._auth = (settings.confluence_username, settings.confluence_password)
        self._memory = memory
        self._session = requests.Session()
        self._session.auth = self._auth
        self._session.headers.update({"Accept": "application/json", "Content-Type": "application/json"})
        self._space_key: str | None = None

    @graceful("Confluence")
    def get_my_space(self) -> str:
        cached = self._memory.get("confluence.personal_space_key")
        if cached:
            self._space_key = cached
            return cached
        resp = self._session.get(f"{self._base}/space", params={"type": "personal", "limit": 10}, timeout=15)
        resp.raise_for_status()
        spaces = resp.json().get("results", [])
        if not spaces:
            raise AgentError("No personal Confluence space found for this user")
        key = spaces[0]["key"]
        self._space_key = key
        self._memory.set("confluence.personal_space_key", key, "confluence")
        return key

    @graceful("Confluence")
    def create_page(self, title: str, body_markdown: str) -> dict:
        run_id = self._memory.start_run("confluence")
        try:
            space_key = self._space_key or self.get_my_space()
            if isinstance(space_key, dict) and "error" in space_key:
                return space_key

            html_body = self._markdown_to_storage(body_markdown)
            payload = {
                "type": "page",
                "title": title,
                "space": {"key": space_key},
                "body": {"storage": {"value": html_body, "representation": "storage"}},
            }
            resp = self._session.post(f"{self._base}/content", json=payload, timeout=20)
            resp.raise_for_status()
            page = resp.json()
            page_id = page["id"]
            page_url = (
                self._base.replace("/wiki/rest/api", "")
                + page.get("_links", {}).get("webui", f"/wiki/spaces/{space_key}/pages/{page_id}")
            )
            result = {
                "page_id": page_id,
                "title": page["title"],
                "url": page_url,
                "space_key": space_key,
            }
            self._memory.set("confluence.last_page", result, "confluence")
            self._memory.end_run(run_id, "done", f"Created page '{title}'")
            return result
        except Exception as exc:
            self._memory.end_run(run_id, "error", str(exc))
            raise

    @graceful("Confluence")
    def list_my_pages(self, limit: int = 20) -> dict:
        space_key = self._space_key or self.get_my_space()
        if isinstance(space_key, dict) and "error" in space_key:
            return space_key
        resp = self._session.get(
            f"{self._base}/content",
            params={"type": "page", "spaceKey": space_key, "limit": limit, "orderby": "modified desc"},
            timeout=15,
        )
        resp.raise_for_status()
        pages = resp.json().get("results", [])
        return {
            "pages": [
                {
                    "id": p["id"],
                    "title": p["title"],
                    "url": self._base.replace("/wiki/rest/api", "") + p.get("_links", {}).get("webui", ""),
                }
                for p in pages
            ]
        }

    def _markdown_to_storage(self, md: str) -> str:
        html = md
        html = re.sub(r"^### (.+)$", r"<h3>\1</h3>", html, flags=re.MULTILINE)
        html = re.sub(r"^## (.+)$", r"<h2>\1</h2>", html, flags=re.MULTILINE)
        html = re.sub(r"^# (.+)$", r"<h1>\1</h1>", html, flags=re.MULTILINE)
        html = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", html)
        html = re.sub(r"\*(.+?)\*", r"<em>\1</em>", html)
        html = re.sub(r"^- (.+)$", r"<li>\1</li>", html, flags=re.MULTILINE)
        html = re.sub(r"(<li>.*</li>)", r"<ul>\1</ul>", html, flags=re.DOTALL)
        html = re.sub(r"```(.+?)```", r"<code>\1</code>", html, flags=re.DOTALL)
        html = re.sub(r"\n\n+", "</p><p>", html)
        html = f"<p>{html}</p>"
        return html
