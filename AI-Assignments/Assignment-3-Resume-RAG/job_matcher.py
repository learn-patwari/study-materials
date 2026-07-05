"""
job_matcher.py
==============
Job matching engine over the Resume RAG index (Assignment 3, Part B).

Given a job description it:
  1. embeds the JD and retrieves the top candidate chunks (semantic search),
  2. blends in a keyword score for the critical skills named in the JD
     (hybrid search),
  3. scores each candidate 0-100 with match reasoning + relevant excerpts,
  4. filters out candidates that fail must-have requirements
     (e.g. "5+ years Python").

Output matches the assignment's schema exactly:

    {
      "job_description": "...",
      "top_matches": [
        {
          "candidate_name": "...", "resume_path": "...",
          "match_score": 92, "matched_skills": [...],
          "relevant_excerpts": [...], "reasoning": "..."
        }, ...
      ]
    }

Usage:
    python job_matcher.py "Senior Backend Engineer, 5+ years Python, Django..."
    python job_matcher.py --job data/jobs/job_backend_python.txt --must "5+ years Python"
"""

from __future__ import annotations

import argparse
import json
import os
import re
from typing import Any, Dict, List, Optional

from resume_rag import ResumeRAG, find_skills, _YEARS_RE

_MUST_RE = re.compile(r"(\d+)\s*\+?\s*years?\s+(?:of\s+)?(.+)", re.I)


def parse_must_have(items: List[str]) -> List[Dict[str, Any]]:
    """Parse requirements like '5+ years Python' -> {skill, min_years}."""
    parsed = []
    for raw in items:
        raw = raw.strip()
        m = _MUST_RE.search(raw)
        if m:
            years = int(m.group(1))
            skill_txt = m.group(2).strip()
            skills = find_skills(skill_txt) or [skill_txt.title()]
            parsed.append({"skill": skills[0], "min_years": years, "raw": raw})
        else:
            skills = find_skills(raw)
            parsed.append({"skill": skills[0] if skills else raw,
                           "min_years": 0, "raw": raw})
    return parsed


class JobMatcher:
    def __init__(self, rag: ResumeRAG):
        self.rag = rag

    # --------------------------------------------------------------
    def match(self, job_description: str, k: int = 10,
              must_have: Optional[List[str]] = None,
              pool: int = 60) -> Dict[str, Any]:
        jd_skills = find_skills(job_description)
        must = parse_must_have(must_have or [])

        # 1) Semantic retrieval over a wide pool of chunks.
        hits = self.rag.search(job_description, k=pool)

        # 2) Aggregate chunk hits per candidate.
        agg: Dict[str, Dict[str, Any]] = {}
        for h in hits:
            cid = h["metadata"]["candidate_id"]
            entry = agg.setdefault(cid, {"chunks": [], "best": 0.0})
            entry["chunks"].append(h)
            entry["best"] = max(entry["best"], h["score"])

        max_best = max((e["best"] for e in agg.values()), default=1.0) or 1.0

        results = []
        for cid, entry in agg.items():
            cand = self.rag.candidates.get(cid, {})
            cand_skills = cand.get("skills", [])
            cand_years = cand.get("experience_years", 0)

            # --- hybrid scoring ---------------------------------------
            semantic = entry["best"] / max_best                     # 0..1
            matched_skills = [s for s in jd_skills if s in cand_skills]
            keyword = (len(matched_skills) / len(jd_skills)) if jd_skills else 0.0
            # weighted blend; skills matter as much as semantic proximity
            score01 = 0.55 * semantic + 0.45 * keyword
            match_score = int(round(100 * score01))

            # --- must-have filtering ----------------------------------
            unmet = []
            for req in must:
                has_skill = req["skill"] in cand_skills
                meets_years = cand_years >= req["min_years"]
                if not (has_skill and meets_years):
                    unmet.append(req["raw"])
            if unmet:
                continue  # candidate filtered out

            # --- excerpts + reasoning ---------------------------------
            top_chunks = sorted(entry["chunks"], key=lambda c: c["score"],
                                reverse=True)[:2]
            excerpts = [self._trim(c["document"]) for c in top_chunks]
            matched_sections = [c["metadata"]["section"] for c in top_chunks]
            reasoning = self._reason(cand, matched_skills, jd_skills,
                                     matched_sections, semantic)

            results.append({
                "candidate_name": cand.get("candidate_name", cid),
                "resume_path": cand.get("resume_path", ""),
                "match_score": match_score,
                "matched_skills": matched_skills,
                "relevant_excerpts": excerpts,
                "reasoning": reasoning,
                "_experience_years": cand_years,
            })

        results.sort(key=lambda r: r["match_score"], reverse=True)
        for r in results:
            r.pop("_experience_years", None)
        return {"job_description": job_description.strip(),
                "top_matches": results[:k]}

    # --------------------------------------------------------------
    @staticmethod
    def _trim(text: str, limit: int = 220) -> str:
        text = " ".join(text.split())
        return text if len(text) <= limit else text[:limit].rstrip() + "…"

    @staticmethod
    def _reason(cand, matched_skills, jd_skills, sections, semantic) -> str:
        name = cand.get("candidate_name", "Candidate")
        years = cand.get("experience_years", 0)
        title = cand.get("title", "")
        parts = [f"{name} ({title}, {years}y experience)"]
        if matched_skills:
            parts.append("matches required skills [" +
                         ", ".join(matched_skills) + "]")
        missing = [s for s in jd_skills if s not in matched_skills]
        if missing:
            parts.append("gaps [" + ", ".join(missing) + "]")
        if sections:
            parts.append("strongest overlap in " +
                         "/".join(dict.fromkeys(sections)).lower() + " section")
        parts.append(f"semantic similarity {semantic:.2f}")
        return "; ".join(parts) + "."


# ==========================================================================
# CLI
# ==========================================================================
def _load_job_text(args) -> str:
    if args.job:
        with open(args.job, "r", encoding="utf-8") as fh:
            return fh.read()
    if args.text:
        return " ".join(args.text)
    raise SystemExit("Provide a job description (positional text or --job FILE).")


def main() -> None:
    parser = argparse.ArgumentParser(description="Match a job description to resumes.")
    parser.add_argument("text", nargs="*", help="Job description text.")
    parser.add_argument("--job", help="Path to a job description file.")
    parser.add_argument("--resumes", default=None, help="Resume directory.")
    parser.add_argument("--must", action="append", default=[],
                        help="Must-have requirement, e.g. '5+ years Python' "
                             "(repeatable).")
    parser.add_argument("-k", type=int, default=10, help="Top-K matches.")
    args = parser.parse_args()

    here = os.path.dirname(os.path.abspath(__file__))
    resume_dir = args.resumes or os.path.join(here, "data", "resumes")

    rag = ResumeRAG()
    rag.build_index(resume_dir)
    matcher = JobMatcher(rag)

    jd = _load_job_text(args)
    # Auto-detect "Must-have:" line inside the JD file if none passed.
    must = list(args.must)
    m = re.search(r"must[- ]?have[s]?:\s*(.+)", jd, re.I)
    if m and not must:
        must = [x.strip() for x in re.split(r"[;,]", m.group(1)) if x.strip()]

    result = matcher.match(jd, k=args.k, must_have=must)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
