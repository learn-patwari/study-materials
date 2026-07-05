# Agentic Resume Matching System

A **LangGraph** agent that matches candidate resumes to a job description,
supports a **conversational** interface with iterative refinement, and produces
**explainable, multi-round** hire/no-hire recommendations.

This is the implementation for the *Agentic Resume Matching* assignment
(see [`../Agent-Resume-Matching-Assignment.md`](../Agent-Resume-Matching-Assignment.md)).

---

## Highlights

- **Real LangGraph state machine** with the exact required workflow and a
  genuine human-in-the-loop feedback edge (`interrupt()` + `MemorySaver`).
- **Runs fully offline** — deterministic heuristics mean no API key is needed
  to run, grade, or test. Drop in `OPENAI_API_KEY` to add LLM-polished narrative.
- **Zero required extra deps** beyond `langgraph` / `langchain-core`. RAG uses a
  built-in pure-Python TF-IDF (upgrades to scikit-learn automatically if present).
- **100 synthetic resumes** generated deterministically and committed as data.
- **8 passing end-to-end conversation-flow tests.**

---

## Quick start

```bash
cd AI-Assignments/resume-matching-agent
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# 1) Chat interface
python cli.py

# 2) One-shot graph demo (pipeline + one refinement)
python matching_agent.py

# 3) Run the test scenarios
python tests/test_scenarios.py         # or: pytest tests/ -q

# 4) Regenerate the state-machine diagram
python diagrams/render_diagram.py
```

> The resume corpus (`data/resumes.json`) is committed. If deleted it is
> regenerated deterministically (`python data_store.py`).

---

## Project layout

```
resume-matching-agent/
├── matching_agent.py      # ★ LangGraph agent: AgentState, nodes, graph, wrapper
├── tools.py               # extract_requirements, compare_candidates,
│                          #   generate_interview_questions, ranking, screening,
│                          #   file-system tools, LangChain tool wrappers
├── rag.py                 # RAG search (TF-IDF cosine; sklearn optional)
├── llm.py                 # optional LLM narrative (OpenAI, best-effort)
├── data_store.py          # deterministic 100-resume dataset + loaders
├── cli.py                 # conversational chat interface
├── tests/test_scenarios.py# 5+ conversation-flow tests (8 total)
├── diagrams/
│   ├── state_machine.md   # rendered Mermaid diagram + node docs
│   ├── state_machine.mmd  # generated Mermaid source
│   └── render_diagram.py  # regenerate from the live graph
├── data/
│   ├── resumes.json       # 100 synthetic candidates
│   └── job_descriptions/senior_frontend_engineer.md
├── DEMO.md                # 5–6 min demo script / walkthrough
└── requirements.txt
```

---

## How it maps to the assignment

### Part A — Agent Architecture (40%)

- **`matching_agent.py`** built with LangGraph.
- **Agent State** (`AgentState`): conversation history (`messages`), the
  requirements understanding (`requirements`), and the shortlist **plus
  reasoning** (`shortlist`, each row carries a `reasoning` string).
- **Graph structure** — exactly:
  `START → Parse JD → Extract Requirements → Search Resumes → Rank Candidates
  → Generate Report → Human Feedback Loop → END` (see `diagrams/state_machine.md`).
- **Tools available to the agent**:
  - file-system tools — `list_resumes`, `read_resume`, `read_job_description`;
  - RAG search — `rag_search`;
  - `extract_requirements(jd)` — must-have vs nice-to-have + min years;
  - `compare_candidates(candidate_ids)` — head-to-head;
  - `generate_interview_questions(candidate_id)` — screening questions.
  All are also exposed as LangChain tools via `tools.build_langchain_tools()`.

### Part B — Interactive Features (30%)

- **Conversational interface** (`cli.py`) accepting natural language:
  - *"Find me candidates with React and 3+ years experience"*
  - *"Compare the top 3 matches side by side"*
  - *"Why did John rank higher than Jane?"* (`why C001 vs C002`)
- **Iterative refinement**: *"require Next.js and 5+ years"* loops back through
  the graph, re-ranks, and the report prints a **CHANGES SINCE LAST RANKING**
  section (new / dropped / moved candidates).

### Part C — Advanced Capabilities (30%)

- **Multi-round screening** (`agent.screen()` / `screen` command):
  Round 1 top-10 of 100 → Round 2 deep analysis → Round 3 hire/no-hire.
- **Explainability**: per-candidate strengths, gaps, and improvement
  suggestions for borderline candidates; every ranking carries a reasoning
  string; `why` produces a head-to-head explanation.

### Submission checklist

- [x] LangGraph-based agent implementation
- [x] State-machine diagram (`diagrams/state_machine.md`, regenerable)
- [x] Chat interface (CLI)
- [x] 5+ test scenarios (`tests/test_scenarios.py` — 8 scenarios)
- [x] Demo video — [`demo/resume_matching_agent_demo.webm`](./demo/resume_matching_agent_demo.webm)
      (~73s, auto-generated from real CLI output — see `demo/README.md`)

---

## Design notes

- **Why heuristics + optional LLM?** The graph, state, and tool orchestration —
  what the assignment grades — are identical with or without an LLM. Keeping the
  default path deterministic makes the system reproducible and testable, while
  `OPENAI_API_KEY` unlocks nicer prose for explanations, interview questions,
  and recommendations.
- **Scoring**: `0.55·must + 0.15·nice + 0.15·years + 0.15·RAG`, with a penalty
  when must-have skills are missing or the experience bar isn't met. See
  `tools.score_candidate`.
