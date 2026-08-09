import requests
from db import database as db


def _session() -> tuple[str, requests.Session]:
    base = db.get_setting("jira_url", "").rstrip("/")
    token = db.get_setting("jira_token", "")
    s = requests.Session()
    s.headers.update({"Authorization": f"Bearer {token}", "Content-Type": "application/json"})
    return base, s


def fetch_projects() -> list[dict]:
    base, s = _session()
    r = s.get(f"{base}/rest/api/2/project", timeout=10)
    r.raise_for_status()
    return [{"key": p["key"], "name": p["name"]} for p in r.json()]


def fetch_issue_types() -> list[dict]:
    base, s = _session()
    r = s.get(f"{base}/rest/api/2/issuetype", timeout=10)
    r.raise_for_status()
    return [{"id": t["id"], "name": t["name"]} for t in r.json()]


def fetch_srs_list(project_key: str) -> list[dict]:
    srs_type = db.get_setting("jira_issue_type_srs", "Story")
    base, s = _session()
    jql = f'project="{project_key}" AND issuetype="{srs_type}" AND resolution=Unresolved ORDER BY created DESC'
    r = s.get(f"{base}/rest/api/2/search", params={"jql": jql, "maxResults": 100}, timeout=15)
    r.raise_for_status()
    return [
        {"key": i["key"], "summary": i["fields"]["summary"],
         "status": i["fields"]["status"]["name"],
         "description": i["fields"].get("description") or ""}
        for i in r.json().get("issues", [])
    ]


def fetch_bugs(project_key: str) -> list[dict]:
    bug_type = db.get_setting("jira_issue_type_bug", "Bug")
    return _fetch_assigned(project_key, bug_type)


def fetch_improvements(project_key: str) -> list[dict]:
    impr_type = db.get_setting("jira_issue_type_improvement", "Improvement")
    return _fetch_assigned(project_key, impr_type)


def _fetch_assigned(project_key: str, issue_type: str) -> list[dict]:
    base, s = _session()
    jql = f'project="{project_key}" AND issuetype="{issue_type}" AND assignee=currentUser() AND resolution=Unresolved ORDER BY priority DESC'
    r = s.get(f"{base}/rest/api/2/search", params={"jql": jql, "maxResults": 100}, timeout=15)
    r.raise_for_status()
    return [
        {"key": i["key"], "summary": i["fields"]["summary"],
         "priority": i["fields"].get("priority", {}).get("name", ""),
         "status": i["fields"]["status"]["name"],
         "description": i["fields"].get("description") or ""}
        for i in r.json().get("issues", [])
    ]


def update_description(jira_key: str, description: str):
    base, s = _session()
    r = s.put(
        f"{base}/rest/api/2/issue/{jira_key}",
        json={"fields": {"description": description}},
        timeout=15,
    )
    r.raise_for_status()


def post_comment(jira_key: str, body: str):
    base, s = _session()
    r = s.post(f"{base}/rest/api/2/issue/{jira_key}/comment", json={"body": body}, timeout=10)
    r.raise_for_status()


def transition_issue(jira_key: str, status_name: str):
    base, s = _session()
    r = s.get(f"{base}/rest/api/2/issue/{jira_key}/transitions", timeout=10)
    r.raise_for_status()
    transitions = r.json().get("transitions", [])
    match = next((t for t in transitions if status_name.lower() in t["name"].lower()), None)
    if not match:
        return
    s.post(
        f"{base}/rest/api/2/issue/{jira_key}/transitions",
        json={"transition": {"id": match["id"]}},
        timeout=10,
    ).raise_for_status()


def fetch_active_sprint_tasks(project_key: str) -> tuple[dict | None, list[dict]]:
    board_id = db.get_setting("jira_board_id", "")
    if not board_id:
        return None, []
    base, s = _session()
    r = s.get(f"{base}/rest/agile/1.0/board/{board_id}/sprint", params={"state": "active"}, timeout=10)
    r.raise_for_status()
    sprints = r.json().get("values", [])
    if not sprints:
        return None, []
    sprint = sprints[0]
    sid = sprint["id"]
    r2 = s.get(
        f"{base}/rest/agile/1.0/sprint/{sid}/issue",
        params={"jql": "assignee=currentUser()", "maxResults": 100},
        timeout=15,
    )
    r2.raise_for_status()
    tasks = [
        {"key": i["key"], "summary": i["fields"]["summary"],
         "status": i["fields"]["status"]["name"],
         "estimate": i["fields"].get("story_points") or i["fields"].get("timeoriginalestimate") or 0}
        for i in r2.json().get("issues", [])
    ]
    sprint_info = {"id": str(sid), "name": sprint.get("name", ""), "start": sprint.get("startDate", ""),
                   "end": sprint.get("endDate", "")}
    return sprint_info, tasks


def fetch_bug_counts(project_key: str, period_days: int | None) -> dict:
    base, s = _session()
    bug_type = db.get_setting("jira_issue_type_bug", "Bug")
    date_filter = f" AND created >= -{period_days}d" if period_days else ""
    base_jql = f'project="{project_key}" AND issuetype="{bug_type}" AND assignee=currentUser(){date_filter}'

    def count(extra=""):
        r = s.get(f"{base}/rest/api/2/search", params={"jql": base_jql + extra, "maxResults": 0}, timeout=10)
        r.raise_for_status()
        return r.json().get("total", 0)

    return {
        "total": count(),
        "open": count(' AND statusCategory="To Do"'),
        "in_progress": count(' AND statusCategory="In Progress"'),
        "resolved": count(' AND statusCategory="Done"'),
    }
