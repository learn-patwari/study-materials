import os
import pytest
from services import code_editor


def test_backup_creates_copy(tmp_dir):
    src = tmp_dir / "src.py"
    src.write_text("original content")
    backup_dir = code_editor.backup_files([str(src)], str(tmp_dir))
    assert os.path.isdir(backup_dir)
    backed = list(p for p in os.walk(backup_dir) for f in p[2] if f == "src.py")
    assert len(backed) == 1


def test_backup_missing_file_skipped(tmp_dir):
    backup_dir = code_editor.backup_files([str(tmp_dir / "ghost.py")], str(tmp_dir))
    assert os.path.isdir(backup_dir)
    files = [f for _, _, fs in os.walk(backup_dir) for f in fs]
    assert files == []


def test_apply_fix_replaces_text(tmp_dir):
    f = tmp_dir / "app.py"
    f.write_text("def foo():\n    return 1\n")
    fix_plan = [{"file": "app.py", "before": "return 1", "after": "return 42"}]
    modified = code_editor.apply_fix(fix_plan, str(tmp_dir))
    assert f.read_text() == "def foo():\n    return 42\n"
    assert len(modified) == 1


def test_apply_fix_first_occurrence_only(tmp_dir):
    f = tmp_dir / "dup.py"
    f.write_text("x = 1\nx = 1\n")
    fix_plan = [{"file": "dup.py", "before": "x = 1", "after": "x = 99"}]
    code_editor.apply_fix(fix_plan, str(tmp_dir))
    content = f.read_text()
    assert content.count("x = 99") == 1
    assert content.count("x = 1") == 1


def test_apply_fix_skips_missing_before(tmp_dir):
    f = tmp_dir / "noop.py"
    f.write_text("def bar(): pass\n")
    fix_plan = [{"file": "noop.py", "before": "DOES_NOT_EXIST", "after": "something"}]
    modified = code_editor.apply_fix(fix_plan, str(tmp_dir))
    assert modified == []
    assert f.read_text() == "def bar(): pass\n"


def test_apply_fix_skips_missing_file(tmp_dir):
    fix_plan = [{"file": "ghost.py", "before": "x", "after": "y"}]
    modified = code_editor.apply_fix(fix_plan, str(tmp_dir))
    assert modified == []


def test_revert_restores_files(tmp_dir):
    src = tmp_dir / "module.py"
    src.write_text("original")
    backup_dir = code_editor.backup_files([str(src)], str(tmp_dir))

    # Simulate a change
    src.write_text("modified")
    assert src.read_text() == "modified"

    code_editor.revert(backup_dir, str(tmp_dir))
    assert src.read_text() == "original"


def test_backup_and_apply_and_revert_full_flow(tmp_dir):
    f = tmp_dir / "service.py"
    f.write_text("return_value = 'old'\n")

    backup_dir = code_editor.backup_files([str(f)], str(tmp_dir))
    code_editor.apply_fix([{"file": "service.py", "before": "'old'", "after": "'new'"}], str(tmp_dir))
    assert f.read_text() == "return_value = 'new'\n"

    code_editor.revert(backup_dir, str(tmp_dir))
    assert f.read_text() == "return_value = 'old'\n"


def test_apply_fix_multiple_files(tmp_dir):
    a = tmp_dir / "a.py"
    b = tmp_dir / "b.py"
    a.write_text("x = 1")
    b.write_text("y = 2")
    fix_plan = [
        {"file": "a.py", "before": "x = 1", "after": "x = 10"},
        {"file": "b.py", "before": "y = 2", "after": "y = 20"},
    ]
    modified = code_editor.apply_fix(fix_plan, str(tmp_dir))
    assert len(modified) == 2
    assert a.read_text() == "x = 10"
    assert b.read_text() == "y = 20"
