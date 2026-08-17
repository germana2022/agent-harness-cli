from dataclasses import FrozenInstanceError

import pytest

from agent_harness.inspection import (
    EntryKind,
    GitInfo,
    InspectionEntry,
    InspectionResult,
    LimitInfo,
    WarningRecord,
)


def test_default_result_fields():
    result = InspectionResult()
    assert result.schema_version == 1
    assert result.status == "ok"
    assert result.partial is False
    assert result.content_bytes_read == 0
    assert result.entries == ()


def test_result_construction():
    entry = InspectionEntry(
        repository_relative_path="a.py",
        kind=EntryKind.FILE,
        size=10,
        classification="python",
    )
    result = InspectionResult(
        status="partial",
        partial=True,
        file_count=1,
        entries=(entry,),
        git=GitInfo(branch="main", commit="abc1234", dirty=False),
        limit=LimitInfo(code="LIMIT_ENTRIES_EXCEEDED", limit=20, count=21),
        warnings=(WarningRecord(code="LINK_NOT_FOLLOWED", message="link"),),
    )
    assert result.partial is True
    assert result.git.branch == "main"
    assert result.limit.code == "LIMIT_ENTRIES_EXCEEDED"
    assert result.warnings[0].code == "LINK_NOT_FOLLOWED"


def test_entry_kind_values():
    assert EntryKind.FILE.value == "file"
    assert EntryKind.DIRECTORY.value == "directory"
    assert EntryKind.SYMLINK.value == "symlink"
    assert EntryKind.JUNCTION.value == "junction"
    assert EntryKind.REPARSE_POINT.value == "reparse_point"
    assert EntryKind.SPECIAL.value == "special"


def test_result_is_immutable():
    result = InspectionResult()
    with pytest.raises(FrozenInstanceError):
        result.file_count = 5  # type: ignore[misc]
