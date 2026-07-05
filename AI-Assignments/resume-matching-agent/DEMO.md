# Demo Script (5–6 minutes)

A walkthrough to record for the demo-video deliverable. Each step lists what to
say and the exact command / input to type. Total runtime ≈ 5–6 min.

Setup (before recording):
```bash
cd AI-Assignments/resume-matching-agent
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

---

## 0:00 – 0:40 · Intro & architecture (show the diagram)

> "This is a LangGraph agent that matches resumes to a job description. Here's
> the state machine." Open `diagrams/state_machine.md` and point at the graph:
> `START → Parse JD → Extract Requirements → Search Resumes → Rank Candidates →
> Generate Report → Human Feedback Loop → END`.

Show it's generated from the live graph:
```bash
python diagrams/render_diagram.py   # writes diagrams/state_machine.mmd
```

---

## 0:40 – 1:30 · Launch the agent (Parse JD → Rank → Report)

```bash
python cli.py
```

> "On start it parses the default Senior Frontend Engineer JD, extracts must-have
> vs nice-to-have requirements, RAG-searches 100 resumes, and ranks a top-10
> shortlist. Notice each candidate has a **reasoning** line — matched must-haves,
> gaps, bonus skills, and experience vs the requirement."

---

## 1:30 – 2:40 · Conversational query (Part B)

Type:
```
find candidates with React and 3+ years experience
```
> "Natural language in — the agent parsed 'React' as a must-have and '3+ years'
> as the experience bar, then re-ranked."

Type:
```
compare top 3
```
> "Side-by-side comparison with a skill matrix and a 'best fit' flag."

Type:
```
why did C001 rank higher than C002
```
> "The agent explains the ranking head-to-head: experience gap, must-have
> coverage, and which unique skills each brings."

---

## 2:40 – 3:40 · Iterative refinement (Part B)

Type:
```
require Next.js and 5+ years
```
> "Mid-conversation I tighten the criteria. The graph **loops back** through
> Extract Requirements → re-ranks → and the report shows a **CHANGES SINCE LAST
> RANKING** section: who's newly in, who dropped, who moved. That closed loop is
> the human-feedback edge in the state machine."

---

## 3:40 – 5:00 · Multi-round screening (Part C)

Type:
```
screen
```
> "Three rounds: Round 1 is the top-10 screen; Round 2 is a deep analysis with
> strengths, gaps, and improvement suggestions for borderline candidates; Round 3
> is a hire / lean-hire / borderline / no-hire recommendation with confidence and
> a rationale for each."

Optionally:
```
questions for C003
```
> "And it can generate targeted screening questions — grounded in the
> candidate's actual skills and their gaps against this role."

---

## 5:00 – 5:45 · Reasoning & tests

Exit the CLI (`quit`), then:
```bash
python tests/test_scenarios.py
```
> "Eight end-to-end conversation-flow tests — pipeline, NL query, refinement,
> comparison, ranking explanation, interview questions, multi-round screening,
> and that the feedback loop actually reaches END. All green, and all offline —
> no API key required."

---

## 5:45 – 6:00 · Wrap

> "Everything the agent decides is explainable and traceable through the graph
> state. Optionally, setting `OPENAI_API_KEY` layers LLM-written prose on top of
> the same deterministic reasoning."

### Tip
For a scripted, non-interactive capture you can pipe inputs:
```bash
printf '%s\n' \
  "find candidates with React and 3+ years experience" \
  "compare top 3" \
  "why did C001 rank higher than C002" \
  "require Next.js and 5+ years" \
  "screen" "quit" | python cli.py
```
