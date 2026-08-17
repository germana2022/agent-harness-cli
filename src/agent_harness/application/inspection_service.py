"""Application orchestration for safe repository inspection.

The service validates the request, resolves the inspection root, evaluates the
Phase 2 policy before any traversal, runs the bounded inspector, optionally
enriches with read-only Git metadata, and assembles the immutable result.
"""

from __future__ import annotations

from pathlib import Path
from typing import Callable

from agent_harness.domain import (
    ActionCategory,
    ActionName,
    Capability,
    PolicyEngine,
    PolicyRequest,
    TargetResource,
)
from agent_harness.domain.modes import OperatingMode

from ..infrastructure.git_metadata import GitMetadataReader
from ..infrastructure.inspector import Inspector, resolve_inspection_root
from ..inspection.errors import PolicyDeniedError, sanitize_text
from ..inspection.request import InspectionRequest
from ..inspection.result import InspectionResult, WarningRecord

Resolver = Callable[[str], tuple[Path, str]]


class InspectionService:
    """Orchestrates a metadata-only repository inspection."""

    def __init__(
        self,
        inspector: Inspector,
        git_reader: GitMetadataReader,
        policy_engine: PolicyEngine,
        resolver: Resolver | None = None,
    ) -> None:
        self._inspector = inspector
        self._git_reader = git_reader
        self._engine = policy_engine
        self._resolver = resolver or resolve_inspection_root

    def inspect(self, request: InspectionRequest) -> InspectionResult:
        root, repository_type = self._resolver(request.requested_path)
        self._assert_allowed(root)
        walk = self._inspector.inspect(root, request)
        git = None
        warnings = list(walk.warnings)
        if repository_type in ("git_worktree", "git_bare") and request.git_metadata != "off":
            git = self._git_reader.read(root)
            if git is None:
                warnings.append(
                    WarningRecord(
                        code="GIT_METADATA_UNAVAILABLE",
                        message="read-only Git metadata could not be obtained",
                    )
                )
        partial = walk.limit is not None
        return InspectionResult(
            status="partial" if partial else "ok",
            partial=partial,
            repository_type=repository_type,
            resolved_root=".",
            requested_path=sanitize_text(request.requested_path),
            file_count=walk.file_count,
            directory_count=walk.directory_count,
            total_metadata_size=walk.total_metadata_size,
            content_bytes_read=0,
            entries=walk.entries,
            language_summary=walk.language_summary,
            manifest_summary=walk.manifest_summary,
            test_directory_count=walk.test_directory_count,
            documentation_count=walk.documentation_count,
            git=git,
            exclusion_summary=walk.exclusion_summary,
            sensitive_entries=walk.sensitive_entries,
            limit=walk.limit,
            warnings=tuple(warnings),
        )

    def _assert_allowed(self, root: Path) -> None:
        target = TargetResource(ref=root.name or str(root), resource_type="repository")
        action = ActionName(
            capability=Capability.REPOSITORY_METADATA_READ,
            category=ActionCategory.READ,
            target=target,
        )
        decision = self._engine.decide(
            PolicyRequest(
                mode=OperatingMode.READ_ONLY,
                action=action,
                target=target,
                allowlist_result=None,
                approval=None,
            )
        )
        if not decision.allowed:
            raise PolicyDeniedError(
                f"policy denied inspection: {decision.reason_code.value}"
            )
