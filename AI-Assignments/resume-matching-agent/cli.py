"""
cli.py
======
Conversational chat interface for the resume-matching agent.

Run:
    python cli.py

Natural-language commands supported (Part B / Part C):
  - "find candidates with React and 3+ years"   -> (re)rank on new criteria
  - "require Next.js and 5+ years"               -> iterative refinement
  - "compare C001 C002 C003"                     -> side-by-side comparison
  - "compare top 3"                              -> compare current top 3
  - "why did C001 rank higher than C002"         -> ranking explanation
  - "questions for C003"                         -> interview questions
  - "screen"  /  "deep dive"                     -> multi-round screening (Part C)
  - "show" / "shortlist"                         -> reprint current shortlist
  - "reset"                                      -> start a fresh session
  - "help"                                       -> command help
  - "quit" / "exit"                              -> leave

The interface is intentionally dependency-free (plain stdin/stdout) so it runs
anywhere. It delegates all reasoning to matching_agent.ResumeMatchingAgent.
"""

from __future__ import annotations

import re
import sys
from typing import List, Optional

from matching_agent import ResumeMatchingAgent
from llm import llm_available

_ID_RE = re.compile(r"\bC\d{3}\b", re.I)
_TOPN_RE = re.compile(r"top\s+(\d+)", re.I)

BANNER = r"""
+------------------------------------------------------------------+
|          Agentic Resume Matching System  (LangGraph)             |
|   Type 'help' for commands, 'quit' to exit.                      |
+------------------------------------------------------------------+
"""

HELP = """
Commands
--------
  find <criteria>            e.g. "find candidates with React and 3+ years"
  require <criteria>         refine current search, e.g. "require Next.js and 5+ years"
  compare <ids | top N>      e.g. "compare C001 C002"  or  "compare top 3"
  why <idA> vs <idB>         e.g. "why did C001 rank higher than C002"
  questions for <id>         generate interview questions for a candidate
  screen                     run 3-round screening on the current top 10
  show                       reprint the current shortlist
  reset                      start a fresh session
  help                       show this help
  quit / exit                leave
"""


def _ids(text: str) -> List[str]:
    return [m.upper() for m in _ID_RE.findall(text)]


def _print_shortlist(state) -> None:
    print(state.get("report", "(no shortlist yet)"))


def _print_comparison(cmp) -> None:
    if "error" in cmp:
        print(cmp["error"])
        return
    print("\nHead-to-head comparison")
    print("-" * 60)
    for r in cmp["candidates"]:
        flag = "  <-- best fit" if r["id"] == cmp["winner"] else ""
        print(f"  {r['name']:20} [{r['id']}]  score={r['score']:.3f}"
              f"  {r['years_experience']}y{flag}")
        if r["must_missing"]:
            print(f"      missing must-haves: {', '.join(r['must_missing'])}")
    print()


def _print_screen(rounds) -> None:
    print("\n=== Round 1: Initial screen (top 10) ===")
    for r in rounds["round1_screen"]:
        print(f"  {r['name']:20} [{r['id']}]  score={r['score']:.3f}")
    print("\n=== Round 2: Deep analysis ===")
    for a in rounds["round2_deep_analysis"][:10]:
        print(f"\n  {a['name']} [{a['id']}] — score {a['score']:.3f}")
        print(f"    strengths: {', '.join(a['strengths']) or '—'}")
        print(f"    gaps:      {', '.join(a['gaps']) or '—'}")
        for s in a["improvement_suggestions"]:
            print(f"    suggest:   {s}")
    print("\n=== Round 3: Hire / No-hire recommendations ===")
    for rec in rounds["round3_recommendations"]:
        print(f"  {rec['name']:20} [{rec['id']}]  {rec['decision']:12} "
              f"(confidence: {rec['confidence']})")
        print(f"      {rec['rationale']}")
    print()


def handle(agent: ResumeMatchingAgent, text: str) -> Optional[str]:
    """Handle one user turn. Returns a control signal ('reset'/'quit') or None."""
    low = text.strip().lower()

    if low in ("quit", "exit"):
        return "quit"
    if low in ("help", "?"):
        print(HELP)
        return None
    if low == "reset":
        return "reset"
    if low in ("show", "shortlist", "list"):
        _print_shortlist(agent.snapshot())
        return None

    # why did A rank higher than B
    if low.startswith("why") or "rank higher" in low or "ranked higher" in low:
        ids = _ids(text)
        if len(ids) >= 2:
            print("\n" + agent.why(ids[0], ids[1]) + "\n")
        else:
            print("Please reference two candidate ids, e.g. 'why C001 vs C002'.")
        return None

    # comparison
    if low.startswith("compare") or "side by side" in low:
        ids = _ids(text)
        m = _TOPN_RE.search(text)
        if not ids and m:
            n = int(m.group(1))
            ids = [r["id"] for r in agent.shortlist[:n]]
        elif not ids and "top" in low:
            ids = [r["id"] for r in agent.shortlist[:3]]
        if len(ids) < 2:
            print("Need at least two candidates to compare.")
            return None
        _print_comparison(agent.compare(ids))
        return None

    # interview questions
    if "question" in low:
        ids = _ids(text)
        if not ids:
            print("Reference a candidate id, e.g. 'questions for C003'.")
            return None
        qs = agent.interview_questions(ids[0])
        print(f"\nInterview questions for {ids[0].upper()}:")
        for i, q in enumerate(qs, 1):
            print(f"  {i}. {q}")
        print()
        return None

    # multi-round screening
    if low in ("screen", "deep dive", "deep-dive", "screening", "final round"):
        if not agent.shortlist:
            print("Run a search first (e.g. 'find candidates with React').")
            return None
        _print_screen(agent.screen())
        return None

    # refinement of an existing search
    if agent.shortlist and (low.startswith("require") or low.startswith("also")
                            or low.startswith("add ") or low.startswith("refine")):
        print("\n[refining search based on your feedback...]\n")
        _print_shortlist(agent.refine(text))
        return None

    # otherwise: treat as a (new or first) search query
    print("\n[searching...]\n")
    if agent.shortlist:
        _print_shortlist(agent.refine(text))
    else:
        _print_shortlist(agent.start(query=text))
    return None


def main() -> None:
    print(BANNER)
    print(f"LLM narrative: {'ON' if llm_available() else 'OFF (heuristic mode)'}")
    agent = ResumeMatchingAgent()
    # Kick off with the default JD so there's an initial shortlist to explore.
    print("\n[loading default job description: Senior Frontend Engineer...]\n")
    _print_shortlist(agent.start())
    print("\nRefine, compare, ask 'why', or 'screen'. Type 'help' for commands.\n")

    while True:
        try:
            text = input("you > ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye.")
            break
        if not text:
            continue
        signal = handle(agent, text)
        if signal == "quit":
            print("Goodbye.")
            break
        if signal == "reset":
            agent = ResumeMatchingAgent(thread_id=f"session-{id(object())}")
            print("\n[session reset]\n")
            _print_shortlist(agent.start())


if __name__ == "__main__":
    main()
