# Assignment 3 — Resume RAG & Job Matching Engine

A retrieval-augmented resume search system: chunk and embed resumes into a
vector store, then match job descriptions to candidates with **hybrid
semantic + keyword** search, 0–100 scoring, and must-have filtering.

See the full brief in [`Assignment-Brief.md`](./Assignment-Brief.md).

---

## Highlights

- **Part A — `resume_rag.py`**: section-aware chunking, pluggable embeddings,
  a pluggable vector store, and metadata extraction (name / skills / experience
  years / education) stored alongside every vector for filtering.
- **Part B — `job_matcher.py`**: JD → embedding → top-K retrieval → hybrid
  re-scoring → **exact output schema** with match score, matched skills,
  relevant excerpts, and reasoning; plus must-have requirement filtering.
- **Runs fully offline** — a pure-Python **TF-IDF** embedder + **in-memory
  cosine** vector store need no deps or keys. It **auto-upgrades** to
  `sentence-transformers` (HuggingFace) and/or `chromadb` if installed, with
  zero code changes.
- **Dataset**: 33 resumes across 11 roles + 6 job descriptions + relevance
  labels. **Metrics**: precision / recall / MRR + latency. **Tests**: 9 passing.

---

## Quick start

```bash
cd AI-Assignments/Assignment-3-Resume-RAG

# 1) Generate the dataset (33 resumes, 6 JDs, ground truth)
python data_gen.py

# 2) Build the index and run a sample query
python resume_rag.py

# 3) Match a job description (prints the required JSON)
python job_matcher.py --job data/jobs/job_backend_python.txt --must "5+ years Python" -k 5

# 4) Performance metrics (retrieval accuracy + latency)
python evaluate.py

# 5) Tests
python tests/test_rag.py        # or: pytest tests/ -q

# 6) Notebook (experimentation + analysis)
jupyter notebook resume_rag_experiments.ipynb
```

### Upgrading the backends (optional)

```bash
pip install sentence-transformers chromadb   # dense embeddings + persistent DB
```

No code changes needed — `resume_rag.get_embedder()` / `get_vector_store()`
detect and use them automatically. Force offline mode with
`ResumeRAG(prefer_embedder="tfidf")`.

---

## Architecture

```
data/resumes/*.txt
        │  load  (file-system loader — mirrors Milestone-1 read_file)
        ▼
 split_sections()                 SUMMARY / SKILLS / EXPERIENCE / EDUCATION
        │  chunk_resume()         → one chunk per section (boundaries preserved)
        ▼
 embed chunks                     TF-IDF (default) │ sentence-transformers
        ▼
 vector store  + metadata         in-memory cosine (default) │ ChromaDB
        ▲
        │  search(query, k, where=…)   ← semantic + metadata filter
JobMatcher.match(jd, must_have)   ← hybrid re-score, 0-100, must-have filter
        ▼
 { job_description, top_matches: [ {candidate_name, resume_path, match_score,
   matched_skills, relevant_excerpts, reasoning}, … ] }
```

## Project layout

```
Assignment-3-Resume-RAG/
├── Assignment-Brief.md
├── resume_rag.py                 # ★ Part A: chunking, embeddings, vector store, metadata
├── job_matcher.py                # ★ Part B: hybrid search, scoring, filtering, JSON output
├── evaluate.py                   # retrieval accuracy + latency metrics
├── data_gen.py                   # builds the dataset + ground truth
├── resume_rag_experiments.ipynb  # experimentation & analysis notebook
├── requirements.txt
├── data/
│   ├── resumes/                  # 33 resumes (11 roles × 3)
│   ├── jobs/                     # 6 job descriptions
│   └── ground_truth.json         # relevance labels for metrics
└── tests/test_rag.py             # 9 tests
```

---

## How it maps to the assignment

### Part A — RAG System Setup (50%)
- **Document processing**: `load_resume` (TXT/PDF/DOCX) → `split_sections` +
  `chunk_resume` (intelligent, section-preserving) → `get_embedder().embed` →
  `get_vector_store().add`.
- **Metadata extraction**: `extract_metadata` pulls Name, Title, Skills,
  Experience Years, Education; stored on every chunk for filtering
  (`search(..., where={"role": ...})`).

### Part B — Job Matching Engine (50%)
- **Semantic search**: JD embedded and matched; top-K (K=10) candidates.
- **Hybrid search**: semantic proximity blended with exact critical-skill
  keyword overlap (`0.55·semantic + 0.45·skill_overlap`).
- **Ranking & scoring**: 0–100 `match_score`, `matched_skills`,
  `relevant_excerpts` (matched sections), and a `reasoning` string.
- **Must-have filtering**: `parse_must_have("5+ years Python")` →
  `{skill, min_years}`; candidates failing any requirement are dropped.
- **Output**: exactly the schema in the brief.

### Deliverables checklist
- [x] Complete RAG implementation
- [x] Dataset: 33 resumes (≥30) + 6 job descriptions (≥5)
- [x] Jupyter notebook with experimentation and analysis
- [x] Performance metrics: retrieval accuracy + latency (`evaluate.py`)
- [x] Tests (9 passing) — bonus over the brief
- [ ] Demo video (3–4 min) — walk through `resume_rag.py`, `job_matcher.py`, and `evaluate.py`

---

## Measured performance (offline TF-IDF backend)

| Metric | Value |
|---|---|
| MRR (first correct role) | **1.00** |
| precision@relevant (P@3) | **~0.75** |
| recall@10 | **~0.72** |
| index build (33 resumes) | **~15 ms** |
| query latency (mean) | **~2.5 ms** |

> Only 3 candidates are relevant per job, so `precision@10` is capped at 0.3 by
> construction — `precision@relevant` and MRR are the meaningful reads. Dense
> `sentence-transformers` embeddings improve recall on paraphrased queries.
```
