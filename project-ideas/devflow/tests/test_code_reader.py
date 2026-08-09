import pytest
from services.code_reader import ingest, CodeSummary, ALLOWED_EXT, SKIP_DIRS


def _make_file(tmp_path, rel_path: str, content: str):
    p = tmp_path / rel_path
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content)
    return p


def test_ingest_local_finds_python_files(tmp_path):
    _make_file(tmp_path, "src/main.py", "print('hello')")
    summary = ingest("local", str(tmp_path))
    assert any("main.py" in f for f in summary.file_tree)


def test_ingest_local_skips_disallowed_extensions(tmp_path):
    _make_file(tmp_path, "readme.md", "# readme")
    _make_file(tmp_path, "image.png", "binary")
    _make_file(tmp_path, "app.py", "x = 1")
    summary = ingest("local", str(tmp_path))
    names = [f for f in summary.file_tree]
    assert not any("readme.md" in n for n in names)
    assert not any("image.png" in n for n in names)
    assert any("app.py" in n for n in names)


def test_ingest_local_skips_skip_dirs(tmp_path):
    _make_file(tmp_path, "node_modules/lib.js", "var x = 1;")
    _make_file(tmp_path, "__pycache__/cached.py", "cached")
    _make_file(tmp_path, "src/real.py", "real code")
    summary = ingest("local", str(tmp_path))
    assert not any("node_modules" in f for f in summary.file_tree)
    assert not any("__pycache__" in f for f in summary.file_tree)
    assert any("real.py" in f for f in summary.file_tree)


def test_ingest_local_reads_file_content(tmp_path):
    _make_file(tmp_path, "service.py", "def greet(): return 'hi'")
    summary = ingest("local", str(tmp_path))
    excerpts = summary.file_excerpts
    assert any("greet" in v for v in excerpts.values())


def test_ingest_local_empty_dir(tmp_path):
    summary = ingest("local", str(tmp_path))
    assert summary.file_tree == []
    assert summary.file_excerpts == {}


def test_ingest_unknown_source_type():
    summary = ingest("ftp", "/some/path")
    assert isinstance(summary, CodeSummary)
    assert summary.file_tree == []


def test_ingest_local_multiple_languages(tmp_path):
    _make_file(tmp_path, "a.py", "x=1")
    _make_file(tmp_path, "b.js", "var y=2;")
    _make_file(tmp_path, "c.go", "package main")
    summary = ingest("local", str(tmp_path))
    assert len(summary.file_tree) == 3


def test_ingest_local_nested_dirs(tmp_path):
    _make_file(tmp_path, "a/b/c/deep.py", "deep code")
    summary = ingest("local", str(tmp_path))
    assert any("deep.py" in f for f in summary.file_tree)


def test_ingest_local_respects_max_files(tmp_path, monkeypatch):
    import services.code_reader as cr
    monkeypatch.setattr(cr, "MAX_FILES", 3)
    for i in range(10):
        _make_file(tmp_path, f"file{i}.py", f"x = {i}")
    summary = ingest("local", str(tmp_path))
    assert len(summary.file_excerpts) <= 3


def test_allowed_extensions_set():
    assert ".py" in ALLOWED_EXT
    assert ".js" in ALLOWED_EXT
    assert ".md" not in ALLOWED_EXT
    assert ".png" not in ALLOWED_EXT


def test_skip_dirs_set():
    assert "node_modules" in SKIP_DIRS
    assert ".git" in SKIP_DIRS
    assert "__pycache__" in SKIP_DIRS
