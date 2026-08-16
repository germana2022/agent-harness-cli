import datetime

import pytest

from agent_harness.domain import (
    TERMINAL_STATES,
    ApprovalDecision,
    ApprovalRecord,
    ApprovalRequest,
    ApprovalState,
    OperatingMode,
)
from agent_harness.domain.errors import InvalidDomainValue

from conftest import make_action, make_target

TZ = datetime.timezone.utc
NOW = datetime.datetime(2026, 1, 1, tzinfo=TZ)


def make_request(**overrides):
    defaults = {
        "request_id": "req-1",
        "action": make_action(),
        "target": make_target(),
        "required_mode": OperatingMode.WORKSPACE_WRITE,
        "current_mode": OperatingMode.READ_ONLY,
        "scope": "scope-1",
        "requesting_component": "tests",
        "rationale": "because",
        "created_at": NOW,
        "expires_at": None,
        "evidence_refs": (),
        "is_external": False,
        "is_destructive": False,
    }
    defaults.update(overrides)
    return ApprovalRequest(**defaults)


def test_request_valid_construction():
    request = make_request()
    assert request.request_id == "req-1"
    assert request.scope == "scope-1"
    assert request.is_external is False


def test_request_normalizes_identifiers():
    request = make_request(request_id="  req-1  ", scope="\x00scope\x00  ")
    assert request.request_id == "req-1"
    assert request.scope == "scope"


def test_request_rejects_empty_identifiers():
    with pytest.raises(InvalidDomainValue):
        make_request(request_id="")
    with pytest.raises(InvalidDomainValue):
        make_request(scope="   ")
    with pytest.raises(InvalidDomainValue):
        make_request(requesting_component="")
    with pytest.raises(InvalidDomainValue):
        make_request(rationale="")


def test_request_rejects_bad_action_target_and_modes():
    with pytest.raises(InvalidDomainValue):
        make_request(action="bad")
    with pytest.raises(InvalidDomainValue):
        make_request(target="bad")
    with pytest.raises(InvalidDomainValue):
        make_request(required_mode="bad")
    with pytest.raises(InvalidDomainValue):
        make_request(current_mode="bad")


def test_request_rejects_naive_timestamps():
    with pytest.raises(InvalidDomainValue):
        make_request(created_at=datetime.datetime(2026, 1, 1))
    with pytest.raises(InvalidDomainValue):
        make_request(created_at=NOW, expires_at=datetime.datetime(2026, 1, 2))


def test_request_rejects_expiry_before_creation():
    with pytest.raises(InvalidDomainValue):
        make_request(created_at=NOW, expires_at=NOW - datetime.timedelta(minutes=1))


def test_request_rejects_non_tuple_evidence_refs():
    with pytest.raises(InvalidDomainValue):
        make_request(evidence_refs=["a", "b"])


def test_record_valid_construction():
    record = ApprovalRecord(
        approval_id="appr-1",
        request_id="req-1",
        decision=ApprovalDecision.APPROVED,
        scope="scope-1",
        action=make_action(),
        target=make_target(),
        required_mode=OperatingMode.WORKSPACE_WRITE,
        approver="human",
        decided_at=NOW,
        expires_at=None,
        state=ApprovalState.APPROVED,
    )
    assert record.reason == "approved"
    assert record.state is ApprovalState.APPROVED


def test_record_rejects_invalid_fields():
    kwargs = {
        "approval_id": "appr-1",
        "request_id": "req-1",
        "decision": ApprovalDecision.APPROVED,
        "scope": "scope-1",
        "action": make_action(),
        "target": make_target(),
        "required_mode": OperatingMode.WORKSPACE_WRITE,
        "approver": "human",
        "decided_at": NOW,
        "expires_at": None,
        "state": ApprovalState.APPROVED,
    }
    with pytest.raises(InvalidDomainValue):
        ApprovalRecord(**{**kwargs, "approval_id": ""})
    with pytest.raises(InvalidDomainValue):
        ApprovalRecord(**{**kwargs, "approver": "  "})
    with pytest.raises(InvalidDomainValue):
        ApprovalRecord(**{**kwargs, "decision": "bad"})
    with pytest.raises(InvalidDomainValue):
        ApprovalRecord(**{**kwargs, "state": "bad"})
    with pytest.raises(InvalidDomainValue):
        ApprovalRecord(**{**kwargs, "action": "bad"})
    with pytest.raises(InvalidDomainValue):
        ApprovalRecord(**{**kwargs, "target": "bad"})
    with pytest.raises(InvalidDomainValue):
        ApprovalRecord(**{**kwargs, "required_mode": "bad"})
    with pytest.raises(InvalidDomainValue):
        ApprovalRecord(**{**kwargs, "decided_at": datetime.datetime(2026, 1, 1)})


def test_record_rejects_expiry_before_decision():
    kwargs = {
        "approval_id": "appr-1",
        "request_id": "req-1",
        "decision": ApprovalDecision.APPROVED,
        "scope": "scope-1",
        "action": make_action(),
        "target": make_target(),
        "required_mode": OperatingMode.WORKSPACE_WRITE,
        "approver": "human",
        "decided_at": NOW,
        "state": ApprovalState.APPROVED,
    }
    with pytest.raises(InvalidDomainValue):
        ApprovalRecord(**{**kwargs, "expires_at": NOW - datetime.timedelta(seconds=1)})
    # Equal is allowed (immediately expired, fail closed) but not rejected.
    record = ApprovalRecord(**{**kwargs, "expires_at": NOW})
    assert record.expires_at == NOW


def test_request_rejects_non_utc_offset():
    tz5 = datetime.timezone(datetime.timedelta(hours=5))
    with pytest.raises(InvalidDomainValue):
        make_request(created_at=datetime.datetime(2026, 1, 1, tzinfo=tz5))
    with pytest.raises(InvalidDomainValue):
        make_request(
            created_at=NOW,
            expires_at=datetime.datetime(2026, 1, 2, tzinfo=tz5),
        )


def test_record_naive_consumed_at_rejected():
    kwargs = {
        "approval_id": "appr-1",
        "request_id": "req-1",
        "decision": ApprovalDecision.APPROVED,
        "scope": "scope-1",
        "action": make_action(),
        "target": make_target(),
        "required_mode": OperatingMode.WORKSPACE_WRITE,
        "approver": "human",
        "decided_at": NOW,
        "expires_at": None,
        "state": ApprovalState.APPROVED,
        "consumed_at": datetime.datetime(2026, 1, 1),
    }
    with pytest.raises(InvalidDomainValue):
        ApprovalRecord(**kwargs)


def test_record_with_evidence_ref_and_correlation_id():
    record = ApprovalRecord(
        approval_id="appr-1",
        request_id="req-1",
        decision=ApprovalDecision.APPROVED,
        scope="scope-1",
        action=make_action(),
        target=make_target(),
        required_mode=OperatingMode.WORKSPACE_WRITE,
        approver="human",
        decided_at=NOW,
        expires_at=None,
        state=ApprovalState.APPROVED,
        evidence_ref="evidence-1",
        correlation_id="corr-1",
    )
    assert record.evidence_ref == "evidence-1"
    assert record.correlation_id == "corr-1"


def test_record_rejects_empty_evidence_ref():
    kwargs = {
        "approval_id": "appr-1",
        "request_id": "req-1",
        "decision": ApprovalDecision.APPROVED,
        "scope": "scope-1",
        "action": make_action(),
        "target": make_target(),
        "required_mode": OperatingMode.WORKSPACE_WRITE,
        "approver": "human",
        "decided_at": NOW,
        "expires_at": None,
        "state": ApprovalState.APPROVED,
        "evidence_ref": "   ",
    }
    with pytest.raises(InvalidDomainValue):
        ApprovalRecord(**kwargs)


def test_terminal_states():
    assert TERMINAL_STATES == {
        ApprovalState.DENIED,
        ApprovalState.EXPIRED,
        ApprovalState.REVOKED,
        ApprovalState.CONSUMED,
    }


def test_request_is_immutable():
    request = make_request()
    with pytest.raises(Exception):
        request.scope = "changed"  # type: ignore[misc]


def test_record_is_immutable():
    record = ApprovalRecord(
        approval_id="appr-1",
        request_id="req-1",
        decision=ApprovalDecision.APPROVED,
        scope="scope-1",
        action=make_action(),
        target=make_target(),
        required_mode=OperatingMode.WORKSPACE_WRITE,
        approver="human",
        decided_at=NOW,
        expires_at=None,
        state=ApprovalState.APPROVED,
    )
    with pytest.raises(Exception):
        record.state = ApprovalState.CONSUMED  # type: ignore[misc]
