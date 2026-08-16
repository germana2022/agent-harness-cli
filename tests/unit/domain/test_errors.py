import datetime

import pytest

from agent_harness.domain.errors import (
    ApprovalLifecycleError,
    DomainError,
    InternalDomainError,
    InvalidDomainValue,
    InvalidTransition,
    PolicyConfigurationError,
    validate_identifier,
    validate_utc,
)

ALL_ERRORS = (
    DomainError,
    InvalidDomainValue,
    InvalidTransition,
    ApprovalLifecycleError,
    PolicyConfigurationError,
    InternalDomainError,
)


def test_all_domain_errors_inherit_from_domain_error():
    for cls in ALL_ERRORS:
        assert issubclass(cls, Exception)


def test_domain_error_subclasses():
    assert issubclass(InvalidDomainValue, DomainError)
    assert issubclass(InvalidTransition, DomainError)
    assert issubclass(ApprovalLifecycleError, DomainError)
    assert issubclass(PolicyConfigurationError, DomainError)
    assert issubclass(InternalDomainError, DomainError)


def test_validate_identifier_normalizes():
    assert validate_identifier("  repo:main  ", "ref") == "repo:main"
    assert validate_identifier("a\x1b[31mb", "ref") == "a[31mb"


def test_validate_identifier_rejects_empty():
    with pytest.raises(InvalidDomainValue):
        validate_identifier("", "ref")
    with pytest.raises(InvalidDomainValue):
        validate_identifier("   ", "ref")
    with pytest.raises(InvalidDomainValue):
        validate_identifier("\x00", "ref")


def test_validate_identifier_rejects_non_string():
    with pytest.raises(InvalidDomainValue):
        validate_identifier(123, "ref")


def test_validate_utc_accepts_aware_utc():
    stamp = datetime.datetime(2026, 1, 1, tzinfo=datetime.timezone.utc)
    assert validate_utc(stamp, "created_at") is stamp


def test_validate_utc_rejects_naive():
    with pytest.raises(InvalidDomainValue):
        validate_utc(datetime.datetime(2026, 1, 1), "created_at")


def test_validate_utc_rejects_non_zero_offset():
    tz5 = datetime.timezone(datetime.timedelta(hours=5))
    stamp = datetime.datetime(2026, 1, 1, 5, tzinfo=tz5)
    with pytest.raises(InvalidDomainValue):
        validate_utc(stamp, "created_at")


def test_domain_error_is_catchable_as_exception():
    with pytest.raises(Exception):
        raise InvalidDomainValue("boom")


def test_denials_are_not_errors_by_construction():
    from agent_harness.domain import PolicyDecision, PolicyReasonCode

    decision = PolicyDecision(
        allowed=False,
        reason_code=PolicyReasonCode.APPROVAL_REQUIRED,
        message="approval required",
        approval_required=True,
    )
    assert decision.allowed is False
    assert not isinstance(decision, Exception)
