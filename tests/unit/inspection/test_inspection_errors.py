import pytest

from agent_harness.domain.errors import DomainError
from agent_harness.inspection.errors import (
    InspectionError,
    InspectionInternalError,
    InvalidInspectionRequestError,
    LinkEncounteredError,
    PathEscapeError,
    PathNotDirectoryError,
    PathNotFoundError,
    PermissionDeniedError,
    PolicyDeniedError,
    RootResolutionError,
    UnsupportedEntryError,
    sanitize_text,
)

_ALL = (
    InspectionError,
    InspectionInternalError,
    InvalidInspectionRequestError,
    LinkEncounteredError,
    PathEscapeError,
    PathNotDirectoryError,
    PathNotFoundError,
    PermissionDeniedError,
    PolicyDeniedError,
    RootResolutionError,
    UnsupportedEntryError,
)


def test_all_inherit_from_domain_error():
    for cls in _ALL:
        assert issubclass(cls, DomainError)


def test_exit_codes():
    assert PathNotFoundError("x").exit_code == 2
    assert PathNotDirectoryError("x").exit_code == 2
    assert PathEscapeError("x").exit_code == 2
    assert PermissionDeniedError("x").exit_code == 3
    assert RootResolutionError("x").exit_code == 3
    assert InvalidInspectionRequestError("x").exit_code == 3
    assert PolicyDeniedError("x").exit_code == 3
    assert InspectionInternalError("x").exit_code == 10
    assert LinkEncounteredError("x").exit_code == 10
    assert UnsupportedEntryError("x").exit_code == 10


def test_codes():
    assert PathNotFoundError("x").code == "PATH_NOT_FOUND"
    assert PermissionDeniedError("x").code == "INSPECTION_PERMISSION_DENIED"
    assert LinkEncounteredError("x").code == "LINK_NOT_FOUND".replace("_FOUND", "_FOLLOWED")


def test_sanitize_text_strips_control_characters():
    assert sanitize_text("a\x1b[31mred\x00b") == "a[31mredb"


def test_sanitize_text_bounds_length():
    assert len(sanitize_text("x" * 5000)) == 1024


def test_error_message_is_sanitized():
    error = PathNotFoundError("bad\x1bpath")
    assert "\x1b" not in str(error)
    assert "badpath" in str(error)
