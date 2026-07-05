# Assignment 2 — LLM Function Calling: File System Tools

An LLM file assistant that exposes four file-system tools to **Claude** via
function calling, so natural-language queries drive real file operations.

See the full brief in [`Assignment-Brief.md`](./Assignment-Brief.md).

---

## Highlights

- **Part A** — `fs_tools.py`: `read_file`, `list_files`, `write_file`,
  `search_in_file`, each returning a **structured** result and failing
  gracefully (never raising to the caller/LLM).
- **Part B** — `llm_file_assistant.py`: the tools are registered with Claude
  (`claude-opus-4-8`) using the Anthropic SDK's tool runner (`@beta_tool` +
  `client.beta.messages.tool_runner`). Claude decides which tools to call.
- **Runs with no API key.** A deterministic intent router calls the *same*
  tools offline, so the assignment is fully runnable and testable without
  credentials. Every tool call is printed, so the function-calling is visible.
- **Sample data**: 8 dummy resumes. **Tests**: 11 passing.

---

## Quick start

```bash
cd AI-Assignments/Assignment-2-LLM-File-Tools

# (optional) create the sample resumes if they aren't present
python sample_data/make_samples.py

# 1) Interactive assistant (offline mode — no key needed)
python llm_file_assistant.py

# 2) One-shot queries
python llm_file_assistant.py "Read all resumes in the resumes folder"
python llm_file_assistant.py "Find resumes mentioning Python experience"
python llm_file_assistant.py "Create a summary file for resume_john_doe.txt"

# 3) Run the tests
python tests/test_fs_tools.py        # or: pytest tests/ -q

# 4) Exercise the tools directly
python fs_tools.py
```

### Enabling real LLM mode (Claude drives the tools)

```bash
pip install -r requirements.txt        # installs anthropic (+ pypdf, python-docx)
export ANTHROPIC_API_KEY=sk-ant-...
python llm_file_assistant.py "Find resumes mentioning Python and summarize the best one"
```

With the key set, the banner shows `Mode: LLM   Model: claude-opus-4-8` and
Claude plans the tool calls itself. Without it, the banner shows
`Mode: offline (heuristic)` and the router handles the example queries.

---

## Project layout

```
Assignment-2-LLM-File-Tools/
├── Assignment-Brief.md         # the assignment requirements
├── fs_tools.py                 # ★ Part A: the four file-system tools
├── llm_file_assistant.py       # ★ Part B: Claude tool-calling + CLI + offline router
├── requirements.txt
├── sample_data/
│   ├── make_samples.py         # regenerates the dummy resumes
│   └── resumes/                # 8 dummy resume .txt files
└── tests/
    └── test_fs_tools.py        # 11 tests (tools + assistant routing)
```

---

## Part A — the tools (`fs_tools.py`)

| Tool | Signature | Returns |
|------|-----------|---------|
| Read | `read_file(filepath)` | `{success, content, metadata, error}` — TXT/PDF/DOCX text + metadata (size, modified, word/char/line counts) |
| List | `list_files(directory, extension=None)` | list of `{name, path, size_bytes, modified, ...}`, extension-filtered |
| Write | `write_file(filepath, content)` | `{success, filepath, bytes_written, error}`, creates parent dirs |
| Search | `search_in_file(filepath, keyword)` | `{success, match_count, matches:[{line_number, context}], error}`, case-insensitive |

- **Errors are values, not exceptions** — a missing file, unsupported type, or
  missing optional parser returns an `error` field so the LLM can react and
  recover instead of crashing.
- **PDF/DOCX** reading uses `pypdf` / `python-docx` when installed; otherwise a
  clear error is returned. TXT/MD/CSV/LOG work with zero dependencies.

## Part B — LLM integration (`llm_file_assistant.py`)

Each tool is wrapped with the Anthropic `@beta_tool` decorator (schema derived
from the function signature + docstring) and passed to
`client.beta.messages.tool_runner(...)`, which runs the agentic loop: Claude
requests tools → the runner executes them → results feed back → repeat until
Claude answers. A system prompt tells Claude to default to the sample
`resumes/` folder and to prefer tools over guessing.

Example queries it handles (offline and with a key):
- *"Read all resumes in the resumes folder"*
- *"Find resumes mentioning Python experience"*
- *"Create a summary file for resume_john_doe.txt"*

---

## Deliverables checklist

- [x] Source code with documentation (`fs_tools.py`, `llm_file_assistant.py`)
- [x] `requirements.txt`
- [x] Sample data: 8 dummy resumes (`sample_data/resumes/`)
- [x] `README.md` with setup and usage
- [x] Tests (11 passing) — bonus over the brief
- [ ] Demo video (2–3 min) — record `llm_file_assistant.py` handling the three
      example queries (the printed `→ tool: ...` lines show the function calling)
```
