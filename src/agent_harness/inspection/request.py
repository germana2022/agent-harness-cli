"""Immutable inspection request contract with mandatory bounded limits."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from .errors import InvalidInspectionRequestError

HARD_MAX_ENTRIES = 1_000_000
HARD_MAX_DIRECTORIES = 100_000
HARD_MAX_DEPTH = 1_024
HARD_MAX_FILE_BYTES = 10 * 1024**3
HARD_MAX_TOTAL_BYTES = 100 * 1024**3
HARD_MAX_PATH_LENGTH = 4_096
HARD_MAX_WARNINGS = 1_000
HARD_MAX_MANIFESTS = 5_000
HARD_MAX_LANGUAGES = 1_000

DEFAULT_MAX_ENTRIES = 20_000
DEFAULT_MAX_DIRECTORIES = 2_000
DEFAULT_MAX_DEPTH = 64
DEFAULT_MAX_FILE_BYTES = 100 * 1024**2
DEFAULT_MAX_TOTAL_BYTES = 10 * 1024**3
DEFAULT_MAX_PATH_LENGTH = 4_096
DEFAULT_MAX_WARNINGS = 1_000
DEFAULT_MAX_MANIFESTS = 500
DEFAULT_MAX_LANGUAGES = 100

GitMetadataMode = Literal["auto", "on", "off"]
LinkPolicy = Literal["classify", "error"]
ErrorPolicy = Literal["skip_warn", "fail"]

_VALID_GIT_MODES = ("auto", "on", "off")
_VALID_LINK_POLICIES = ("classify", "error")
_VALID_ERROR_POLICIES = ("skip_warn", "fail")


@dataclass(frozen=True)
class InspectionRequest:
    """A validated, immutable inspection request.

    Mandatory limits are always finite: entry/directory/depth limits must be
    at least one and never exceed their hard maxima. Byte limits may be zero
    (meaning unlimited) because inspection never reads file content.
    """

    requested_path: str = "."
    max_entries: int = DEFAULT_MAX_ENTRIES
    max_directories: int = DEFAULT_MAX_DIRECTORIES
    max_depth: int = DEFAULT_MAX_DEPTH
    max_individual_file_bytes: int = DEFAULT_MAX_FILE_BYTES
    max_total_bytes: int = DEFAULT_MAX_TOTAL_BYTES
    max_path_length: int = DEFAULT_MAX_PATH_LENGTH
    max_warnings: int = DEFAULT_MAX_WARNINGS
    max_manifests: int = DEFAULT_MAX_MANIFESTS
    max_languages: int = DEFAULT_MAX_LANGUAGES
    include_hidden: bool = False
    include_ignored: bool = False
    git_metadata: GitMetadataMode = "auto"
    link_policy: LinkPolicy = "classify"
    error_policy: ErrorPolicy = "skip_warn"

    def __post_init__(self) -> None:
        self._check_str("requested_path", self.requested_path, required=True)
        self._check_range("max_entries", self.max_entries, 1, HARD_MAX_ENTRIES)
        self._check_range("max_directories", self.max_directories, 1, HARD_MAX_DIRECTORIES)
        self._check_range("max_depth", self.max_depth, 1, HARD_MAX_DEPTH)
        self._check_range(
            "max_individual_file_bytes", self.max_individual_file_bytes, 0, HARD_MAX_FILE_BYTES
        )
        self._check_range("max_total_bytes", self.max_total_bytes, 0, HARD_MAX_TOTAL_BYTES)
        self._check_range("max_path_length", self.max_path_length, 1, HARD_MAX_PATH_LENGTH)
        self._check_range("max_warnings", self.max_warnings, 1, HARD_MAX_WARNINGS)
        self._check_range("max_manifests", self.max_manifests, 1, HARD_MAX_MANIFESTS)
        self._check_range("max_languages", self.max_languages, 1, HARD_MAX_LANGUAGES)
        for value, allowed, field in (
            (self.git_metadata, _VALID_GIT_MODES, "git_metadata"),
            (self.link_policy, _VALID_LINK_POLICIES, "link_policy"),
            (self.error_policy, _VALID_ERROR_POLICIES, "error_policy"),
        ):
            if value not in allowed:
                raise InvalidInspectionRequestError(
                    f"invalid {field} {value!r}; must be one of {allowed}"
                )

    @staticmethod
    def _check_str(field: str, value: object, *, required: bool) -> None:
        if not isinstance(value, str) or (required and not value.strip()):
            raise InvalidInspectionRequestError(f"{field} must be a nonempty string")

    @staticmethod
    def _check_range(field: str, value: object, low: int, high: int) -> None:
        if not isinstance(value, int) or isinstance(value, bool):
            raise InvalidInspectionRequestError(f"{field} must be an integer")
        if value < low or value > high:
            raise InvalidInspectionRequestError(
                f"{field} must be between {low} and {high}"
            )
