import json
import uuid
from datetime import datetime, timedelta
from typing import Callable, Generator, Optional

from core.llm_client import make_client
from core.memory import SQLiteMemory
from utils.config import Settings
from agents.jira_agent import JiraAgent
from agents.bitbucket_agent import BitbucketAgent
from agents.confluence_agent import ConfluenceAgent

PATTU_SYSTEM_PROMPT = """You are Pattu, a personal AI assistant for Akshay Patwari.
You are smart, concise, and action-oriented. You have Jira, Bitbucket, and Confluence
subagent tools available. You remember past conversations and cached results in memory.

Rules:
1. Before calling a subagent tool, check if cached data is fresh (within the last 15 min).
   Use recall_memory to check. If fresh, use the cached result instead of re-fetching.
2. Always prioritize Bug tickets above all other issue types.
3. For each bug ticket, check BUG_REPO_MAP to find the right repo, then call
   bitbucket_inspect_repo and suggest a specific code fix.
4. Always address the user as "Akshay".
5. When the user says "save this", "create a page", or "document this", call
   confluence_create_page with a good title and the relevant content.
6. Be concise. Use bullet points. Skip pleasantries unless it's a greeting.
"""

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "run_jira_agent",
            "description": "Spin up Jira subagent to fetch all assigned open tickets.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "run_bitbucket_agent",
            "description": "Spin up Bitbucket subagent to fetch open PRs across all monitored repos.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "bitbucket_inspect_repo",
            "description": "Inspect a Bitbucket repo for source files related to a bug ticket.",
            "parameters": {
                "type": "object",
                "properties": {
                    "repo_slug": {"type": "string", "description": "Bitbucket repo slug"},
                    "search_terms": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Keywords to match against file paths",
                    },
                },
                "required": ["repo_slug", "search_terms"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "confluence_create_page",
            "description": "Create a new page in Akshay's personal Confluence space.",
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "content": {"type": "string", "description": "Page content in markdown or plain text"},
                },
                "required": ["title", "content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "confluence_list_pages",
            "description": "List pages in Akshay's personal Confluence space.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "recall_memory",
            "description": "Read a cached value from shared memory by key.",
            "parameters": {
                "type": "object",
                "properties": {
                    "key": {"type": "string", "description": "Memory key to retrieve"}
                },
                "required": ["key"],
            },
        },
    },
]


class Orchestrator:
    def __init__(self, settings: Settings, memory: SQLiteMemory):
        self._settings = settings
        self._memory = memory
        self._client = make_client(settings)
        self._session_id = str(uuid.uuid4())
        self._jira: Optional[JiraAgent] = None
        self._bitbucket: Optional[BitbucketAgent] = None
        self._confluence: Optional[ConfluenceAgent] = None

    def _jira_agent(self) -> JiraAgent:
        if self._jira is None:
            self._jira = JiraAgent(self._settings, self._memory)
        return self._jira

    def _bitbucket_agent(self) -> BitbucketAgent:
        if self._bitbucket is None:
            self._bitbucket = BitbucketAgent(self._settings, self._memory)
        return self._bitbucket

    def _confluence_agent(self) -> ConfluenceAgent:
        if self._confluence is None:
            self._confluence = ConfluenceAgent(self._settings, self._memory)
        return self._confluence

    def _dispatch(self, name: str, args: dict) -> str:
        try:
            if name == "run_jira_agent":
                return json.dumps(self._jira_agent().fetch_my_tickets())
            elif name == "run_bitbucket_agent":
                return json.dumps(self._bitbucket_agent().fetch_open_prs())
            elif name == "bitbucket_inspect_repo":
                return json.dumps(
                    self._bitbucket_agent().inspect_repo_for_bug(
                        args["repo_slug"], args.get("search_terms", [])
                    )
                )
            elif name == "confluence_create_page":
                return json.dumps(
                    self._confluence_agent().create_page(args["title"], args["content"])
                )
            elif name == "confluence_list_pages":
                return json.dumps(self._confluence_agent().list_my_pages())
            elif name == "recall_memory":
                val = self._memory.get(args["key"])
                return json.dumps({"key": args["key"], "value": val})
            else:
                return json.dumps({"error": f"Unknown tool: {name}"})
        except Exception as exc:
            return json.dumps({"error": str(exc)})

    def chat(self, user_message: str, on_tool_call: Optional[Callable[[str, dict], None]] = None) -> str:
        """Run one user turn. Returns the final assistant text."""
        self._memory.save_message(self._session_id, "user", user_message)

        history = self._memory.get_history(self._session_id, limit=30)
        messages = [{"role": "system", "content": PATTU_SYSTEM_PROMPT}] + history

        while True:
            response = self._client.chat.completions.create(
                model=self._settings.llm_model,
                messages=messages,
                tools=TOOLS,
                max_tokens=4096,
            )
            choice = response.choices[0]
            msg = choice.message

            if choice.finish_reason == "tool_calls" and msg.tool_calls:
                messages.append(msg)
                for tc in msg.tool_calls:
                    fn_name = tc.function.name
                    fn_args = json.loads(tc.function.arguments or "{}")
                    if on_tool_call:
                        on_tool_call(fn_name, fn_args)
                    result = self._dispatch(fn_name, fn_args)
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "content": result,
                    })
                continue

            final_text = msg.content or ""
            self._memory.save_message(self._session_id, "assistant", final_text)
            return final_text

    def stream_chat(self, user_message: str, on_tool_call: Optional[Callable[[str, dict], None]] = None) -> Generator[str, None, None]:
        """Stream the final response token by token. Tool calls are handled silently."""
        self._memory.save_message(self._session_id, "user", user_message)

        history = self._memory.get_history(self._session_id, limit=30)
        messages = [{"role": "system", "content": PATTU_SYSTEM_PROMPT}] + history

        while True:
            response = self._client.chat.completions.create(
                model=self._settings.llm_model,
                messages=messages,
                tools=TOOLS,
                max_tokens=4096,
            )
            choice = response.choices[0]
            msg = choice.message

            if choice.finish_reason == "tool_calls" and msg.tool_calls:
                messages.append(msg)
                for tc in msg.tool_calls:
                    fn_name = tc.function.name
                    fn_args = json.loads(tc.function.arguments or "{}")
                    if on_tool_call:
                        on_tool_call(fn_name, fn_args)
                    result = self._dispatch(fn_name, fn_args)
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "content": result,
                    })
                continue

            final_text = msg.content or ""
            self._memory.save_message(self._session_id, "assistant", final_text)
            yield final_text
            return

    @property
    def session_id(self) -> str:
        return self._session_id
