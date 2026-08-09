import os
import shutil
from datetime import datetime
from pathlib import Path


class CodeEditorError(Exception):
    pass


def backup_files(file_paths: list[str], project_root: str) -> str:
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dir = os.path.join(project_root, ".devflow_backup", ts)
    os.makedirs(backup_dir, exist_ok=True)
    for fp in file_paths:
        if os.path.isfile(fp):
            rel = os.path.relpath(fp, project_root)
            dest = os.path.join(backup_dir, rel)
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            shutil.copy2(fp, dest)
    return backup_dir


def apply_fix(fix_plan: list[dict], project_root: str) -> list[str]:
    """Apply fix plan items. Each item: {file, before, after}. Returns list of modified files."""
    modified = []
    for item in fix_plan:
        rel_path = item.get("file", "")
        before = item.get("before", "")
        after = item.get("after", "")
        if not rel_path or not before:
            continue
        full = os.path.join(project_root, rel_path)
        if not os.path.isfile(full):
            # Try as absolute path
            if not os.path.isfile(rel_path):
                continue
            full = rel_path
        try:
            text = Path(full).read_text(errors="replace")
            if before not in text:
                continue
            new_text = text.replace(before, after, 1)
            Path(full).write_text(new_text)
            modified.append(full)
        except OSError as e:
            raise CodeEditorError(f"Could not edit {full}: {e}") from e
    return modified


def revert(backup_dir: str, project_root: str):
    for dirpath, _, filenames in os.walk(backup_dir):
        for fname in filenames:
            src = os.path.join(dirpath, fname)
            rel = os.path.relpath(src, backup_dir)
            dest = os.path.join(project_root, rel)
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            shutil.copy2(src, dest)
