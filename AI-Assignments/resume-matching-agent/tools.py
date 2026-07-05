"""
tools.py
========
Tools available to the matching agent.

This module provides both:
  * plain Python functions (used directly by the LangGraph nodes), and
  * ``@tool``-decorated LangChain tools (so an LLM-driven agent could call
    them by name — satisfying "Tools Available to Agent").

Tool inventory (per the assignment):
  File-system tools (Milestone 1)  : list_resumes, read_resume, read_job_description
  RAG search tool   (Milestone 2)  : rag_search
  extract_requirements(jd)         : parse must-have vs nice-to-have
  compare_candidates(candidate_ids): head-to-head comparison
  generate_interview_questions(id) : screening questions
Plus scoring/analysis helpers used by the workflow:
  rank_candidates, deep_analysis, hire_recommendation
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

from data_store import SKILL_VOCAB, load_candidates, render_resume
from llm import llm_complete
from rag import ResumeIndex

# --------------------------------------------------------------------------
# Corpus singleton
# --------------------------------------------------------------------------
class Corpus:
    """Lazily-loaded candidate corpus + RAG index (shared across tools)."""

    _candidates: Optional[List[Dict[str, Any]]] = None
    _index: Optional[ResumeIndex] = None

    @classmethod
    def candidates(cls) -> List[Dict[str, Any]]:
        if cls._candidates is None:
            cls._candidates = load_candidates()
        return cls._candidates

    @classmethod
    def index(cls) -> ResumeIndex:
        if cls._index is None:
            cls._index = ResumeIndex(cls.candidates())
        return cls._index

    @classmethod
    def by_id(cls, cid: str) -> Optional[Dict[str, Any]]:
        return {c["id"]: c for c in cls.candidates()}.get(cid.upper())


# --------------------------------------------------------------------------
# File-system tools (Milestone 1)
# --------------------------------------------------------------------------
def list_resumes() -> List[Dict[str, str]]:
    """List all resumes in the corpus (id, name, title, years)."""
    return [
        {"id": c["id"], "name": c["name"], "title": c["title"],
         "years_experience": c["years_experience"]}
        for c in Corpus.candidates()
    ]


def read_resume(candidate_id: str) -> str:
    """Return the full rendered resume text for a candidate id."""
    c = Corpus.by_id(candidate_id)
    if not c:
        return f"No resume found for id '{candidate_id}'."
    return render_resume(c)


def read_job_description(path: Optional[str] = None) -> str:
    """Read a job description file. Defaults to the sample JD."""
    import os
    from data_store import JD_DIR, SAMPLE_JD, ensure_data

    ensure_data()
    if path is None:
        path = os.path.join(JD_DIR, "senior_frontend_engineer.md")
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as fh:
            return fh.read()
    return SAMPLE_JD


# --------------------------------------------------------------------------
# RAG search tool (Milestone 2)
# --------------------------------------------------------------------------
def rag_search(query: str, k: int = 10) -> List[Dict[str, Any]]:
    """Semantic search over resumes. Returns top-k {id, score, name}."""
    hits = Corpus.index().search(query, k=k)
    return [{"id": h["id"], "score": h["score"], "name": h["candidate"]["name"]}
            for h in hits]


# --------------------------------------------------------------------------
# extract_requirements(jd) — must-have vs nice-to-have
# --------------------------------------------------------------------------
_MUST_HDR = re.compile(r"(must[- ]?have|requirements?|required|qualifications)", re.I)
_NICE_HDR = re.compile(r"(nice[- ]?to[- ]?have|preferred|bonus|plus|good to have)", re.I)
_YEARS_RE = re.compile(r"(\d+)\s*\+?\s*years?", re.I)


def _find_skills(text: str) -> List[str]:
    found = []
    low = text.lower()
    for skill in SKILL_VOCAB:
        # word-ish boundary match (handles React, Next.js, Tailwind CSS, etc.)
        pat = re.escape(skill.lower())
        if re.search(rf"(?<![a-z0-9]){pat}(?![a-z0-9])", low):
            found.append(skill)
    return found


def extract_requirements(jd: str) -> Dict[str, Any]:
    """Parse a job description into structured requirements.

    Returns:
        {
          "must_have_skills": [...],
          "nice_to_have_skills": [...],
          "min_years": int | None,
          "raw": {"must_section": str, "nice_section": str},
        }
    """
    lines = jd.splitlines()
    must_section, nice_section = [], []
    bucket = must_section  # default un-headed text to must-have
    for line in lines:
        if _NICE_HDR.search(line) and not _MUST_HDR.search(line):
            bucket = nice_section
            continue
        if _MUST_HDR.search(line):
            bucket = must_section
            continue
        bucket.append(line)

    must_text = "\n".join(must_section)
    nice_text = "\n".join(nice_section)

    must_skills = _find_skills(must_text)
    nice_skills = [s for s in _find_skills(nice_text) if s not in must_skills]

    ym = _YEARS_RE.search(must_text) or _YEARS_RE.search(jd)
    min_years = int(ym.group(1)) if ym else None

    return {
        "must_have_skills": must_skills,
        "nice_to_have_skills": nice_skills,
        "min_years": min_years,
        "raw": {"must_section": must_text.strip(), "nice_section": nice_text.strip()},
    }


def parse_query_criteria(query: str) -> Dict[str, Any]:
    """Extract ad-hoc criteria from a natural-language query.

    e.g. "Find candidates with React and 3+ years experience"
         -> {"must_have_skills": ["React"], "min_years": 3}
    """
    skills = _find_skills(query)
    ym = _YEARS_RE.search(query)
    return {
        "must_have_skills": skills,
        "nice_to_have_skills": [],
        "min_years": int(ym.group(1)) if ym else None,
    }


# --------------------------------------------------------------------------
# Scoring / ranking
# --------------------------------------------------------------------------
def score_candidate(candidate: Dict[str, Any], requirements: Dict[str, Any],
                    rag_score: float = 0.0) -> Dict[str, Any]:
    """Score one candidate against requirements. Returns score + breakdown."""
    cand_skills = {s.lower() for s in candidate["skills"]}
    must = requirements.get("must_have_skills") or []
    nice = requirements.get("nice_to_have_skills") or []
    min_years = requirements.get("min_years")

    must_matched = [s for s in must if s.lower() in cand_skills]
    must_missing = [s for s in must if s.lower() not in cand_skills]
    nice_matched = [s for s in nice if s.lower() in cand_skills]

    must_ratio = (len(must_matched) / len(must)) if must else 1.0
    nice_ratio = (len(nice_matched) / len(nice)) if nice else 0.0

    years = candidate["years_experience"]
    if min_years:
        years_factor = min(1.0, years / min_years)
        meets_years = years >= min_years
    else:
        years_factor = 1.0
        meets_years = True

    # Weighted blend. Must-have skills dominate; RAG adds semantic signal.
    score = (0.55 * must_ratio + 0.15 * nice_ratio +
             0.15 * years_factor + 0.15 * rag_score)
    # Hard-ish gate: missing a must-have skill caps the score.
    if must and must_missing:
        score *= 0.6 + 0.4 * must_ratio
    if not meets_years:
        score *= 0.7

    return {
        "id": candidate["id"],
        "name": candidate["name"],
        "title": candidate["title"],
        "years_experience": years,
        "score": round(float(score), 4),
        "must_matched": must_matched,
        "must_missing": must_missing,
        "nice_matched": nice_matched,
        "meets_years": meets_years,
        "rag_score": round(float(rag_score), 4),
    }


def _reasoning(row: Dict[str, Any], requirements: Dict[str, Any]) -> str:
    parts = []
    if row["must_matched"]:
        parts.append("matches must-haves [" + ", ".join(row["must_matched"]) + "]")
    if row["must_missing"]:
        parts.append("missing [" + ", ".join(row["must_missing"]) + "]")
    if row["nice_matched"]:
        parts.append("bonus [" + ", ".join(row["nice_matched"]) + "]")
    min_years = requirements.get("min_years")
    if min_years:
        parts.append(f"{row['years_experience']}y exp vs {min_years}y required"
                     + ("" if row["meets_years"] else " (below)"))
    else:
        parts.append(f"{row['years_experience']}y exp")
    return "; ".join(parts)


def rank_candidates(requirements: Dict[str, Any], query: str = "",
                    top_k: int = 10) -> List[Dict[str, Any]]:
    """Rank the full corpus against requirements. Returns top_k ranked rows."""
    # RAG query = explicit query + skills, so semantic signal reinforces skills.
    rag_query = " ".join(filter(None, [
        query,
        " ".join(requirements.get("must_have_skills") or []),
        " ".join(requirements.get("nice_to_have_skills") or []),
    ])) or "frontend engineer"
    rag_hits = {h["id"]: h["score"] for h in Corpus.index().search(rag_query, k=100)}
    max_rag = max(rag_hits.values()) if rag_hits else 1.0
    max_rag = max_rag or 1.0

    rows = []
    for c in Corpus.candidates():
        norm_rag = rag_hits.get(c["id"], 0.0) / max_rag
        row = score_candidate(c, requirements, rag_score=norm_rag)
        row["reasoning"] = _reasoning(row, requirements)
        rows.append(row)
    rows.sort(key=lambda r: r["score"], reverse=True)
    return rows[:top_k]


# --------------------------------------------------------------------------
# compare_candidates(candidate_ids)
# --------------------------------------------------------------------------
def compare_candidates(candidate_ids: List[str],
                       requirements: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Head-to-head comparison of candidates across skills and experience."""
    requirements = requirements or {"must_have_skills": [], "nice_to_have_skills": []}
    cands = [Corpus.by_id(cid) for cid in candidate_ids]
    cands = [c for c in cands if c]
    if not cands:
        return {"error": "No valid candidate ids provided."}

    all_skills = sorted({s for c in cands for s in c["skills"]})
    rows = []
    for c in cands:
        scored = score_candidate(c, requirements)
        rows.append({
            "id": c["id"], "name": c["name"], "title": c["title"],
            "years_experience": c["years_experience"],
            "score": scored["score"],
            "skills": c["skills"],
            "must_missing": scored["must_missing"],
        })
    rows.sort(key=lambda r: r["score"], reverse=True)
    return {
        "candidates": rows,
        "skill_matrix": {
            skill: [skill in c["skills"] for c in cands] for skill in all_skills
        },
        "order": [c["id"] for c in cands],
        "winner": rows[0]["id"] if rows else None,
    }


def explain_ranking(id_a: str, id_b: str,
                    requirements: Dict[str, Any]) -> str:
    """Explain why candidate A ranks vs candidate B (the "why" query)."""
    a, b = Corpus.by_id(id_a), Corpus.by_id(id_b)
    if not a or not b:
        return "One or both candidates not found."
    sa = score_candidate(a, requirements)
    sb = score_candidate(b, requirements)
    higher, lower = (sa, sb) if sa["score"] >= sb["score"] else (sb, sa)

    a_only = sorted(set(a["skills"]) - set(b["skills"]))
    b_only = sorted(set(b["skills"]) - set(a["skills"]))
    lines = [
        f"{higher['name']} ({higher['score']}) ranks higher than "
        f"{lower['name']} ({lower['score']}).",
        f"- Experience: {higher['name']} has {higher['years_experience']}y vs "
        f"{lower['name']}'s {lower['years_experience']}y.",
        f"- Must-have coverage: {higher['name']} matches "
        f"{len(higher['must_matched'])}/"
        f"{len(higher['must_matched']) + len(higher['must_missing'])}, "
        f"{lower['name']} matches {len(lower['must_matched'])}/"
        f"{len(lower['must_matched']) + len(lower['must_missing'])}.",
    ]
    winner_name = higher["name"]
    winner_only = a_only if higher["id"] == a["id"] else b_only
    loser_only = b_only if higher["id"] == a["id"] else a_only
    if winner_only:
        lines.append(f"- {winner_name} additionally brings: {', '.join(winner_only)}.")
    if loser_only:
        lines.append(f"- {lower['name']} uniquely brings: {', '.join(loser_only)} "
                     f"(not enough to close the gap).")

    narrative = llm_complete(
        "You are a concise technical recruiter. Explain candidate ranking "
        "differences factually in 2-3 sentences.",
        "\n".join(lines),
    )
    return narrative or "\n".join(lines)


# --------------------------------------------------------------------------
# generate_interview_questions(candidate_id)
# --------------------------------------------------------------------------
def generate_interview_questions(candidate_id: str,
                                 requirements: Optional[Dict[str, Any]] = None,
                                 n: int = 5) -> List[str]:
    """Generate targeted screening questions for a candidate."""
    c = Corpus.by_id(candidate_id)
    if not c:
        return [f"No candidate '{candidate_id}'."]
    requirements = requirements or {"must_have_skills": [], "nice_to_have_skills": []}
    scored = score_candidate(c, requirements)

    # LLM path (nicer, contextual questions).
    narrative = llm_complete(
        "You are a senior engineer preparing a technical screen. Given a "
        "candidate's skills, gaps, and the role requirements, write "
        f"{n} specific interview questions. Return them as a numbered list.",
        f"Role must-haves: {requirements.get('must_have_skills')}\n"
        f"Candidate skills: {c['skills']}\n"
        f"Missing must-haves: {scored['must_missing']}\n"
        f"Experience: {c['years_experience']} years",
    )
    if narrative:
        qs = [re.sub(r"^\s*\d+[\.\)]\s*", "", ln).strip()
              for ln in narrative.splitlines() if ln.strip()]
        return [q for q in qs if q][:n]

    # Heuristic fallback.
    questions: List[str] = []
    for skill in c["skills"][:3]:
        questions.append(
            f"Describe a challenging problem you solved using {skill}. "
            f"What trade-offs did you make?")
    for gap in scored["must_missing"][:2]:
        questions.append(
            f"This role requires {gap}, which isn't on your resume. "
            f"What's your experience or ramp-up plan for {gap}?")
    questions.append(
        f"Walk me through how you'd approach building a feature end-to-end "
        f"given your {c['years_experience']} years of experience.")
    return questions[:n]


# --------------------------------------------------------------------------
# Multi-round screening (Part C)
# --------------------------------------------------------------------------
def deep_analysis(candidate_id: str, requirements: Dict[str, Any]) -> Dict[str, Any]:
    """Round-2 deep analysis: strengths, gaps, improvement suggestions."""
    c = Corpus.by_id(candidate_id)
    if not c:
        return {"error": f"No candidate '{candidate_id}'."}
    scored = score_candidate(c, requirements)

    strengths = list(scored["must_matched"]) + list(scored["nice_matched"])
    gaps = list(scored["must_missing"])
    suggestions = []
    for gap in gaps:
        suggestions.append(f"Gain hands-on {gap} experience (course, side project, or OJT).")
    if requirements.get("min_years") and not scored["meets_years"]:
        suggestions.append(
            f"Needs more experience: {c['years_experience']}y vs "
            f"{requirements['min_years']}y target.")
    if not suggestions:
        suggestions.append("Strong all-round match; focus screen on depth, not breadth.")

    return {
        "id": c["id"], "name": c["name"], "title": c["title"],
        "score": scored["score"],
        "strengths": strengths,
        "gaps": gaps,
        "improvement_suggestions": suggestions,
        "highlights": [h for job in c["experience"] for h in job["highlights"]][:4],
    }


def hire_recommendation(candidate_id: str, requirements: Dict[str, Any]) -> Dict[str, Any]:
    """Round-3 final hire / no-hire recommendation for a candidate."""
    c = Corpus.by_id(candidate_id)
    if not c:
        return {"error": f"No candidate '{candidate_id}'."}
    scored = score_candidate(c, requirements)
    score = scored["score"]

    if score >= 0.75 and not scored["must_missing"] and scored["meets_years"]:
        decision, confidence = "HIRE", "high"
    elif score >= 0.6:
        decision, confidence = "LEAN HIRE", "medium"
    elif score >= 0.45:
        decision, confidence = "BORDERLINE", "low"
    else:
        decision, confidence = "NO HIRE", "medium"

    rationale = _reasoning(scored, requirements)
    narrative = llm_complete(
        "You are a hiring manager. In 2 sentences, justify a hire decision "
        "given the score breakdown. Be direct.",
        f"Decision: {decision}\nScore: {score}\nDetails: {rationale}",
    )
    return {
        "id": c["id"], "name": c["name"],
        "decision": decision, "confidence": confidence,
        "score": score, "rationale": narrative or rationale,
    }


# --------------------------------------------------------------------------
# LangChain tool wrappers (so an LLM agent can call tools by name)
# --------------------------------------------------------------------------
def build_langchain_tools():
    """Return the tools as LangChain StructuredTools (best-effort)."""
    try:
        from langchain_core.tools import tool
    except Exception:
        return []

    @tool
    def list_resumes_tool() -> list:
        """List all resumes (id, name, title, years)."""
        return list_resumes()

    @tool
    def read_resume_tool(candidate_id: str) -> str:
        """Read a candidate's full resume by id (e.g. 'C001')."""
        return read_resume(candidate_id)

    @tool
    def rag_search_tool(query: str, k: int = 10) -> list:
        """Semantic search over resumes; returns top-k candidates."""
        return rag_search(query, k)

    @tool
    def extract_requirements_tool(jd: str) -> dict:
        """Parse a job description into must-have vs nice-to-have requirements."""
        return extract_requirements(jd)

    @tool
    def compare_candidates_tool(candidate_ids: list) -> dict:
        """Head-to-head comparison of candidates by id."""
        return compare_candidates(candidate_ids)

    @tool
    def generate_interview_questions_tool(candidate_id: str) -> list:
        """Generate screening interview questions for a candidate id."""
        return generate_interview_questions(candidate_id)

    return [
        list_resumes_tool, read_resume_tool, rag_search_tool,
        extract_requirements_tool, compare_candidates_tool,
        generate_interview_questions_tool,
    ]
