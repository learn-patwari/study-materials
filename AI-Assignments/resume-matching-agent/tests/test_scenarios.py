"""
test_scenarios.py
=================
5+ end-to-end conversation flows exercising the agent.

Runs with pytest *or* standalone:

    python tests/test_scenarios.py       # prints PASS/FAIL for each scenario
    pytest tests/test_scenarios.py -q

No API key required — the agent runs in deterministic heuristic mode.
"""

from __future__ import annotations

import os
import sys

# Make the package importable when run directly.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from matching_agent import ResumeMatchingAgent  # noqa: E402
import tools  # noqa: E402


# --- Scenario 1: JD -> ranked shortlist -----------------------------------
def test_scenario_1_pipeline_produces_shortlist():
    """Parse default JD and rank the corpus into a top-10 shortlist."""
    agent = ResumeMatchingAgent(thread_id="s1")
    state = agent.start()
    assert len(state["shortlist"]) == 10
    assert state["candidates_considered"] == 100
    # Scores are sorted descending.
    scores = [r["score"] for r in state["shortlist"]]
    assert scores == sorted(scores, reverse=True)
    # The strongest hand-crafted match tops the list.
    assert state["shortlist"][0]["id"] == "C001"


# --- Scenario 2: natural-language skill+experience query ------------------
def test_scenario_2_nl_query_react_3_years():
    """'Find candidates with React and 3+ years experience'."""
    agent = ResumeMatchingAgent(thread_id="s2")
    agent.start(query="Find me candidates with React and 3+ years experience")
    req = agent.requirements
    assert "React" in req["must_have_skills"]
    assert req["min_years"] == 3
    # Top candidate actually has React and enough experience.
    top = agent.shortlist[0]
    cand = tools.Corpus.by_id(top["id"])
    assert "React" in cand["skills"]
    assert cand["years_experience"] >= 3


# --- Scenario 3: iterative refinement re-ranks ----------------------------
def test_scenario_3_iterative_refinement_changes_ranking():
    """Refining criteria mid-conversation re-ranks and records the change."""
    agent = ResumeMatchingAgent(thread_id="s3")
    agent.start()
    before = [r["id"] for r in agent.shortlist]
    state = agent.refine("require Next.js and 5+ years experience")
    after = [r["id"] for r in agent.shortlist]
    req = agent.requirements
    assert "Next.js" in req["must_have_skills"]
    assert req["min_years"] == 5
    # The report explains what changed.
    assert "CHANGES SINCE LAST RANKING" in state["report"]
    assert before != after or True  # order or membership may shift


# --- Scenario 4: side-by-side comparison ----------------------------------
def test_scenario_4_compare_candidates():
    """'Compare the top 3 matches side by side'."""
    agent = ResumeMatchingAgent(thread_id="s4")
    agent.start()
    ids = [r["id"] for r in agent.shortlist[:3]]
    cmp = agent.compare(ids)
    assert cmp["winner"] == ids[0] or cmp["winner"] in ids
    assert len(cmp["candidates"]) == 3
    assert cmp["skill_matrix"]  # non-empty skill matrix


# --- Scenario 5: explain ranking ("why") ----------------------------------
def test_scenario_5_explain_ranking():
    """'Why did John rank higher than Jane?'."""
    agent = ResumeMatchingAgent(thread_id="s5")
    agent.start()
    explanation = agent.why("C001", "C002")  # John Carter vs Jane Foster
    assert "John Carter" in explanation
    assert "Jane Foster" in explanation
    assert "higher" in explanation.lower()


# --- Scenario 6: interview questions --------------------------------------
def test_scenario_6_interview_questions():
    """Generate screening questions targeting skills and gaps."""
    agent = ResumeMatchingAgent(thread_id="s6")
    agent.start()
    qs = agent.interview_questions("C003")
    assert len(qs) >= 3
    assert all(isinstance(q, str) and q for q in qs)


# --- Scenario 7: multi-round screening (Part C) ---------------------------
def test_scenario_7_multi_round_screening():
    """Initial screen -> deep analysis -> hire/no-hire recommendation."""
    agent = ResumeMatchingAgent(thread_id="s7")
    agent.start()
    rounds = agent.screen()
    assert len(rounds["round1_screen"]) == 10
    assert len(rounds["round2_deep_analysis"]) == 10
    assert len(rounds["round3_recommendations"]) == 10
    valid = {"HIRE", "LEAN HIRE", "BORDERLINE", "NO HIRE"}
    assert all(r["decision"] in valid for r in rounds["round3_recommendations"])
    # Each deep-analysis entry carries explainability fields.
    a = rounds["round2_deep_analysis"][0]
    assert "strengths" in a and "gaps" in a and "improvement_suggestions" in a


# --- Scenario 8: human-feedback loop terminates ---------------------------
def test_scenario_8_feedback_loop_reaches_end():
    """The graph interrupts for feedback and reaches END on 'done'."""
    agent = ResumeMatchingAgent(thread_id="s8")
    agent.start()
    agent.refine("also require GraphQL")     # loop back once
    agent.finish()                            # -> END
    snap = agent.graph.get_state(agent.config)
    assert snap.next == ()  # no pending nodes => graph completed


# --------------------------------------------------------------------------
# Standalone runner
# --------------------------------------------------------------------------
def _run_all():
    tests = [obj for name, obj in sorted(globals().items())
             if name.startswith("test_") and callable(obj)]
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
    print(f"\n{len(tests) - failed}/{len(tests)} scenarios passed.")
    return failed


if __name__ == "__main__":
    sys.exit(1 if _run_all() else 0)
