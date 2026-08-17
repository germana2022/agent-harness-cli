"""Deterministic JSON (schema v1) and text serializers.

JSON output never contains ANSI, machine-specific absolute paths, or raw
sensitive filenames. All collections are emitted in sorted order and the
document is produced with ``sort_keys=True`` for byte stability.
"""

from __future__ import annotations

import json

from .result import InspectionResult

SCHEMA_VERSION = 1

_ENTRY_DISPLAY_LIMIT = 200


def to_json(result: InspectionResult) -> str:
    payload: dict[str, object] = {
        "schema_version": SCHEMA_VERSION,
        "status": result.status,
        "partial": result.partial,
        "repository_type": result.repository_type,
        "resolved_root": result.resolved_root,
        "file_count": result.file_count,
        "directory_count": result.directory_count,
        "total_metadata_size": result.total_metadata_size,
        "content_bytes_read": result.content_bytes_read,
        "entries": [_entry_dict(entry) for entry in result.entries],
    }
    if result.language_summary:
        payload["language_summary"] = {
            name: count for name, count in sorted(result.language_summary)
        }
    if result.manifest_summary:
        payload["manifest_summary"] = [
            {"repository_relative_path": path, "ecosystem": ecosystem}
            for path, ecosystem in sorted(result.manifest_summary)
        ]
    if result.test_directory_count:
        payload["test_directory_count"] = result.test_directory_count
    if result.documentation_count:
        payload["documentation_count"] = result.documentation_count
    if result.git is not None:
        git: dict[str, object] = {}
        if result.git.branch is not None:
            git["branch"] = result.git.branch
        if result.git.commit is not None:
            git["commit"] = result.git.commit
        if result.git.dirty is not None:
            git["dirty"] = result.git.dirty
        if result.git.tracked_count is not None:
            git["tracked_count"] = result.git.tracked_count
        if result.git.untracked_count is not None:
            git["untracked_count"] = result.git.untracked_count
        payload["git"] = git
    if result.exclusion_summary:
        payload["exclusion_summary"] = {
            category: count for category, count in sorted(result.exclusion_summary)
        }
    if result.sensitive_entries:
        payload["sensitive_entries"] = result.sensitive_entries
    if result.limit is not None:
        payload["limit"] = {
            "code": result.limit.code,
            "limit": result.limit.limit,
            "count": result.limit.count,
        }
    if result.warnings:
        payload["warnings"] = [
            {"code": warning.code, "message": warning.message}
            for warning in result.warnings
        ]
    return json.dumps(payload, sort_keys=True, ensure_ascii=True)


def to_text(result: InspectionResult) -> str:
    lines: list[str] = []
    lines.append(f"Repository: {result.resolved_root}")
    lines.append(f"Status: {result.status}")
    if result.partial and result.limit is not None:
        lines.append(f"Partial: true (reason: {result.limit.code})")
    lines.append(f"Repository type: {result.repository_type}")
    lines.append(f"Files: {result.file_count}")
    lines.append(f"Directories: {result.directory_count}")
    lines.append(f"Total metadata size: {result.total_metadata_size}")
    lines.append(f"Content bytes read: {result.content_bytes_read}")
    if result.language_summary:
        lines.append("Languages:")
        for name, count in sorted(result.language_summary):
            lines.append(f"  {name}: {count}")
    if result.manifest_summary:
        lines.append("Manifests:")
        for path, ecosystem in sorted(result.manifest_summary):
            lines.append(f"  {path} ({ecosystem})")
    if result.git is not None:
        lines.append("Git:")
        if result.git.branch is not None:
            lines.append(f"  branch: {result.git.branch}")
        if result.git.commit is not None:
            lines.append(f"  commit: {result.git.commit}")
        if result.git.dirty is not None:
            lines.append(f"  dirty: {result.git.dirty}")
    if result.exclusion_summary:
        lines.append("Exclusions:")
        for category, count in sorted(result.exclusion_summary):
            lines.append(f"  {category}: {count}")
    if result.sensitive_entries:
        lines.append(f"Sensitive entries redacted: {result.sensitive_entries}")
    lines.append("Entries:")
    visible = result.entries[:_ENTRY_DISPLAY_LIMIT]
    for entry in visible:
        marker = " [redacted]" if entry.redacted else ""
        lines.append(f"  {entry.repository_relative_path} ({entry.kind.value}){marker}")
    if len(result.entries) > _ENTRY_DISPLAY_LIMIT:
        lines.append(
            f"  ... {len(result.entries) - _ENTRY_DISPLAY_LIMIT} more entries not shown"
        )
    if result.warnings:
        lines.append("Warnings:")
        for warning in result.warnings:
            lines.append(f"  {warning.code}: {warning.message}")
    return "\n".join(lines)


def _entry_dict(entry: object) -> dict[str, object]:
    from .result import InspectionEntry

    assert isinstance(entry, InspectionEntry)
    return {
        "repository_relative_path": entry.repository_relative_path,
        "kind": entry.kind.value,
        "size": entry.size,
        "classification": entry.classification,
        "redacted": entry.redacted,
    }
