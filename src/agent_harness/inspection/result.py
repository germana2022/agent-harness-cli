"""Immutable inspection result model."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class EntryKind(str, Enum):
    FILE = "file"
    DIRECTORY = "directory"
    SYMLINK = "symlink"
    JUNCTION = "junction"
    REPARSE_POINT = "reparse_point"
    SPECIAL = "special"


@dataclass(frozen=True)
class InspectionEntry:
    repository_relative_path: str
    kind: EntryKind
    size: int
    classification: str = "unknown"
    redacted: bool = False


@dataclass(frozen=True)
class WarningRecord:
    code: str
    message: str


@dataclass(frozen=True)
class LimitInfo:
    code: str
    limit: int
    count: int


@dataclass(frozen=True)
class GitInfo:
    branch: str | None = None
    commit: str | None = None
    dirty: bool | None = None
    tracked_count: int | None = None
    untracked_count: int | None = None


@dataclass(frozen=True)
class InspectionResult:
    schema_version: int = 1
    status: str = "ok"
    partial: bool = False
    repository_type: str = "directory"
    resolved_root: str = "."
    requested_path: str = "."
    file_count: int = 0
    directory_count: int = 0
    total_metadata_size: int = 0
    content_bytes_read: int = 0
    entries: tuple[InspectionEntry, ...] = ()
    language_summary: tuple[tuple[str, int], ...] = ()
    manifest_summary: tuple[tuple[str, str], ...] = ()
    test_directory_count: int = 0
    documentation_count: int = 0
    git: GitInfo | None = None
    exclusion_summary: tuple[tuple[str, int], ...] = ()
    sensitive_entries: int = 0
    limit: LimitInfo | None = None
    warnings: tuple[WarningRecord, ...] = ()
