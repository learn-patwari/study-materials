import pytest
from unittest.mock import patch, MagicMock
import services.ai_service as ai_service


def _mock_chat(response_text: str):
    """Context manager that patches _chat to return response_text."""
    return patch("services.ai_service._chat", return_value=response_text)


# ── _parse_json ───────────────────────────────────────────────────────

def test_parse_json_plain_array():
    result = ai_service._parse_json('[{"a": 1}]')
    assert result == [{"a": 1}]


def test_parse_json_plain_object():
    result = ai_service._parse_json('{"key": "value"}')
    assert result == {"key": "value"}


def test_parse_json_with_markdown_fence():
    text = '```json\n[{"title": "Task 1"}]\n```'
    result = ai_service._parse_json(text)
    assert result == [{"title": "Task 1"}]


def test_parse_json_embedded_in_prose():
    text = 'Here are the tasks:\n[{"title": "Do something"}]\nEnd.'
    result = ai_service._parse_json(text)
    assert result == [{"title": "Do something"}]


def test_parse_json_invalid_returns_empty_list():
    result = ai_service._parse_json("This is not JSON at all")
    assert result == []


def test_parse_json_nested_object():
    result = ai_service._parse_json('{"root_cause": "null pointer", "files": []}')
    assert result["root_cause"] == "null pointer"


# ── generate_tasks ────────────────────────────────────────────────────

def test_generate_tasks_returns_list():
    response = '[{"title": "Task A", "estimated_hrs": 3}, {"title": "Task B", "estimated_hrs": 5}]'
    with _mock_chat(response):
        code = MagicMock()
        result = ai_service.generate_tasks("SRS text", [], code)
    assert isinstance(result, list)
    assert len(result) == 2
    assert result[0]["title"] == "Task A"


def test_generate_tasks_fallback_on_bad_json():
    with _mock_chat("Sorry, I cannot generate tasks today."):
        code = MagicMock()
        result = ai_service.generate_tasks("SRS text", [], code)
    assert result == []


# ── generate_architecture ─────────────────────────────────────────────

def test_generate_architecture_strips_fences():
    with _mock_chat("```mermaid\ngraph LR; A-->B\n```"):
        code = MagicMock()
        result = ai_service.generate_architecture("SRS", [], code)
    assert "```" not in result
    assert "graph LR" in result


def test_generate_architecture_plain_returned_as_is():
    with _mock_chat("graph LR; A-->B"):
        code = MagicMock()
        result = ai_service.generate_architecture("SRS", [], code)
    assert result == "graph LR; A-->B"


# ── generate_pr_review ────────────────────────────────────────────────

def test_generate_pr_review_returns_comments():
    response = '[{"file_path": "main.py", "line_num": 10, "comment": "No error handling."}]'
    with _mock_chat(response):
        result = ai_service.generate_pr_review("diff text", "PR title")
    assert len(result) == 1
    assert result[0]["file_path"] == "main.py"
    assert result[0]["line_num"] == 10


def test_generate_pr_review_empty_on_bad_json():
    with _mock_chat("Looks good to me!"):
        result = ai_service.generate_pr_review("diff text", "PR title")
    assert result == []


# ── analyze_bug ───────────────────────────────────────────────────────

def test_analyze_bug_returns_dict():
    response = '{"root_cause": "NPE in line 42", "affected_files": [], "fix_plan": [], "related_test_files": []}'
    with _mock_chat(response):
        code = MagicMock()
        result = ai_service.analyze_bug("Bug description", code)
    assert result["root_cause"] == "NPE in line 42"
    assert "fix_plan" in result


def test_analyze_bug_fallback_on_bad_response():
    with _mock_chat("I cannot analyse this."):
        code = MagicMock()
        result = ai_service.analyze_bug("Bug description", code)
    assert isinstance(result, dict)
    assert "root_cause" in result


# ── generate_tests ────────────────────────────────────────────────────

def test_generate_tests_returns_list():
    response = '[{"filename": "test_service.py", "content": "def test_x(): pass"}]'
    with _mock_chat(response):
        result = ai_service.generate_tests("SRS", "SDD content")
    assert isinstance(result, list)
    assert result[0]["filename"] == "test_service.py"


# ── _fmt_history ──────────────────────────────────────────────────────

def test_fmt_history_formats_roles():
    history = [
        {"role": "user", "content": "Hello"},
        {"role": "assistant", "content": "Hi there"},
    ]
    text = ai_service._fmt_history(history)
    assert "user" in text.lower()
    assert "Hello" in text
    assert "Hi there" in text


def test_fmt_history_empty():
    assert ai_service._fmt_history([]) == ""
