import os
from pathlib import Path
from dataclasses import dataclass, field
from services import bitbucket_client

ALLOWED_EXT = {".py", ".js", ".ts", ".java", ".go", ".cs", ".sql", ".xml", ".yaml", ".yml", ".json"}
SKIP_DIRS = {"node_modules", ".git", "__pycache__", "build", "dist", "target", ".idea", ".vscode"}
MAX_FILE_BYTES = 32_000
MAX_FILES = 60


@dataclass
class CodeSummary:
    file_tree: list[str] = field(default_factory=list)
    file_excerpts: dict[str, str] = field(default_factory=dict)
    language_hint: str = ""
    source: str = ""


def ingest(source_type: str, source: str) -> CodeSummary:
    if source_type == "local":
        return _ingest_local(source)
    elif source_type == "bitbucket":
        return _ingest_bitbucket(source)
    return CodeSummary()


def _ingest_local(root: str) -> CodeSummary:
    summary = CodeSummary(source=root)
    collected: list[tuple[str, str]] = []

    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for fname in filenames:
            ext = Path(fname).suffix.lower()
            if ext not in ALLOWED_EXT:
                continue
            full = os.path.join(dirpath, fname)
            rel = os.path.relpath(full, root)
            summary.file_tree.append(rel)
            if len(collected) < MAX_FILES:
                try:
                    size = os.path.getsize(full)
                    if size <= MAX_FILE_BYTES:
                        text = Path(full).read_text(errors="replace")
                    else:
                        with open(full, errors="replace") as f:
                            text = "".join(f.readline() for _ in range(200))
                    collected.append((rel, text))
                except OSError:
                    pass

    summary.file_excerpts = dict(collected)
    summary.language_hint = _detect_language(summary.file_tree)
    return summary


def _ingest_bitbucket(repo_slug: str) -> CodeSummary:
    summary = CodeSummary(source=repo_slug)
    try:
        all_files = bitbucket_client.list_files(repo_slug)
    except Exception:
        return summary

    for f in all_files:
        ext = Path(f).suffix.lower()
        if ext in ALLOWED_EXT:
            summary.file_tree.append(f)

    for f in summary.file_tree[:MAX_FILES]:
        try:
            content = bitbucket_client.get_file_content(repo_slug, f)
            summary.file_excerpts[f] = content[:MAX_FILE_BYTES]
        except Exception:
            pass

    summary.language_hint = _detect_language(summary.file_tree)
    return summary


def _detect_language(file_tree: list[str]) -> str:
    counts: dict[str, int] = {}
    for f in file_tree:
        ext = Path(f).suffix.lower()
        counts[ext] = counts.get(ext, 0) + 1
    if not counts:
        return "unknown"
    dominant = max(counts, key=counts.__getitem__)
    mapping = {".py": "Python", ".js": "JavaScript", ".ts": "TypeScript",
               ".java": "Java", ".go": "Go", ".cs": "C#"}
    return mapping.get(dominant, dominant.lstrip(".").upper())


def format_for_prompt(summary: CodeSummary, max_chars: int = 12_000) -> str:
    lines = [f"Language: {summary.language_hint}", "File tree:"]
    lines += [f"  {f}" for f in summary.file_tree[:80]]
    lines.append("\nKey file excerpts:")
    budget = max_chars - len("\n".join(lines))
    for path, content in list(summary.file_excerpts.items())[:20]:
        snippet = f"\n### {path}\n{content[:1500]}"
        if budget - len(snippet) < 0:
            break
        lines.append(snippet)
        budget -= len(snippet)
    return "\n".join(lines)
