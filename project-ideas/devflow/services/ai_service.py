import json
import re
from openai import OpenAI
from db import database as db
from services.code_reader import CodeSummary, format_for_prompt


class AIServiceError(Exception):
    pass


def _client() -> OpenAI:
    base_url = db.get_setting("ai_base_url", "")
    api_key = db.get_setting("ai_api_key", "sk-placeholder")
    if not base_url:
        return OpenAI(api_key=api_key)
    return OpenAI(base_url=base_url, api_key=api_key)


def _model() -> str:
    return db.get_setting("ai_model", "gpt-4o")


def _chat(messages: list[dict]) -> str:
    try:
        resp = _client().chat.completions.create(model=_model(), messages=messages, temperature=0.3)
        return resp.choices[0].message.content or ""
    except Exception as e:
        raise AIServiceError(str(e)) from e


def _parse_json(text: str) -> list | dict:
    """Extract and parse first JSON array/object from text."""
    match = re.search(r"(\[.*\]|\{.*\})", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            pass
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return []


# ── Elaboration ────────────────────────────────────────────────────────────

def start_elaboration(srs_text: str, user_description: str) -> str:
    return _chat([
        {"role": "system", "content": "You are a software requirements analyst. Ask 3–5 concise, targeted clarifying questions to fully understand the requirement. Number each question. Ask only what is genuinely unclear."},
        {"role": "user", "content": f"SRS:\n{srs_text}\n\nDeveloper's description:\n{user_description}"},
    ])


def continue_elaboration(history: list[dict]) -> str:
    system = {"role": "system", "content": (
        "You are a software requirements analyst. Continue the Q&A. "
        "If you have enough information, reply exactly: ELABORATION_COMPLETE. "
        "Otherwise ask the next clarifying question."
    )}
    return _chat([system] + history)


# ── Generation ─────────────────────────────────────────────────────────────

def generate_formatted_desc(srs: str, chat_history: list[dict], template: str, code: CodeSummary) -> str:
    code_ctx = format_for_prompt(code)
    return _chat([
        {"role": "system", "content": f"You are a senior software engineer writing a Jira ticket description. Use exactly this template structure:\n\n{template}\n\nFill every section based on the SRS, the conversation, and the codebase context. Be specific and concise."},
        {"role": "user", "content": f"SRS:\n{srs}\n\nCodebase:\n{code_ctx}\n\nConversation history:\n{_fmt_history(chat_history)}"},
    ])


def generate_architecture(srs: str, chat_history: list[dict], code: CodeSummary) -> str:
    code_ctx = format_for_prompt(code)
    result = _chat([
        {"role": "system", "content": "You are a software architect. Produce a valid Mermaid diagram (graph TD) showing components, services, and data flows affected by the requirement. Output ONLY the Mermaid source, no markdown fences."},
        {"role": "user", "content": f"SRS:\n{srs}\n\nCodebase:\n{code_ctx}\n\nQ&A:\n{_fmt_history(chat_history)}"},
    ])
    # Strip fences if present
    result = re.sub(r"^```(?:mermaid)?\s*", "", result.strip(), flags=re.IGNORECASE)
    result = re.sub(r"\s*```$", "", result)
    return result.strip()


def generate_tasks(srs: str, chat_history: list[dict], code: CodeSummary) -> list[dict]:
    code_ctx = format_for_prompt(code)
    raw = _chat([
        {"role": "system", "content": 'You are a project manager. Break the requirement into development tasks. Return a JSON array: [{"title":"...","assignee_hint":"developer","estimated_hrs":4,"rationale":"..."}]. Only JSON, no commentary.'},
        {"role": "user", "content": f"SRS:\n{srs}\n\nCodebase:\n{code_ctx}\n\nQ&A:\n{_fmt_history(chat_history)}"},
    ])
    result = _parse_json(raw)
    return result if isinstance(result, list) else []


def generate_sdd(srs: str, chat_history: list[dict], code: CodeSummary) -> str:
    code_ctx = format_for_prompt(code)
    return _chat([
        {"role": "system", "content": "You are a senior architect. Write a Software Design Document in Markdown covering: Overview, Affected Components, Data Flow, API Changes, Error Handling, Security Considerations."},
        {"role": "user", "content": f"SRS:\n{srs}\n\nCodebase:\n{code_ctx}\n\nQ&A:\n{_fmt_history(chat_history)}"},
    ])


def generate_tests(srs: str, sdd_content: str) -> list[dict]:
    raw = _chat([
        {"role": "system", "content": 'You are a QA engineer. Generate unit test file stubs for every service/component mentioned in the SDD. Return a JSON array: [{"filename":"test_X.py","content":"# test stub\\n..."}]. Only JSON.'},
        {"role": "user", "content": f"SRS:\n{srs}\n\nSDD:\n{sdd_content}"},
    ])
    try:
        return _parse_json(raw)
    except Exception:
        return [{"filename": "test_feature.py", "content": "# TODO: add tests\n"}]


def generate_integration_tests(sprint_tasks: list[dict]) -> list[dict]:
    raw = _chat([
        {"role": "system", "content": 'Generate integration test tasks for a sprint. Return JSON: [{"title":"...","estimated_hrs":2,"covers_tasks":["PROJ-101"]}]. Only JSON.'},
        {"role": "user", "content": f"Sprint tasks:\n{json.dumps(sprint_tasks, indent=2)}"},
    ])
    try:
        return _parse_json(raw)
    except Exception:
        return []


def estimate_sprint_fit(tasks: list[dict], dev_days: int, test_days: int) -> str:
    total = sum(t.get("estimated_hrs", 0) for t in tasks)
    capacity = (dev_days + test_days) * 8
    if total > capacity:
        return f"⚠ Total estimate ({total:.1f}h) exceeds sprint capacity ({capacity}h). Consider moving tasks."
    return f"✓ Total estimate ({total:.1f}h) fits within sprint capacity ({capacity}h)."


# ── PR Review ──────────────────────────────────────────────────────────────

def generate_pr_review(diff_text: str, pr_title: str) -> list[dict]:
    raw = _chat([
        {"role": "system", "content": (
            "You are a senior software engineer conducting a formal code review. "
            "Review the diff and produce a list of review comments. "
            "Each comment must be professional, specific, and actionable. "
            "Do not write tips or suggestions — write formal observations about correctness, "
            "naming, structure, error handling, test coverage, and security. "
            "Every comment must reference the exact file and line. "
            'Return JSON: [{"file_path":"...","line_num":42,"comment":"..."}]. Only JSON.'
        )},
        {"role": "user", "content": f"PR: {pr_title}\n\nDiff:\n{diff_text[:8000]}"},
    ])
    try:
        return _parse_json(raw)
    except Exception:
        return []


# ── Bug Analysis ───────────────────────────────────────────────────────────

def analyze_bug(description: str, code_ctx: str) -> dict:
    raw = _chat([
        {"role": "system", "content": (
            "You are a senior engineer. Given the bug description and codebase, identify: "
            "(1) root cause with exact file(s) and line(s), "
            "(2) a list of code changes needed to fix it, "
            "(3) which existing unit test files relate to this area. "
            'Return JSON: {"root_cause":"...","affected_files":[{"file":"...","lines":"42-58","reason":"..."}],'
            '"fix_plan":[{"file":"...","change":"...","before":"...","after":"..."}],'
            '"related_test_files":["..."]}. Only JSON.'
        )},
        {"role": "user", "content": f"Bug description:\n{description}\n\nCodebase:\n{code_ctx}"},
    ])
    result = _parse_json(raw)
    if isinstance(result, dict):
        return result
    return {"root_cause": "Could not analyse.", "affected_files": [], "fix_plan": [], "related_test_files": []}


def predict_test_impact(fix_plan: list[dict], test_files: list[str], test_contents: dict) -> list[dict]:
    contents_text = "\n".join(f"### {f}\n{c[:1000]}" for f, c in test_contents.items())
    raw = _chat([
        {"role": "system", "content": (
            "You are a QA engineer. Given proposed code changes and existing tests, identify "
            "which test cases may fail. "
            'Return JSON: [{"test_file":"...","test_name":"...","risk":"may_fail","reason":"..."}]. Only JSON.'
        )},
        {"role": "user", "content": f"Fix plan:\n{json.dumps(fix_plan, indent=2)}\n\nTest files:\n{contents_text}"},
    ])
    try:
        return _parse_json(raw)
    except Exception:
        return []


# ── Helpers ────────────────────────────────────────────────────────────────

def _fmt_history(history: list[dict]) -> str:
    return "\n".join(f"{m['role'].upper()}: {m['content']}" for m in history)
