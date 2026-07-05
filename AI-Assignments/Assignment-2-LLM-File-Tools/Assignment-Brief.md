# Assignment 2: LLM Function Calling — File System Tools

## Brief

### Learning Objectives
- Understand LLM function calling / tool use
- Implement structured tool interfaces
- Handle file I/O operations programmatically
- Parse and validate documents

---

## Assignment Requirements

### Part A: Core File System Tools (60%)

Create a Python module `fs_tools.py` with the following tools:

#### `read_file(filepath: str) -> dict`
- Read resume files (PDF, TXT, DOCX)
- Extract text content
- Return structured response with content and metadata
- Handle errors gracefully

#### `list_files(directory: str, extension: str = None) -> list`
- List all files in a directory
- Filter by extension (e.g., `.pdf`, `.txt`)
- Return file metadata (name, size, modified date)

#### `write_file(filepath: str, content: str) -> dict`
- Write content to file
- Create directories if needed
- Return success/failure status

#### `search_in_file(filepath: str, keyword: str) -> dict`
- Search for keywords in file content
- Return matches with context (surrounding text)
- Case-insensitive search

---

### Part B: LLM Integration (40%)

Create `llm_file_assistant.py`:
- Integrate tools with an LLM (OpenAI / Anthropic / etc.)
- LLM should be able to call tools based on user queries

Example queries:
- "Read all resumes in the resumes folder"
- "Find resumes mentioning Python experience"
- "Create a summary file for resume_john_doe.pdf"

---

## Submission Guidelines

### Deliverables
- Source code with proper documentation
- `requirements.txt` with dependencies
- Sample data: 5–10 dummy resume files
- `README.md` with setup and usage instructions
- Demo video (2–3 minutes) showing tool calling in action
