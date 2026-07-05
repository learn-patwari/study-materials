"""
llm_file_assistant.py
=====================
LLM integration for the file-system tools (Assignment 2, Part B).

The four tools in ``fs_tools`` are exposed to **Claude** via the Anthropic SDK's
tool runner. Claude decides which tool(s) to call based on a natural-language
query, the runner executes them, feeds results back, and loops until Claude has
an answer — classic LLM function calling.

    "Read all resumes in the resumes folder"
    "Find resumes mentioning Python experience"
    "Create a summary file for resume_john_doe.txt"

Runs in two modes:
  * **LLM mode** — when ``ANTHROPIC_API_KEY`` is set and ``anthropic`` is
    installed, Claude (``claude-opus-4-8``) drives the tools.
  * **Offline mode** — a small deterministic intent router calls the same tools,
    so the assignment is runnable and testable with no API key. Every tool call
    is printed either way, so you can see the function calling happen.

Usage:
    python llm_file_assistant.py                      # interactive chat
    python llm_file_assistant.py "Find resumes mentioning Python"   # one-shot
"""

from __future__ import annotations

import json
import os
import re
import sys
from typing import Any, Dict, List

import fs_tools

MODEL = os.getenv("ANTHROPIC_MODEL", "claude-opus-4-8")
HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_RESUME_DIR = os.path.join(HERE, "sample_data", "resumes")

SYSTEM_PROMPT = (
    "You are a helpful file-system assistant for a recruiter. You have tools to "
    "list files, read files (TXT/PDF/DOCX resumes), search within files, and "
    "write files. When the user refers to 'the resumes folder' and gives no path, "
    f"use '{DEFAULT_RESUME_DIR}'. Prefer calling tools over guessing. When asked "
    "to create a summary file, read the source first, then write a concise summary."
)


# ==========================================================================
# Tool call logging (so the function-calling is visible in the demo)
# ==========================================================================
def _log_call(name: str, **kwargs: Any) -> None:
    args = ", ".join(f"{k}={v!r}" for k, v in kwargs.items())
    print(f"  \033[36m→ tool: {name}({args})\033[0m")


# ==========================================================================
# Anthropic tool definitions (LLM mode)
# ==========================================================================
def _build_llm_tools():
    """Wrap the fs_tools functions as Anthropic beta tools."""
    from anthropic import beta_tool

    @beta_tool
    def list_files(directory: str, extension: str = "") -> str:
        """List files in a directory, optionally filtered by extension.

        Args:
            directory: The directory to list files from.
            extension: Optional extension filter such as ".pdf" or ".txt". Empty for all.
        """
        _log_call("list_files", directory=directory, extension=extension or None)
        result = fs_tools.list_files(directory, extension or None)
        return json.dumps(result)

    @beta_tool
    def read_file(filepath: str) -> str:
        """Read a resume/text file (TXT, PDF, or DOCX) and return content + metadata.

        Args:
            filepath: Path to the file to read.
        """
        _log_call("read_file", filepath=filepath)
        return json.dumps(fs_tools.read_file(filepath))

    @beta_tool
    def search_in_file(filepath: str, keyword: str) -> str:
        """Case-insensitively search a file for a keyword; returns matches with context.

        Args:
            filepath: File to search.
            keyword: Keyword or phrase to look for.
        """
        _log_call("search_in_file", filepath=filepath, keyword=keyword)
        return json.dumps(fs_tools.search_in_file(filepath, keyword))

    @beta_tool
    def write_file(filepath: str, content: str) -> str:
        """Write text content to a file, creating parent directories if needed.

        Args:
            filepath: Destination path.
            content: Text content to write.
        """
        _log_call("write_file", filepath=filepath, content=f"<{len(content)} chars>")
        return json.dumps(fs_tools.write_file(filepath, content))

    return [list_files, read_file, search_in_file, write_file]


# ==========================================================================
# The assistant
# ==========================================================================
class FileAssistant:
    """Natural-language front-end over the file-system tools."""

    def __init__(self) -> None:
        self.client = self._make_client()
        self.mode = "LLM" if self.client else "offline (heuristic)"

    @staticmethod
    def _make_client():
        if not os.getenv("ANTHROPIC_API_KEY"):
            return None
        try:
            import anthropic
            return anthropic.Anthropic()
        except Exception:
            return None

    # -- public entry point ----------------------------------------------
    def ask(self, query: str) -> str:
        if self.client:
            return self._ask_llm(query)
        return self._ask_offline(query)

    # -- LLM mode (Claude drives the tools) ------------------------------
    def _ask_llm(self, query: str) -> str:
        tools = _build_llm_tools()
        runner = self.client.beta.messages.tool_runner(
            model=MODEL,
            max_tokens=4096,
            system=SYSTEM_PROMPT,
            tools=tools,
            messages=[{"role": "user", "content": query}],
        )
        final_text: List[str] = []
        for message in runner:
            for block in message.content:
                if block.type == "text" and block.text.strip():
                    final_text.append(block.text.strip())
        return "\n".join(final_text) if final_text else "(no response)"

    # -- offline mode (deterministic intent router) ----------------------
    def _ask_offline(self, query: str) -> str:
        q = query.lower().strip()
        directory = self._resolve_dir(query)

        # Intent: create/generate a summary file for <resume>
        if ("summary" in q or "summarize" in q) and ("file" in q or "create" in q
                                                      or "for" in q):
            return self._offline_summary(query, directory)

        # Intent: find/search resumes mentioning <keyword>
        if any(w in q for w in ("find", "search", "mention", "which", "who has")):
            kw = self._extract_keyword(query)
            if kw:
                return self._offline_search(directory, kw)

        # Intent: read all resumes / read <file>
        if "read" in q or "list" in q or "show" in q or "all resumes" in q:
            # "all", "every", or "folder" => operate on the whole directory.
            broad = any(w in q for w in ("all ", "every", "folder", "each"))
            target = "" if broad else self._extract_filename(query)
            if target:
                path = self._find_file(directory, target)
                _log_call("read_file", filepath=path)
                r = fs_tools.read_file(path)
                if not r["success"]:
                    return f"Could not read {target}: {r['error']}"
                m = r["metadata"]
                return (f"{m['name']} — {m['word_count']} words, "
                        f"{m['size_bytes']} bytes.\n\n{r['content']}")
            return self._offline_list_and_read(directory)

        # Fallback: just list the folder.
        return self._offline_list_and_read(directory, read=False)

    # -- offline helpers -------------------------------------------------
    def _offline_list_and_read(self, directory: str, read: bool = True) -> str:
        _log_call("list_files", directory=directory)
        files = fs_tools.list_files(directory)
        if files and "error" in files[0]:
            return files[0]["error"]
        names = [f["name"] for f in files]
        out = [f"Found {len(names)} file(s) in {directory}:"]
        for f in files:
            out.append(f"  - {f['name']} ({f['size_bytes']} bytes)")
        if read:
            out.append("\nContents:")
            for f in files:
                _log_call("read_file", filepath=f["path"])
                r = fs_tools.read_file(f["path"])
                if r["success"]:
                    first = r["content"].splitlines()[0] if r["content"] else ""
                    out.append(f"  {f['name']}: {first} "
                               f"({r['metadata']['word_count']} words)")
        return "\n".join(out)

    def _offline_search(self, directory: str, keyword: str) -> str:
        _log_call("list_files", directory=directory)
        files = fs_tools.list_files(directory)
        if files and "error" in files[0]:
            return files[0]["error"]
        hits: List[str] = []
        for f in files:
            _log_call("search_in_file", filepath=f["path"], keyword=keyword)
            res = fs_tools.search_in_file(f["path"], keyword)
            if res["success"] and res["match_count"] > 0:
                sample = res["matches"][0]["context"]
                hits.append(f"  - {f['name']} ({res['match_count']} match(es)): {sample}")
        if not hits:
            return f"No resumes mention '{keyword}'."
        return f"Resumes mentioning '{keyword}':\n" + "\n".join(hits)

    def _offline_summary(self, query: str, directory: str) -> str:
        target = self._extract_filename(query)
        if not target:
            return "Which resume should I summarize? Name a file, e.g. resume_john_doe.txt"
        path = self._find_file(directory, target)
        _log_call("read_file", filepath=path)
        r = fs_tools.read_file(path)
        if not r["success"]:
            return f"Could not read {target}: {r['error']}"
        content = r["content"]
        # Heuristic summary: name/title line + skills line + word count.
        lines = [ln.strip() for ln in content.splitlines() if ln.strip()]
        header = " / ".join(lines[:2]) if len(lines) >= 2 else (lines[0] if lines else "")
        skills = ""
        for i, ln in enumerate(lines):
            if ln.upper() == "SKILLS" and i + 1 < len(lines):
                skills = lines[i + 1]
                break
        summary = (f"SUMMARY OF {r['metadata']['name']}\n"
                   f"{'=' * 40}\n"
                   f"{header}\n"
                   f"Skills: {skills}\n"
                   f"Length: {r['metadata']['word_count']} words\n")
        out_path = os.path.join(
            os.path.dirname(path),
            "summary_" + os.path.splitext(os.path.basename(path))[0] + ".txt")
        _log_call("write_file", filepath=out_path, content=f"<{len(summary)} chars>")
        w = fs_tools.write_file(out_path, summary)
        if not w["success"]:
            return f"Failed to write summary: {w['error']}"
        return (f"Wrote summary to {w['filepath']} ({w['bytes_written']} bytes):\n\n"
                f"{summary}")

    # -- parsing helpers -------------------------------------------------
    def _resolve_dir(self, query: str) -> str:
        # Explicit path in the query?
        m = re.search(r"(/[^\s'\"]+|[.\w/-]+/resumes)", query)
        if m and os.path.isdir(m.group(1)):
            return m.group(1)
        return DEFAULT_RESUME_DIR

    @staticmethod
    def _extract_filename(query: str) -> str:
        m = re.search(r"[\w./-]+\.(?:txt|pdf|docx|md)", query, re.I)
        if m:
            return m.group(0)
        # Only treat "resume_<name>" as a filename — not the bare word "resume(s)".
        m = re.search(r"resume[_-][\w-]+", query, re.I)
        return m.group(0) if m else ""

    @staticmethod
    def _extract_keyword(query: str) -> str:
        # "mentioning X", "with X", "about X", "who has X"
        m = re.search(r"(?:mention(?:ing)?|with|about|has|know[s]?|experience in|"
                      r"skilled in|using)\s+([A-Za-z0-9+.#]+)", query, re.I)
        if m:
            return m.group(1)
        # last capitalized-ish token as a fallback
        tokens = re.findall(r"[A-Za-z0-9+.#]{2,}", query)
        stop = {"find", "search", "resumes", "resume", "which", "who", "the",
                "mentioning", "mention", "folder", "all", "for", "file"}
        for tok in reversed(tokens):
            if tok.lower() not in stop:
                return tok
        return ""

    @staticmethod
    def _find_file(directory: str, target: str) -> str:
        target = os.path.basename(target)
        candidate = os.path.join(directory, target)
        if os.path.exists(candidate):
            return candidate
        # fuzzy: match by stem
        if os.path.isdir(directory):
            stem = os.path.splitext(target)[0].lower()
            for name in os.listdir(directory):
                if stem in name.lower():
                    return os.path.join(directory, name)
        return candidate


# ==========================================================================
# CLI
# ==========================================================================
BANNER = """\
=======================================================================
  LLM File Assistant  —  natural-language file-system tools
  Try: "Read all resumes in the resumes folder"
       "Find resumes mentioning Python experience"
       "Create a summary file for resume_john_doe.txt"
  Type 'quit' to exit.
=======================================================================\
"""


def main() -> None:
    assistant = FileAssistant()
    print(BANNER)
    print(f"Mode: {assistant.mode}   Model: "
          f"{MODEL if assistant.client else 'n/a'}\n")

    # One-shot mode if a query is passed on the command line.
    if len(sys.argv) > 1:
        query = " ".join(sys.argv[1:])
        print(f"you > {query}")
        print(assistant.ask(query))
        return

    while True:
        try:
            query = input("you > ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye.")
            break
        if not query:
            continue
        if query.lower() in ("quit", "exit"):
            print("Goodbye.")
            break
        print(assistant.ask(query))
        print()


if __name__ == "__main__":
    main()
