import pytest

from agent_harness.inspection import (
    DEFAULT_MAX_DEPTH,
    DEFAULT_MAX_ENTRIES,
    HARD_MAX_DEPTH,
    HARD_MAX_ENTRIES,
    InspectionRequest,
)
from agent_harness.inspection.errors import InvalidInspectionRequestError


def test_defaults_are_valid():
    request = InspectionRequest()
    assert request.requested_path == "."
    assert request.max_entries == DEFAULT_MAX_ENTRIES
    assert request.max_depth == DEFAULT_MAX_DEPTH
    assert request.include_hidden is False
    assert request.include_ignored is False
    assert request.git_metadata == "auto"
    assert request.link_policy == "classify"
    assert request.error_policy == "skip_warn"


def test_valid_custom_values():
    request = InspectionRequest(
        requested_path="src",
        max_entries=100,
        max_depth=5,
        max_individual_file_bytes=0,
        include_hidden=True,
        git_metadata="off",
        link_policy="error",
        error_policy="fail",
    )
    assert request.requested_path == "src"
    assert request.max_entries == 100
    assert request.max_individual_file_bytes == 0


def test_boundary_values_accepted():
    InspectionRequest(max_entries=1)
    InspectionRequest(max_entries=HARD_MAX_ENTRIES)
    InspectionRequest(max_depth=1)
    InspectionRequest(max_depth=HARD_MAX_DEPTH)


def test_zero_bytes_is_unlimited():
    request = InspectionRequest(max_individual_file_bytes=0)
    assert request.max_individual_file_bytes == 0


@pytest.mark.parametrize(
    "kwargs",
    [
        {"max_entries": 0},
        {"max_entries": -1},
        {"max_entries": HARD_MAX_ENTRIES + 1},
        {"max_depth": 0},
        {"max_depth": HARD_MAX_DEPTH + 1},
        {"max_directories": 0},
        {"max_warnings": 0},
        {"max_path_length": 0},
        {"max_manifests": 0},
        {"max_languages": 0},
        {"max_individual_file_bytes": -1},
        {"max_total_bytes": -1},
        {"requested_path": ""},
        {"requested_path": "   "},
    ],
)
def test_invalid_values_rejected(kwargs):
    with pytest.raises(InvalidInspectionRequestError):
        InspectionRequest(**kwargs)


@pytest.mark.parametrize(
    "field",
    [
        {"git_metadata": "always"},
        {"link_policy": "follow"},
        {"error_policy": "ignore"},
    ],
)
def test_invalid_mode_rejected(field):
    with pytest.raises(InvalidInspectionRequestError):
        InspectionRequest(**field)


def test_wrong_types_rejected():
    with pytest.raises(InvalidInspectionRequestError):
        InspectionRequest(max_entries="100")
    with pytest.raises(InvalidInspectionRequestError):
        InspectionRequest(max_entries=True)
    with pytest.raises(InvalidInspectionRequestError):
        InspectionRequest(requested_path=123)


def test_request_is_immutable():
    request = InspectionRequest()
    with pytest.raises(Exception):
        request.max_entries = 5  # type: ignore[misc]
