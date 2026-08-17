import json

from agent_harness.inspection import (
    EntryKind,
    GitInfo,
    InspectionEntry,
    InspectionResult,
    LimitInfo,
    WarningRecord,
    to_json,
    to_text,
)


def _entry(path, kind=EntryKind.FILE, size=1, classification="unknown", redacted=False):
    return InspectionEntry(
        repository_relative_path=path,
        kind=kind,
        size=size,
        classification=classification,
        redacted=redacted,
    )


def test_json_minimal():
    result = InspectionResult(
        resolved_root=".",
        file_count=1,
        directory_count=0,
        entries=(_entry("a.py", classification="python"),),
    )
    payload = json.loads(to_json(result))
    assert payload["schema_version"] == 1
    assert payload["status"] == "ok"
    assert payload["partial"] is False
    assert payload["file_count"] == 1
    assert payload["entries"][0]["repository_relative_path"] == "a.py"
    assert "requested_path" not in payload
    assert payload["resolved_root"] == "."


def test_json_full():
    result = InspectionResult(
        status="partial",
        partial=True,
        repository_type="git_worktree",
        file_count=2,
        directory_count=1,
        language_summary=(("python", 2), ("go", 1)),
        manifest_summary=(("pyproject.toml", "python"),),
        test_directory_count=1,
        documentation_count=1,
        git=GitInfo(branch="main", commit="abc1234", dirty=True, tracked_count=3, untracked_count=1),
        exclusion_summary=(("hidden", 1), ("ignored", 2)),
        sensitive_entries=1,
        limit=LimitInfo(code="LIMIT_ENTRIES_EXCEEDED", limit=20, count=21),
        warnings=(WarningRecord(code="LINK_NOT_FOLLOWED", message="link"),),
        entries=(_entry("a.py", classification="python"),),
    )
    payload = json.loads(to_json(result))
    assert payload["partial"] is True
    assert payload["git"]["branch"] == "main"
    assert payload["git"]["dirty"] is True
    assert payload["limit"]["code"] == "LIMIT_ENTRIES_EXCEEDED"
    assert payload["warnings"][0]["code"] == "LINK_NOT_FOLLOWED"
    assert payload["language_summary"] == {"go": 1, "python": 2}
    assert payload["sensitive_entries"] == 1
    assert payload["content_bytes_read"] == 0


def test_json_is_deterministic():
    result = InspectionResult(
        entries=(_entry("b.go"), _entry("a.py")),
        language_summary=(("python", 1), ("go", 1)),
    )
    first = to_json(result)
    second = to_json(result)
    assert first == second


def test_json_contains_no_ansi():
    result = InspectionResult(entries=(_entry("a\x1b[31m.py"),))
    assert "\x1b" not in to_json(result)


def test_json_does_not_include_absolute_requested_path():
    result = InspectionResult(requested_path="C:/Users/someone/project", resolved_root=".")
    assert "C:/Users/someone" not in to_json(result)


def test_json_redacted_entry():
    result = InspectionResult(entries=(_entry("<sensitive-1>", redacted=True),))
    payload = json.loads(to_json(result))
    assert payload["entries"][0]["redacted"] is True
    assert payload["entries"][0]["repository_relative_path"] == "<sensitive-1>"


def test_text_deterministic_and_ordered():
    result = InspectionResult(
        file_count=2,
        entries=(_entry("a.py"), _entry("b.go")),
        language_summary=(("go", 1), ("python", 1)),
    )
    text = to_text(result)
    assert "Repository: ." in text
    assert "Files: 2" in text
    assert text.index("a.py") < text.index("b.go")
    assert to_text(result) == to_text(result)


def test_text_partial_marker():
    result = InspectionResult(
        status="partial",
        partial=True,
        limit=LimitInfo(code="LIMIT_ENTRIES_EXCEEDED", limit=20, count=21),
    )
    assert "Partial: true (reason: LIMIT_ENTRIES_EXCEEDED)" in to_text(result)


def test_text_full_sections():
    result = InspectionResult(
        repository_type="git_worktree",
        file_count=1,
        manifest_summary=(("pyproject.toml", "python"),),
        git=GitInfo(branch="main", commit="abc", dirty=True),
        exclusion_summary=(("hidden", 1), ("ignored", 2)),
        sensitive_entries=1,
        warnings=(WarningRecord(code="LINK_NOT_FOLLOWED", message="link"),),
        entries=(_entry("a.py", classification="python"),),
    )
    text = to_text(result)
    assert "Languages:" not in text
    assert "Manifests:" in text and "pyproject.toml (python)" in text
    assert "Git:" in text and "branch: main" in text and "dirty: True" in text
    assert "Exclusions:" in text and "hidden: 1" in text
    assert "Sensitive entries redacted: 1" in text
    assert "Warnings:" in text and "LINK_NOT_FOLLOWED: link" in text


def test_text_entry_truncation():
    entries = tuple(_entry(f"f{i}.py") for i in range(250))
    result = InspectionResult(file_count=250, entries=entries)
    text = to_text(result)
    assert "more entries not shown" in text
