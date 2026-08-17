import os
from pathlib import Path

import pytest

from agent_harness.infrastructure.inspector import Inspector
from agent_harness.inspection import EntryKind, InspectionRequest, to_json


def _walk(root, **kwargs):
    return Inspector().inspect(root, InspectionRequest(**kwargs))


def _make_symlink(target, link):
    try:
        link.symlink_to(target)
    except (OSError, NotImplementedError):
        pytest.skip("symlink creation is not permitted in this environment")
    return link


def test_empty_directory(tmp_path):
    summary = _walk(tmp_path)
    assert summary.file_count == 0
    assert summary.directory_count == 0
    assert summary.limit is None


def test_mixed_repository(tmp_path):
    (tmp_path / "a.py").write_text("print(1)")
    (tmp_path / "README.md").write_text("readme")
    (tmp_path / "sub").mkdir()
    (tmp_path / "sub" / "b.go").write_text("package main")
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "test_x.py").write_text("x")
    summary = _walk(tmp_path)
    assert summary.file_count == 4
    assert summary.directory_count == 2
    languages = dict(summary.language_summary)
    assert languages.get("python") == 2
    assert languages.get("go") == 1
    assert summary.documentation_count == 1
    assert summary.test_directory_count == 1
    paths = [entry.repository_relative_path for entry in summary.entries]
    assert "a.py" in paths and "sub/b.go" in paths and "tests/test_x.py" in paths


def test_nested_repository_excluded(tmp_path):
    outer = tmp_path / "outer"
    outer.mkdir()
    (outer / ".git").mkdir()
    inner = outer / "inner"
    inner.mkdir()
    (inner / ".git").mkdir()
    (inner / "x.py").write_text("x")
    summary = _walk(outer)
    assert summary.exclusion_summary == (("ignored", 1), ("nested_repository", 1))
    assert summary.file_count == 0


def test_git_marker_always_excluded(tmp_path):
    (tmp_path / ".git").mkdir()
    (tmp_path / "a.py").write_text("x")
    summary = _walk(tmp_path)
    assert dict(summary.exclusion_summary).get("ignored") == 1
    assert summary.file_count == 1
    assert all(".git" not in e.repository_relative_path for e in summary.entries)


def test_generated_directory_respects_include_ignored(tmp_path):
    (tmp_path / "node_modules").mkdir()
    (tmp_path / "node_modules" / "x.js").write_text("x")
    default = _walk(tmp_path)
    assert dict(default.exclusion_summary).get("ignored") == 1
    assert default.file_count == 0
    included = _walk(tmp_path, include_ignored=True)
    assert dict(included.exclusion_summary).get("ignored") is None
    assert included.file_count == 1


def test_hidden_files(tmp_path):
    (tmp_path / ".hidden").write_text("x")
    (tmp_path / "visible.py").write_text("x")
    default = _walk(tmp_path)
    assert dict(default.exclusion_summary).get("hidden") == 1
    assert default.file_count == 1
    included = _walk(tmp_path, include_hidden=True)
    assert included.file_count == 2


def test_sensitive_names_redacted(tmp_path):
    (tmp_path / "secrets.json").write_text("{}")
    (tmp_path / "id_rsa").write_text("key")
    (tmp_path / "normal.py").write_text("x")
    summary = _walk(tmp_path)
    assert summary.sensitive_entries == 2
    assert summary.file_count == 3
    text = to_json(__import__("agent_harness.inspection.result", fromlist=["InspectionResult"]).InspectionResult(
        entries=summary.entries, file_count=summary.file_count
    ))
    assert "secrets.json" not in text
    assert "id_rsa" not in text
    assert "<sensitive-" in text


def test_symlink_inside_root_classified_not_followed(tmp_path):
    (tmp_path / "real").mkdir()
    (tmp_path / "real" / "data.txt").write_text("data")
    link = _make_symlink(tmp_path / "real", tmp_path / "linkdir")
    summary = _walk(tmp_path)
    link_entries = [e for e in summary.entries if e.kind is EntryKind.SYMLINK]
    assert len(link_entries) == 1
    assert any(w.code == "LINK_NOT_FOLLOWED" for w in summary.warnings)
    assert "real/data.txt" in [e.repository_relative_path for e in summary.entries]
    assert not any("linkdir/data.txt" in e.repository_relative_path for e in summary.entries)


def test_symlink_outside_root_not_traversed(tmp_path):
    outside = tmp_path.parent / (tmp_path.name + "_outside")
    outside.mkdir(exist_ok=True)
    (outside / "leak.py").write_text("secret")
    link = _make_symlink(outside, tmp_path / "escape")
    summary = _walk(tmp_path)
    assert all("leak.py" not in e.repository_relative_path for e in summary.entries)
    assert not any("escape/leak.py" in e.repository_relative_path for e in summary.entries)


def test_broken_symlink(tmp_path):
    link = _make_symlink(tmp_path / "missing-target", tmp_path / "broken")
    summary = _walk(tmp_path)
    assert any(e.kind is EntryKind.SYMLINK for e in summary.entries)


def test_symlink_cycle_no_hang(tmp_path):
    a = _make_symlink(tmp_path / "b", tmp_path / "a")
    b = _make_symlink(tmp_path / "a", tmp_path / "b")
    summary = _walk(tmp_path)
    assert len([e for e in summary.entries if e.kind is EntryKind.SYMLINK]) == 2
    assert summary.limit is None


def test_link_policy_error(tmp_path):
    _make_symlink(tmp_path / "target", tmp_path / "link")
    from agent_harness.inspection.errors import LinkEncounteredError

    with pytest.raises(LinkEncounteredError):
        _walk(tmp_path, link_policy="error")


def test_max_entries_partial(tmp_path):
    for i in range(10):
        (tmp_path / f"f{i}.py").write_text("x")
    summary = _walk(tmp_path, max_entries=3)
    assert summary.limit is not None
    assert summary.limit.code == "LIMIT_ENTRIES_EXCEEDED"
    assert summary.file_count <= 3


def test_max_depth_partial(tmp_path):
    deep = tmp_path
    for name in ("a", "b", "c", "d", "e"):
        deep = deep / name
        deep.mkdir()
    deep.joinpath("leaf.py").write_text("x")
    summary = _walk(tmp_path, max_depth=2)
    assert summary.limit is not None
    assert summary.limit.code == "LIMIT_DEPTH_EXCEEDED"


def test_max_warnings_partial(tmp_path):
    (tmp_path / "real").mkdir()
    for i in range(5):
        _make_symlink(tmp_path / "missing", tmp_path / f"link{i}")
    summary = _walk(tmp_path, max_warnings=2)
    assert summary.limit is not None
    assert summary.limit.code == "LIMIT_WARNINGS_EXCEEDED"
    assert len(summary.warnings) == 2


def test_unicode_and_control_filenames(tmp_path):
    (tmp_path / "caf\u00e9.py").write_text("x")
    if os.name == "nt":
        pytest.skip("NUL bytes are not valid in Windows filenames")
    (tmp_path / "weird\x00name.py").write_text("x")
    summary = _walk(tmp_path)
    assert summary.file_count == 2


def test_no_content_read(tmp_path, monkeypatch):
    (tmp_path / "a.py").write_text("print(secret)")
    (tmp_path / ".env").write_text("TOKEN=secret")
    (tmp_path / "secrets.json").write_text("{}")
    calls = []
    real_open = open

    def spy_open(*args, **kwargs):
        calls.append(args)
        return real_open(*args, **kwargs)

    monkeypatch.setattr("builtins.open", spy_open)
    summary = _walk(tmp_path, include_hidden=True)
    assert summary.file_count >= 1
    # The inspector must never open any file for reading during the walk.
    assert calls == []


def test_determinism(tmp_path):
    (tmp_path / "b.py").write_text("x")
    (tmp_path / "a.py").write_text("x")
    (tmp_path / "sub").mkdir()
    first = _walk(tmp_path)
    second = _walk(tmp_path)
    assert first.entries == second.entries
    assert [e.repository_relative_path for e in first.entries] == [
        e.repository_relative_path for e in second.entries
    ]
    assert to_json(
        __import__("agent_harness.inspection.result", fromlist=["InspectionResult"]).InspectionResult(
            entries=first.entries, file_count=first.file_count
        )
    ) == to_json(
        __import__("agent_harness.inspection.result", fromlist=["InspectionResult"]).InspectionResult(
            entries=second.entries, file_count=second.file_count
        )
    )


def test_no_side_effects(tmp_path):
    before = {p.name for p in tmp_path.iterdir()}
    (tmp_path / "a.py").write_text("x")
    _walk(tmp_path)
    after = {p.name for p in tmp_path.iterdir()}
    assert after == before | {"a.py"}
    assert (tmp_path / "a.py").read_text() == "x"


def test_special_file_skipped(tmp_path):
    if os.name == "nt":
        pytest.skip("FIFO creation is not supported on Windows")
    os.mkfifo(tmp_path / "pipe")
    summary = _walk(tmp_path)
    assert any(w.code == "UNSUPPORTED_ENTRY" for w in summary.warnings)
