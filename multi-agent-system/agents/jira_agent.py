from datetime import datetime
from typing import Optional

import requests

from core.memory import SQLiteMemory
from utils.config import Settings
from utils.errors import AgentError, graceful


class JiraAgent:
    def __init__(self, settings: Settings, memory: SQLiteMemory):
        if not all([settings.jira_base_url, settings.jira_user_email, settings.jira_api_token]):
            raise AgentError("Jira not configured — set JIRA_BASE_URL, JIRA_USER_EMAIL, JIRA_API_TOKEN")
        self._base = settings.jira_base_url.rstrip("/")
        self._auth = (settings.jira_user_email, settings.jira_api_token)
        self._project = settings.jira_project_key
        self._memory = memory
        self._session = requests.Session()
        self._session.auth = self._auth
        self._session.headers.update({"Accept": "application/json"})

    @graceful("Jira")
    def fetch_my_tickets(self) -> dict:
        run_id = self._memory.start_run("jira")
        try:
            jql = "assignee = currentUser() AND statusCategory != Done ORDER BY priority ASC, updated DESC"
            if self._project:
                keys = [k.strip() for k in self._project.split(",") if k.strip()]
                if keys:
                    proj_filter = " OR ".join(f'project = "{k}"' for k in keys)
                    jql = f"({proj_filter}) AND {jql}"

            resp = self._session.get(
                f"{self._base}/rest/api/3/search",
                params={"jql": jql, "maxResults": 50, "fields": "summary,issuetype,priority,status,updated,components,labels,description"},
                timeout=15,
            )
            resp.raise_for_status()
            data = resp.json()

            tasks = []
            for issue in data.get("issues", []):
                f = issue["fields"]
                desc = self._extract_description(f.get("description"))
                tasks.append({
                    "key": issue["key"],
                    "summary": f.get("summary", ""),
                    "type": f.get("issuetype", {}).get("name", ""),
                    "priority": f.get("priority", {}).get("name", "Medium"),
                    "status": f.get("status", {}).get("name", ""),
                    "updated": f.get("updated", ""),
                    "components": [c["name"] for c in f.get("components", [])],
                    "labels": f.get("labels", []),
                    "description_snippet": desc[:300] if desc else "",
                    "url": f"{self._base}/browse/{issue['key']}",
                })

            bug_tickets = [t for t in tasks if t["type"].lower() == "bug"]
            result = {
                "total": len(tasks),
                "tasks": tasks,
                "bug_tickets": bug_tickets,
                "fetched_at": datetime.utcnow().isoformat(),
            }

            self._memory.set("jira.last_tickets", result, "jira")
            self._memory.set("jira.last_fetch", datetime.utcnow().isoformat(), "jira")
            self._memory.end_run(run_id, "done", f"Fetched {len(tasks)} tickets ({len(bug_tickets)} bugs)")
            return result

        except Exception as exc:
            self._memory.end_run(run_id, "error", str(exc))
            raise

    def _extract_description(self, desc_adf) -> str:
        if not desc_adf or not isinstance(desc_adf, dict):
            return ""
        texts = []
        for block in desc_adf.get("content", []):
            for inline in block.get("content", []):
                if inline.get("type") == "text":
                    texts.append(inline.get("text", ""))
        return " ".join(texts)
