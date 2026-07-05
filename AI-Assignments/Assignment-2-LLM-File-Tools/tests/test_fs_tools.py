"""
test_fs_tools.py
================
Tests for the Part A file-system tools and the Part B assistant routing.

Runs standalone or under pytest:
    python tests/test_fs_tools.py
    pytest tests/ -q

No API key required — the assistant is exercised in offline heuristic mode.
"""

from __future__ import annotations

import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import fs_tools  # noqa: E402
from llm_file_assistant import FileAssistant  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
RESUMES = os.path.join(os.path.dirname(HERE), "sample_data", "resumes")


def _ensure_samples():
    if not os.path.isdir(RESUMES) or not os.listdir(RESUMES):
        from sample_data.make_samples import main as make
        make()


# --- fs_tools: list_files -------------------------------------------------
def test_list_files_filters_by_extension():
    _ensure_samples()
    txts = fs_tools.list_files(RESUMES, ".txt")
    assert len(txts) >= 8
    assert all(f["extension"] == ".txt" for f in txts)
    # every entry carries the required metadata
    for f in txts:
        assert {"name", "path", "size_bytes", "modified"} <= set(f)


def test_list_files_missing_directory():
    res = fs_tools.list_files("/no/such/dir")
    assert res and "error" in res[0]


# --- fs_tools: read_file --------------------------------------------------
def test_read_file_txt_success():
    _ensure_samples()
    path = os.path.join(RESUMES, "resume_john_doe.txt")
    r = fs_tools.read_file(path)
    assert r["success"] is True
    assert "John Doe" in r["content"]
    assert r["metadata"]["word_count"] > 0
    assert r["metadata"]["file_type"] == "txt"


def test_read_file_missing_is_graceful():
    r = fs_tools.read_file("/no/such/file.txt")
    assert r["success"] is False
    assert "not found" in r["error"].lower()


def test_read_file_unsupported_type():
    with tempfile.NamedTemporaryFile(suffix=".xyz", delete=False) as tmp:
        tmp.write(b"data")
        name = tmp.name
    try:
        r = fs_tools.read_file(name)
        assert r["success"] is False
        assert "unsupported" in r["error"].lower()
    finally:
        os.unlink(name)


# --- fs_tools: write_file -------------------------------------------------
def test_write_file_creates_dirs():
    with tempfile.TemporaryDirectory() as d:
        target = os.path.join(d, "nested", "deep", "out.txt")
        w = fs_tools.write_file(target, "hello world")
        assert w["success"] is True
        assert w["bytes_written"] == len("hello world")
        assert os.path.exists(target)
        assert fs_tools.read_file(target)["content"] == "hello world"


# --- fs_tools: search_in_file --------------------------------------------
def test_search_case_insensitive_with_context():
    _ensure_samples()
    path = os.path.join(RESUMES, "resume_john_doe.txt")
    res = fs_tools.search_in_file(path, "python")  # lowercase query
    assert res["success"] is True
    assert res["match_count"] >= 1
    assert "context" in res["matches"][0]
    assert "line_number" in res["matches"][0]


def test_search_no_match():
    _ensure_samples()
    path = os.path.join(RESUMES, "resume_john_doe.txt")
    res = fs_tools.search_in_file(path, "cobol")
    assert res["success"] is True
    assert res["match_count"] == 0


# --- Part B: assistant routes NL queries to the right tools ---------------
def test_assistant_find_query():
    _ensure_samples()
    a = FileAssistant()
    out = a.ask("Find resumes mentioning Python experience")
    assert "resume_john_doe.txt" in out
    assert "Python" in out


def test_assistant_summary_query_writes_file():
    _ensure_samples()
    a = FileAssistant()
    out = a.ask("Create a summary file for resume_john_doe.txt")
    summary_path = os.path.join(RESUMES, "summary_resume_john_doe.txt")
    try:
        assert os.path.exists(summary_path)
        assert "SUMMARY OF resume_john_doe.txt" in out
    finally:
        if os.path.exists(summary_path):
            os.unlink(summary_path)


def test_assistant_read_all_query():
    _ensure_samples()
    a = FileAssistant()
    out = a.ask("Read all resumes in the resumes folder")
    assert "resume_jane_smith.txt" in out


# --------------------------------------------------------------------------
def _run_all():
    tests = [v for k, v in sorted(globals().items())
             if k.startswith("test_") and callable(v)]
    failed = 0
    for t in tests:
        try:
            t()
            print(f"PASS  {t.__name__}")
        except AssertionError as e:
            failed += 1
            print(f"FAIL  {t.__name__}: {e}")
        except Exception as e:  # noqa: BLE001
            failed += 1
            print(f"ERROR {t.__name__}: {type(e).__name__}: {e}")
    print(f"\n{len(tests) - failed}/{len(tests)} tests passed.")
    return failed


if __name__ == "__main__":
    sys.exit(1 if _run_all() else 0)
