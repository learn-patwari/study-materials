"""
fs_tools.py
===========
Core file-system tools for the LLM file assistant (Assignment 2, Part A).

Each tool returns a **structured** result (a dict, or a list of dicts) with a
consistent shape so an LLM — or any caller — can reason about success/failure
without parsing prose:

    read_file(filepath)            -> dict   {success, content, metadata, error}
    list_files(directory, ext)     -> list   [{name, path, size_bytes, ...}, ...]
    write_file(filepath, content)  -> dict   {success, filepath, bytes_written, error}
    search_in_file(filepath, kw)   -> dict   {success, matches, match_count, error}

Reading supports **TXT, PDF, and DOCX**. PDF/DOCX parsing needs optional
dependencies (`pypdf`, `python-docx`); if they're missing, the tool returns a
graceful error dict instead of raising, so the assistant keeps working.
"""

from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

# Extensions we know how to extract text from.
SUPPORTED_READ_EXTENSIONS = {".txt", ".md", ".csv", ".log", ".pdf", ".docx"}


# --------------------------------------------------------------------------
# Internal helpers
# --------------------------------------------------------------------------
def _iso(ts: float) -> str:
    """Format a POSIX timestamp as an ISO-8601 UTC string."""
    return datetime.fromtimestamp(ts, tz=timezone.utc).isoformat()


def _file_metadata(path: str) -> Dict[str, Any]:
    st = os.stat(path)
    _, ext = os.path.splitext(path)
    return {
        "name": os.path.basename(path),
        "path": os.path.abspath(path),
        "extension": ext.lower(),
        "size_bytes": st.st_size,
        "modified": _iso(st.st_mtime),
        "created": _iso(st.st_ctime),
    }


def _extract_txt(path: str) -> str:
    with open(path, "r", encoding="utf-8", errors="replace") as fh:
        return fh.read()


def _extract_pdf(path: str) -> str:
    try:
        from pypdf import PdfReader  # type: ignore
    except Exception as exc:  # pragma: no cover - depends on optional dep
        raise RuntimeError(
            "Reading PDF files requires the 'pypdf' package "
            "(pip install pypdf). Original error: %s" % exc
        )
    reader = PdfReader(path)
    return "\n".join((page.extract_text() or "") for page in reader.pages)


def _extract_docx(path: str) -> str:
    try:
        import docx  # type: ignore  # python-docx
    except Exception as exc:  # pragma: no cover - depends on optional dep
        raise RuntimeError(
            "Reading DOCX files requires the 'python-docx' package "
            "(pip install python-docx). Original error: %s" % exc
        )
    document = docx.Document(path)
    return "\n".join(p.text for p in document.paragraphs)


_EXTRACTORS = {
    ".txt": _extract_txt,
    ".md": _extract_txt,
    ".csv": _extract_txt,
    ".log": _extract_txt,
    ".pdf": _extract_pdf,
    ".docx": _extract_docx,
}


# --------------------------------------------------------------------------
# Tool 1: read_file
# --------------------------------------------------------------------------
def read_file(filepath: str) -> Dict[str, Any]:
    """Read a resume/text file (TXT, PDF, or DOCX) and return its content + metadata.

    Args:
        filepath: Path to the file to read.

    Returns:
        {
          "success": bool,
          "filepath": str,
          "content": str,            # extracted text ("" on failure)
          "metadata": dict,          # name/size/modified/word_count/... ({} on failure)
          "error": str | None,       # human-readable error message on failure
        }
    """
    if not os.path.exists(filepath):
        return {"success": False, "filepath": filepath, "content": "",
                "metadata": {}, "error": f"File not found: {filepath}"}
    if os.path.isdir(filepath):
        return {"success": False, "filepath": filepath, "content": "",
                "metadata": {}, "error": f"Path is a directory, not a file: {filepath}"}

    _, ext = os.path.splitext(filepath)
    ext = ext.lower()
    extractor = _EXTRACTORS.get(ext)
    if extractor is None:
        return {"success": False, "filepath": filepath, "content": "",
                "metadata": {},
                "error": f"Unsupported file type '{ext}'. Supported: "
                         f"{sorted(SUPPORTED_READ_EXTENSIONS)}"}

    try:
        content = extractor(filepath)
    except Exception as exc:  # graceful — never raise to the caller/LLM
        return {"success": False, "filepath": filepath, "content": "",
                "metadata": _safe_metadata(filepath), "error": str(exc)}

    metadata = _file_metadata(filepath)
    metadata["file_type"] = ext.lstrip(".")
    metadata["char_count"] = len(content)
    metadata["word_count"] = len(content.split())
    metadata["line_count"] = content.count("\n") + 1 if content else 0
    return {"success": True, "filepath": filepath, "content": content,
            "metadata": metadata, "error": None}


def _safe_metadata(path: str) -> Dict[str, Any]:
    try:
        return _file_metadata(path)
    except Exception:
        return {}


# --------------------------------------------------------------------------
# Tool 2: list_files
# --------------------------------------------------------------------------
def list_files(directory: str, extension: Optional[str] = None) -> List[Dict[str, Any]]:
    """List files in a directory, optionally filtered by extension.

    Args:
        directory: Directory to list.
        extension: Optional extension filter, e.g. ".pdf" or "txt" (dot optional).

    Returns:
        A list of file-metadata dicts (name, path, size_bytes, modified, ...).
        On error (missing dir), returns a single-element list containing an
        {"error": ...} dict so callers/LLMs get a structured signal.
    """
    if not os.path.exists(directory):
        return [{"error": f"Directory not found: {directory}"}]
    if not os.path.isdir(directory):
        return [{"error": f"Not a directory: {directory}"}]

    norm_ext = None
    if extension:
        norm_ext = extension.lower()
        if not norm_ext.startswith("."):
            norm_ext = "." + norm_ext

    results: List[Dict[str, Any]] = []
    for name in sorted(os.listdir(directory)):
        full = os.path.join(directory, name)
        if not os.path.isfile(full):
            continue
        _, ext = os.path.splitext(name)
        if norm_ext and ext.lower() != norm_ext:
            continue
        results.append(_file_metadata(full))
    return results


# --------------------------------------------------------------------------
# Tool 3: write_file
# --------------------------------------------------------------------------
def write_file(filepath: str, content: str) -> Dict[str, Any]:
    """Write text content to a file, creating parent directories as needed.

    Args:
        filepath: Destination path.
        content: Text to write.

    Returns:
        {"success": bool, "filepath": str, "bytes_written": int, "error": str|None}
    """
    try:
        parent = os.path.dirname(os.path.abspath(filepath))
        if parent:
            os.makedirs(parent, exist_ok=True)
        data = content if isinstance(content, str) else str(content)
        with open(filepath, "w", encoding="utf-8") as fh:
            fh.write(data)
        return {"success": True, "filepath": os.path.abspath(filepath),
                "bytes_written": len(data.encode("utf-8")), "error": None}
    except Exception as exc:
        return {"success": False, "filepath": filepath,
                "bytes_written": 0, "error": str(exc)}


# --------------------------------------------------------------------------
# Tool 4: search_in_file
# --------------------------------------------------------------------------
def search_in_file(filepath: str, keyword: str,
                   context_chars: int = 60) -> Dict[str, Any]:
    """Case-insensitively search a file for a keyword, returning matches with context.

    Args:
        filepath: File to search (TXT/PDF/DOCX — uses read_file to extract text).
        keyword: The keyword/phrase to look for (case-insensitive).
        context_chars: How many characters of surrounding text to include per match.

    Returns:
        {
          "success": bool,
          "filepath": str,
          "keyword": str,
          "match_count": int,
          "matches": [{"line_number": int, "line": str, "context": str}, ...],
          "error": str | None,
        }
    """
    if not keyword:
        return {"success": False, "filepath": filepath, "keyword": keyword,
                "match_count": 0, "matches": [], "error": "Empty keyword."}

    read = read_file(filepath)
    if not read["success"]:
        return {"success": False, "filepath": filepath, "keyword": keyword,
                "match_count": 0, "matches": [], "error": read["error"]}

    content = read["content"]
    needle = keyword.lower()
    matches: List[Dict[str, Any]] = []

    # Line-level matches (nice for display), plus a char-window context.
    for lineno, line in enumerate(content.splitlines(), start=1):
        low = line.lower()
        start = low.find(needle)
        if start == -1:
            continue
        c_start = max(0, start - context_chars)
        c_end = min(len(line), start + len(keyword) + context_chars)
        snippet = line[c_start:c_end].strip()
        if c_start > 0:
            snippet = "…" + snippet
        if c_end < len(line):
            snippet = snippet + "…"
        matches.append({"line_number": lineno, "line": line.strip(),
                        "context": snippet})

    return {"success": True, "filepath": filepath, "keyword": keyword,
            "match_count": len(matches), "matches": matches, "error": None}


# --------------------------------------------------------------------------
# Manual smoke test
# --------------------------------------------------------------------------
if __name__ == "__main__":
    import json

    here = os.path.dirname(os.path.abspath(__file__))
    resumes = os.path.join(here, "sample_data", "resumes")
    print("list_files:", json.dumps(list_files(resumes, ".txt")[:2], indent=2))
    files = list_files(resumes, ".txt")
    if files and "error" not in files[0]:
        first = files[0]["path"]
        r = read_file(first)
        print(f"\nread_file {os.path.basename(first)}: "
              f"{r['metadata'].get('word_count')} words")
        print("search 'Python':",
              search_in_file(first, "Python")["match_count"], "matches")
