import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

from utils.errors import ConfigError

load_dotenv()


@dataclass(frozen=True)
class Settings:
    # LLM
    llm_base_url: str
    llm_api_key: str
    llm_model: str

    # Jira
    jira_base_url: Optional[str]
    jira_user_email: Optional[str]
    jira_api_token: Optional[str]
    jira_project_key: str

    # Bitbucket
    bitbucket_base_url: str
    bitbucket_username: Optional[str]
    bitbucket_app_password: Optional[str]
    bitbucket_workspace: Optional[str]
    bitbucket_repos: list

    # Bug → Repo mapping
    bug_repo_map: dict

    # Confluence
    confluence_base_url: Optional[str]
    confluence_username: Optional[str]
    confluence_password: Optional[str]

    # Memory
    memory_db_path: str
    memory_cache_ttl_minutes: int


def _parse_bug_repo_map(raw: str) -> dict:
    result = {}
    if not raw:
        return result
    for pair in raw.split(","):
        pair = pair.strip()
        if ":" in pair:
            k, v = pair.split(":", 1)
            result[k.strip()] = v.strip()
    return result


def _parse_repos(raw: str) -> list:
    if not raw:
        return []
    return [r.strip() for r in raw.split(",") if r.strip()]


def load_settings() -> Settings:
    missing = []
    for var in ("LLM_BASE_URL", "LLM_API_KEY", "LLM_MODEL"):
        if not os.getenv(var):
            missing.append(var)
    if missing:
        raise ConfigError(f"Missing required env vars: {', '.join(missing)}")

    db_path = os.getenv("MEMORY_DB_PATH", "~/.pattu/memory.db")
    db_path = str(Path(db_path).expanduser())

    return Settings(
        llm_base_url=os.environ["LLM_BASE_URL"],
        llm_api_key=os.environ["LLM_API_KEY"],
        llm_model=os.environ["LLM_MODEL"],
        jira_base_url=os.getenv("JIRA_BASE_URL"),
        jira_user_email=os.getenv("JIRA_USER_EMAIL"),
        jira_api_token=os.getenv("JIRA_API_TOKEN"),
        jira_project_key=os.getenv("JIRA_PROJECT_KEY", ""),
        bitbucket_base_url=os.getenv("BITBUCKET_BASE_URL", "https://api.bitbucket.org/2.0"),
        bitbucket_username=os.getenv("BITBUCKET_USERNAME"),
        bitbucket_app_password=os.getenv("BITBUCKET_APP_PASSWORD"),
        bitbucket_workspace=os.getenv("BITBUCKET_WORKSPACE"),
        bitbucket_repos=_parse_repos(os.getenv("BITBUCKET_REPOS", "")),
        bug_repo_map=_parse_bug_repo_map(os.getenv("BUG_REPO_MAP", "")),
        confluence_base_url=os.getenv("CONFLUENCE_BASE_URL"),
        confluence_username=os.getenv("CONFLUENCE_USERNAME"),
        confluence_password=os.getenv("CONFLUENCE_PASSWORD"),
        memory_db_path=db_path,
        memory_cache_ttl_minutes=int(os.getenv("MEMORY_CACHE_TTL_MINUTES", "15")),
    )
