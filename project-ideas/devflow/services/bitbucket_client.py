import requests
from db import database as db


def _session() -> tuple[str, requests.Session]:
    base = db.get_setting("bitbucket_url", "").rstrip("/")
    token = db.get_setting("bitbucket_token", "")
    s = requests.Session()
    s.headers.update({"Authorization": f"Bearer {token}"})
    return base, s


def _parse_slug(repo_slug: str) -> tuple[str, str]:
    """Split 'PROJECT/repo-name' into (project, repo)."""
    parts = repo_slug.split("/", 1)
    return parts[0], parts[1] if len(parts) > 1 else parts[0]


def list_files(repo_slug: str, path: str = "") -> list[str]:
    base, s = _session()
    proj, repo = _parse_slug(repo_slug)
    url = f"{base}/rest/api/1.0/projects/{proj}/repos/{repo}/files/{path}"
    r = s.get(url, params={"limit": 500}, timeout=15)
    r.raise_for_status()
    return r.json().get("values", [])


def get_file_content(repo_slug: str, file_path: str) -> str:
    base, s = _session()
    proj, repo = _parse_slug(repo_slug)
    url = f"{base}/rest/api/1.0/projects/{proj}/repos/{repo}/raw/{file_path}"
    r = s.get(url, timeout=15)
    if not r.ok:
        return ""
    return r.text


def list_open_prs(repo_slug: str) -> list[dict]:
    base, s = _session()
    proj, repo = _parse_slug(repo_slug)
    url = f"{base}/rest/api/1.0/projects/{proj}/repos/{repo}/pull-requests"
    r = s.get(url, params={"state": "OPEN", "limit": 100}, timeout=15)
    r.raise_for_status()
    prs = []
    for pr in r.json().get("values", []):
        prs.append({
            "id": pr["id"],
            "title": pr["title"],
            "author": pr["author"]["user"]["displayName"],
            "source_branch": pr["fromRef"]["displayId"],
            "target_branch": pr["toRef"]["displayId"],
            "links": pr.get("links", {}).get("self", [{}])[0].get("href", ""),
        })
    return prs


def get_pr_diff(repo_slug: str, pr_id: int) -> str:
    base, s = _session()
    proj, repo = _parse_slug(repo_slug)
    url = f"{base}/rest/api/1.0/projects/{proj}/repos/{repo}/pull-requests/{pr_id}/diff"
    r = s.get(url, timeout=20)
    if not r.ok:
        return ""
    # Bitbucket diff format — convert to unified diff text
    data = r.json()
    lines = []
    for diff in data.get("diffs", []):
        lines.append(f"--- {diff.get('source', {}).get('toString', 'a')}")
        lines.append(f"+++ {diff.get('destination', {}).get('toString', 'b')}")
        for hunk in diff.get("hunks", []):
            lines.append(f"@@ -{hunk['sourceLine']},{hunk['sourceSpan']} +{hunk['destinationLine']},{hunk['destinationSpan']} @@")
            for seg in hunk.get("segments", []):
                prefix = "+" if seg["type"] == "ADDED" else ("-" if seg["type"] == "REMOVED" else " ")
                for line in seg.get("lines", []):
                    lines.append(f"{prefix}{line['line']}")
    return "\n".join(lines)


def post_pr_inline_comment(repo_slug: str, pr_id: int, file_path: str, line_num: int, comment: str):
    base, s = _session()
    s.headers["Content-Type"] = "application/json"
    proj, repo = _parse_slug(repo_slug)
    url = f"{base}/rest/api/1.0/projects/{proj}/repos/{repo}/pull-requests/{pr_id}/comments"
    payload = {
        "text": comment,
        "anchor": {
            "line": line_num,
            "lineType": "ADDED",
            "fileType": "TO",
            "path": file_path,
        },
    }
    r = s.post(url, json=payload, timeout=10)
    r.raise_for_status()
