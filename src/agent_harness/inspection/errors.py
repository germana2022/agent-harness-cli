"""Inspection error taxonomy and sanitization helpers.

Expected operational denials are raised as :class:`InspectionError` subtypes
with a stable machine-readable code and an exit code; the CLI boundary
translates them without tracebacks.
"""

from __future__ import annotations

import re

from agent_harness.domain.errors import DomainError

_CONTROL = re.compile(r"[\x00-\x1f\x7f]")
_MAX_SANITIZED_LENGTH = 1024


def sanitize_text(value: str) -> str:
    """Strip control characters and bound length for safe output."""
    cleaned = _CONTROL.sub("", value)
    return cleaned[:_MAX_SANITIZED_LENGTH]


class InspectionError(DomainError):
    """Base class for expected inspection failures."""

    code = "INSPECTION_INTERNAL_ERROR"
    exit_code = 10

    def __init__(self, message: str) -> None:
        super().__init__(sanitize_text(message))
        self.message = sanitize_text(message)


class PathNotFoundError(InspectionError):
    code = "PATH_NOT_FOUND"
    exit_code = 2


class PathNotDirectoryError(InspectionError):
    code = "PATH_NOT_DIRECTORY"
    exit_code = 2


class PermissionDeniedError(InspectionError):
    code = "INSPECTION_PERMISSION_DENIED"
    exit_code = 3


class RootResolutionError(InspectionError):
    code = "ROOT_RESOLUTION_FAILED"
    exit_code = 3


class PathEscapeError(InspectionError):
    code = "PATH_ESCAPE"
    exit_code = 2


class LinkEncounteredError(InspectionError):
    """Raised when a link is encountered under ``link_policy="error"``."""

    code = "LINK_NOT_FOLLOWED"
    exit_code = 10


class UnsupportedEntryError(InspectionError):
    """Raised when an unsupported special entry is encountered and the
    error policy requires failure."""

    code = "UNSUPPORTED_ENTRY"
    exit_code = 10


class InvalidInspectionRequestError(InspectionError):
    code = "INVALID_INSPECTION_REQUEST"
    exit_code = 3


class PolicyDeniedError(InspectionError):
    """Raised when the Phase 2 policy denies the inspection request."""

    code = "POLICY_DENIED"
    exit_code = 3


class InspectionInternalError(InspectionError):
    code = "INSPECTION_INTERNAL_ERROR"
    exit_code = 10
