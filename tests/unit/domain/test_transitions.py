import datetime
from dataclasses import FrozenInstanceError

import pytest

from agent_harness.domain import (
    ApprovalDecision,
    ApprovalRequest,
    InMemoryApprovalManager,
    ModeTransitionRequest,
    OperatingMode,
    PolicyReasonCode,
    TransitionDecision,
    evaluate_transition,
    transition_scope,
)

from conftest import make_action

R = OperatingMode.READ_ONLY
W = OperatingMode.WORKSPACE_WRITE
D = OperatingMode.DELIVERY


def _transition_approval(manager, clock, from_mode, to_mode, *, expires_at=None):
    action = make_action()
    request = ApprovalRequest(
        request_id=f"tr-{from_mode.value}-{to_mode.value}",
        action=action,
        target=action.target,
        required_mode=to_mode,
        current_mode=from_mode,
        scope=transition_scope(from_mode, to_mode),
        requesting_component="tests",
        rationale="escalation",
        created_at=clock.now(),
        expires_at=expires_at,
    )
    manager.request(request)
    return manager.record_decision(
        request.request_id, ApprovalDecision.APPROVED, "human", "ok"
    )


def test_allowed_escalations_require_approval(clock):
    for from_mode, to_mode in ((R, W), (R, D), (W, D)):
        manager = InMemoryApprovalManager(clock)
        result = evaluate_transition(
            ModeTransitionRequest(from_mode=from_mode, to_mode=to_mode),
            manager,
            None,
            clock.now(),
        )
        assert result.allowed is False
        assert result.reason_code is PolicyReasonCode.APPROVAL_REQUIRED
        assert result.approval_required is True
        # with a valid authoritative approval
        approval = _transition_approval(manager, clock, from_mode, to_mode)
        ok = evaluate_transition(
            ModeTransitionRequest(from_mode=from_mode, to_mode=to_mode),
            manager,
            approval.approval_id,
            clock.now(),
        )
        assert ok.allowed is True
        assert ok.reason_code is PolicyReasonCode.ALLOWED
        assert ok.approval_id == approval.approval_id


def test_restrictive_transitions_do_not_require_approval(clock):
    for from_mode, to_mode in ((W, R), (D, W), (D, R)):
        result = evaluate_transition(
            ModeTransitionRequest(from_mode=from_mode, to_mode=to_mode),
            None,
            None,
            clock.now(),
        )
        assert result.allowed is True
        assert result.approval_required is False
        assert result.reason_code is PolicyReasonCode.ALLOWED


def test_identity_transition_is_unsupported(clock):
    for mode in (R, W, D):
        result = evaluate_transition(
            ModeTransitionRequest(from_mode=mode, to_mode=mode), None, None, clock.now()
        )
        assert result.allowed is False
        assert result.reason_code is PolicyReasonCode.UNSUPPORTED_TRANSITION


def test_escalation_wrong_scope_approval_denies(clock):
    manager = InMemoryApprovalManager(clock)
    approval = _transition_approval(manager, clock, R, W)
    result = evaluate_transition(
        ModeTransitionRequest(from_mode=R, to_mode=D), manager, approval.approval_id, clock.now()
    )
    assert result.allowed is False
    assert result.reason_code is PolicyReasonCode.APPROVAL_SCOPE_MISMATCH


def test_escalation_expired_approval_denies(clock):
    manager = InMemoryApprovalManager(clock)
    approval = _transition_approval(
        manager,
        clock,
        R,
        W,
        expires_at=clock.now() + datetime.timedelta(minutes=10),
    )
    clock.advance(datetime.timedelta(minutes=11))
    result = evaluate_transition(
        ModeTransitionRequest(from_mode=R, to_mode=W), manager, approval.approval_id, clock.now()
    )
    assert result.allowed is False
    assert result.reason_code is PolicyReasonCode.APPROVAL_EXPIRED


def test_escalation_consumed_approval_denies(clock):
    manager = InMemoryApprovalManager(clock)
    approval = _transition_approval(manager, clock, R, W)
    manager.consume(approval.approval_id)
    result = evaluate_transition(
        ModeTransitionRequest(from_mode=R, to_mode=W), manager, approval.approval_id, clock.now()
    )
    assert result.allowed is False
    assert result.reason_code is PolicyReasonCode.APPROVAL_CONSUMED


def test_escalation_without_authority_fails_closed(clock):
    result = evaluate_transition(
        ModeTransitionRequest(from_mode=R, to_mode=W), None, "appr-anything", clock.now()
    )
    assert result.allowed is False
    assert result.reason_code is PolicyReasonCode.APPROVAL_MISSING


def test_forged_approval_id_cannot_authorize_transition(clock):
    manager = InMemoryApprovalManager(clock)
    result = evaluate_transition(
        ModeTransitionRequest(from_mode=R, to_mode=W), manager, "appr-forged", clock.now()
    )
    assert result.allowed is False
    assert result.reason_code is PolicyReasonCode.APPROVAL_MISSING


def test_transition_scope_format():
    assert transition_scope(R, W) == "mode_transition:read_only:workspace_write"


def test_transition_decision_is_immutable_and_has_evidence(clock):
    result = evaluate_transition(
        ModeTransitionRequest(from_mode=W, to_mode=R), None, None, clock.now()
    )
    assert isinstance(result, TransitionDecision)
    assert result.timestamp == clock.now()
    assert result.evidence == ()
    with pytest.raises(FrozenInstanceError):
        result.allowed = False  # type: ignore[misc]
