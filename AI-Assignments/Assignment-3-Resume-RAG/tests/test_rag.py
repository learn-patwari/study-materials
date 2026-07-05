"""
test_rag.py
===========
Tests for the Resume RAG system and job matcher.

Runs standalone or under pytest:
    python tests/test_rag.py
    pytest tests/ -q

Offline by default — no API key, no external services.
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import resume_rag as rr  # noqa: E402
from job_matcher import JobMatcher, parse_must_have  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
RESUME_DIR = os.path.join(ROOT, "data", "resumes")
JOB_DIR = os.path.join(ROOT, "data", "jobs")


def _ensure_data():
    if not os.path.isdir(RESUME_DIR) or len(os.listdir(RESUME_DIR)) < 30:
        from data_gen import generate
        generate()


def _fresh_rag():
    _ensure_data()
    rag = rr.ResumeRAG(persist_dir=os.path.join(HERE, ".test_store"),
                       prefer_embedder="tfidf")
    rag.build_index(RESUME_DIR)
    return rag


# --- chunking / metadata --------------------------------------------------
def test_section_aware_chunking():
    text = ("Jane Smith\nFrontend Engineer\n\nSUMMARY\nGreat.\n\n"
            "SKILLS\nReact, TypeScript\n\nEXPERIENCE\n- built X\n\n"
            "EDUCATION\nB.S. CS\n\nCONTACT\nemail: x@y.com")
    chunks = rr.chunk_resume(text)
    sections = {c["section"] for c in chunks}
    assert {"SUMMARY", "SKILLS", "EXPERIENCE", "EDUCATION"} <= sections
    assert "CONTACT" not in sections  # contact is dropped


def test_metadata_extraction():
    text = ("John Doe\nBackend Engineer\n\nSUMMARY\nBackend Engineer with 7 "
            "years of experience.\n\nSKILLS\nPython, Django, PostgreSQL\n\n"
            "EDUCATION\nB.S. Computer Science")
    meta = rr.extract_metadata(text, "john.txt")
    assert meta["candidate_name"] == "John Doe"
    assert meta["experience_years"] == 7
    assert "Python" in meta["skills"] and "Django" in meta["skills"]
    assert "Computer Science" in meta["education"]


# --- indexing / retrieval -------------------------------------------------
def test_index_builds_all_resumes():
    rag = _fresh_rag()
    assert len(rag.candidates) >= 30
    assert rag.store.count() > len(rag.candidates)  # multiple chunks per resume


def test_semantic_search_returns_relevant_role():
    rag = _fresh_rag()
    hits = rag.search("react typescript frontend web app", k=5)
    roles = [h["metadata"]["role"] for h in hits]
    assert "frontend_engineer" in roles


def test_metadata_filtering():
    rag = _fresh_rag()
    hits = rag.search("engineer", k=10, where={"role": "devops_engineer"})
    assert hits and all(h["metadata"]["role"] == "devops_engineer" for h in hits)


# --- matcher --------------------------------------------------------------
def test_parse_must_have():
    parsed = parse_must_have(["5+ years Python", "3 years of AWS"])
    assert parsed[0] == {"skill": "Python", "min_years": 5, "raw": "5+ years Python"}
    assert parsed[1]["skill"] == "AWS" and parsed[1]["min_years"] == 3


def test_match_output_schema():
    rag = _fresh_rag()
    matcher = JobMatcher(rag)
    jd = open(os.path.join(JOB_DIR, "job_backend_python.txt"), encoding="utf-8").read()
    result = matcher.match(jd, k=5)
    assert set(result) == {"job_description", "top_matches"}
    assert len(result["top_matches"]) <= 5
    top = result["top_matches"][0]
    assert {"candidate_name", "resume_path", "match_score", "matched_skills",
            "relevant_excerpts", "reasoning"} <= set(top)
    assert 0 <= top["match_score"] <= 100


def test_top_match_is_correct_role_and_scored():
    rag = _fresh_rag()
    matcher = JobMatcher(rag)
    jd = open(os.path.join(JOB_DIR, "job_ml_engineer.txt"), encoding="utf-8").read()
    result = matcher.match(jd, k=5, must_have=["3+ years Python"])
    top = result["top_matches"][0]
    # scores are sorted descending
    scores = [m["match_score"] for m in result["top_matches"]]
    assert scores == sorted(scores, reverse=True)
    assert top["match_score"] >= 50


def test_must_have_filter_excludes_unqualified():
    rag = _fresh_rag()
    matcher = JobMatcher(rag)
    jd = "Backend role needing Python."
    # Require an absurd experience bar — everyone should be filtered out.
    result = matcher.match(jd, k=10, must_have=["99+ years Python"])
    assert result["top_matches"] == []


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
