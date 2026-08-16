import datetime

import pytest

from agent_harness.domain import (
    ApprovalDecision,
    ApprovalRequest,
    ApprovalState,
    InMemoryApprovalManager,
    OperatingMode,
    PolicyReasonCode,
    action_scope,
    transition_scope,
)
from agent_harness.domain.errors import ApprovalLifecycleError

from conftest import make_action, make_target

_seq = [0]


def _request(
    clock,
    request_id="req-1",
    *,
    expires_at=None,
    scope=None,
    mode=OperatingMode.WORKSPACE_WRITE,
):
    _seq[0] += 1
    rid = request_id if request_id != "req-1" else f"req-{_seq[0]}"
    action = make_action()
    return ApprovalRequest(
        request_id=rid,
        action=action,
        target=action.target,
        required_mode=mode,
        current_mode=mode,
        scope=scope or action_scope(action),
        requesting_component="tests",
        rationale="test",
        created_at=clock.now(),
        expires_at=expires_at,
    )


def test_request_and_decision_lifecycle(clock):
    manager = InMemoryApprovalManager(clock)
    request = _request(clock)
    manager.request(request)
    record = manager.record_decision(
        request.request_id, ApprovalDecision.APPROVED, approver="human", reason="ok"
    )
    assert record.state is ApprovalState.APPROVED
    assert record.decision is ApprovalDecision.APPROVED
    assert record.approver == "human"
    assert manager.get(record.approval_id) == record


def test_denied_decision_state(clock):
    manager = InMemoryApprovalManager(clock)
    request = _request(clock)
    manager.request(request)
    record = manager.record_decision(
        request.request_id, ApprovalDecision.DENIED, approver="human", reason="no"
    )
    assert record.state is ApprovalState.DENIED


def test_duplicate_request_id_rejected(clock):
    manager = InMemoryApprovalManager(clock)
    manager.request(_request(clock, request_id="dup"))
    with pytest.raises(ApprovalLifecycleError):
        manager.request(_request(clock, request_id="dup"))


def test_duplicate_decision_rejected(clock):
    manager = InMemoryApprovalManager(clock)
    request = _request(clock)
    manager.request(request)
    manager.record_decision(request.request_id, ApprovalDecision.APPROVED, "human", "ok")
    with pytest.raises(ApprovalLifecycleError):
        manager.record_decision(request.request_id, ApprovalDecision.APPROVED, "human", "again")


def test_unknown_request_id_rejected(clock):
    manager = InMemoryApprovalManager(clock)
    with pytest.raises(ApprovalLifecycleError):
        manager.record_decision("missing", ApprovalDecision.APPROVED, "h", "r")


def test_get_unknown_approval_rejected(clock):
    manager = InMemoryApprovalManager(clock)
    with pytest.raises(ApprovalLifecycleError):
        manager.get("missing")


def test_authorize_unknown_approval_returns_missing(clock):
    manager = InMemoryApprovalManager(clock)
    action = make_action()
    decision = manager.authorize_action(
        "missing", action, action.target, OperatingMode.WORKSPACE_WRITE, clock.now()
    )
    assert decision.allowed is False
    assert decision.reason_code is PolicyReasonCode.APPROVAL_MISSING


def test_authorize_valid_approval(clock):
    manager = InMemoryApprovalManager(clock)
    request = _request(clock)
    manager.request(request)
    record = manager.record_decision(
        request.request_id, ApprovalDecision.APPROVED, "human", "ok"
    )
    decision = manager.authorize_action(
        record.approval_id,
        request.action,
        request.target,
        OperatingMode.WORKSPACE_WRITE,
        clock.now(),
    )
    assert decision.allowed is True
    assert decision.reason_code is PolicyReasonCode.ALLOWED


def test_authorize_target_mismatch(clock):
    manager = InMemoryApprovalManager(clock)
    request = _request(clock)
    manager.request(request)
    record = manager.record_decision(
        request.request_id, ApprovalDecision.APPROVED, "human", "ok"
    )
    other_target = make_target(ref="repo:main:other")
    decision = manager.authorize_action(
        record.approval_id,
        request.action,
        other_target,
        OperatingMode.WORKSPACE_WRITE,
        clock.now(),
    )
    assert decision.allowed is False
    assert decision.reason_code is PolicyReasonCode.APPROVAL_SCOPE_MISMATCH


def test_authorize_scope_mismatch(clock):
    manager = InMemoryApprovalManager(clock)
    request = _request(clock, scope="wrong-scope")
    manager.request(request)
    record = manager.record_decision(
        request.request_id, ApprovalDecision.APPROVED, "human", "ok"
    )
    decision = manager.authorize_action(
        record.approval_id,
        request.action,
        request.target,
        OperatingMode.WORKSPACE_WRITE,
        clock.now(),
    )
    assert decision.allowed is False
    assert decision.reason_code is PolicyReasonCode.APPROVAL_SCOPE_MISMATCH


def test_authorize_mode_mismatch(clock):
    manager = InMemoryApprovalManager(clock)
    request = _request(clock, mode=OperatingMode.DELIVERY)
    manager.request(request)
    record = manager.record_decision(
        request.request_id, ApprovalDecision.APPROVED, "human", "ok"
    )
    decision = manager.authorize_action(
        record.approval_id,
        request.action,
        request.target,
        OperatingMode.WORKSPACE_WRITE,
        clock.now(),
    )
    assert decision.allowed is False
    assert decision.reason_code is PolicyReasonCode.APPROVAL_SCOPE_MISMATCH


def test_authorize_transition_scope_and_mode(clock):
    manager = InMemoryApprovalManager(clock)
    action = make_action()
    request = ApprovalRequest(
        request_id="tr",
        action=action,
        target=action.target,
        required_mode=OperatingMode.WORKSPACE_WRITE,
        current_mode=OperatingMode.READ_ONLY,
        scope=transition_scope(OperatingMode.READ_ONLY, OperatingMode.WORKSPACE_WRITE),
        requesting_component="tests",
        rationale="escalation",
        created_at=clock.now(),
    )
    manager.request(request)
    record = manager.record_decision("tr", ApprovalDecision.APPROVED, "human", "ok")
    ok = manager.authorize_transition(
        record.approval_id,
        OperatingMode.READ_ONLY,
        OperatingMode.WORKSPACE_WRITE,
        clock.now(),
    )
    assert ok.allowed is True
    wrong = manager.authorize_transition(
        record.approval_id,
        OperatingMode.WORKSPACE_WRITE,
        OperatingMode.DELIVERY,
        clock.now(),
    )
    assert wrong.allowed is False
    assert wrong.reason_code is PolicyReasonCode.APPROVAL_SCOPE_MISMATCH


def test_consume_single_use(clock):
    manager = InMemoryApprovalManager(clock)
    request = _request(clock)
    manager.request(request)
    record = manager.record_decision(
        request.request_id, ApprovalDecision.APPROVED, "human", "ok"
    )
    consumed = manager.consume(record.approval_id)
    assert consumed.state is ApprovalState.CONSUMED
    assert consumed.consumed_at == clock.now()
    decision = manager.authorize_action(
        consumed.approval_id,
        request.action,
        request.target,
        OperatingMode.WORKSPACE_WRITE,
        clock.now(),
    )
    assert decision.allowed is False
    assert decision.reason_code is PolicyReasonCode.APPROVAL_CONSUMED


def test_consume_again_rejected(clock):
    manager = InMemoryApprovalManager(clock)
    request = _request(clock)
    manager.request(request)
    record = manager.record_decision(
        request.request_id, ApprovalDecision.APPROVED, "human", "ok"
    )
    manager.consume(record.approval_id)
    with pytest.raises(ApprovalLifecycleError):
        manager.consume(record.approval_id)


def test_consume_denied_rejected(clock):
    manager = InMemoryApprovalManager(clock)
    request = _request(clock)
    manager.request(request)
    record = manager.record_decision(
        request.request_id, ApprovalDecision.DENIED, "human", "no"
    )
    with pytest.raises(ApprovalLifecycleError):
        manager.consume(record.approval_id)


def test_consume_unknown_approval_rejected(clock):
    manager = InMemoryApprovalManager(clock)
    with pytest.raises(ApprovalLifecycleError):
        manager.consume("missing")


def test_revoke_unknown_approval_rejected(clock):
    manager = InMemoryApprovalManager(clock)
    with pytest.raises(ApprovalLifecycleError):
        manager.revoke("missing")


def test_consume_action_scoped_atomic(clock):
    manager = InMemoryApprovalManager(clock)
    request = _request(clock)
    manager.request(request)
    record = manager.record_decision(
        request.request_id, ApprovalDecision.APPROVED, "human", "ok"
    )
    decision = manager.consume_action(
        record.approval_id,
        request.action,
        request.target,
        OperatingMode.WORKSPACE_WRITE,
        clock.now(),
    )
    assert decision.allowed is True
    assert manager.get(record.approval_id).state is ApprovalState.CONSUMED
    # Second attempt denies and does not change state.
    again = manager.consume_action(
        record.approval_id,
        request.action,
        request.target,
        OperatingMode.WORKSPACE_WRITE,
        clock.now(),
    )
    assert again.allowed is False
    assert again.reason_code is PolicyReasonCode.APPROVAL_CONSUMED


def test_consume_action_scope_mismatch_does_not_consume(clock):
    manager = InMemoryApprovalManager(clock)
    request = _request(clock, scope="wrong-scope")
    manager.request(request)
    record = manager.record_decision(
        request.request_id, ApprovalDecision.APPROVED, "human", "ok"
    )
    decision = manager.consume_action(
        record.approval_id,
        request.action,
        request.target,
        OperatingMode.WORKSPACE_WRITE,
        clock.now(),
    )
    assert decision.allowed is False
    assert decision.reason_code is PolicyReasonCode.APPROVAL_SCOPE_MISMATCH
    assert manager.get(record.approval_id).state is ApprovalState.APPROVED


def test_consume_transition_scoped_atomic(clock):
    manager = InMemoryApprovalManager(clock)
    action = make_action()
    request = ApprovalRequest(
        request_id="tr2",
        action=action,
        target=action.target,
        required_mode=OperatingMode.WORKSPACE_WRITE,
        current_mode=OperatingMode.READ_ONLY,
        scope=transition_scope(OperatingMode.READ_ONLY, OperatingMode.WORKSPACE_WRITE),
        requesting_component="tests",
        rationale="escalation",
        created_at=clock.now(),
    )
    manager.request(request)
    record = manager.record_decision("tr2", ApprovalDecision.APPROVED, "human", "ok")
    decision = manager.consume_transition(
        record.approval_id,
        OperatingMode.READ_ONLY,
        OperatingMode.WORKSPACE_WRITE,
        clock.now(),
    )
    assert decision.allowed is True
    assert manager.get(record.approval_id).state is ApprovalState.CONSUMED


def test_consume_transition_mismatch_does_not_consume(clock):
    manager = InMemoryApprovalManager(clock)
    action = make_action()
    request = ApprovalRequest(
        request_id="tr3",
        action=action,
        target=action.target,
        required_mode=OperatingMode.WORKSPACE_WRITE,
        current_mode=OperatingMode.READ_ONLY,
        scope=transition_scope(OperatingMode.READ_ONLY, OperatingMode.WORKSPACE_WRITE),
        requesting_component="tests",
        rationale="escalation",
        created_at=clock.now(),
    )
    manager.request(request)
    record = manager.record_decision("tr3", ApprovalDecision.APPROVED, "human", "ok")
    decision = manager.consume_transition(
        record.approval_id,
        OperatingMode.READ_ONLY,
        OperatingMode.DELIVERY,
        clock.now(),
    )
    assert decision.allowed is False
    assert decision.reason_code is PolicyReasonCode.APPROVAL_SCOPE_MISMATCH
    assert manager.get(record.approval_id).state is ApprovalState.APPROVED


def test_revoke_approved(clock):
    manager = InMemoryApprovalManager(clock)
    request = _request(clock)
    manager.request(request)
    record = manager.record_decision(
        request.request_id, ApprovalDecision.APPROVED, "human", "ok"
    )
    revoked = manager.revoke(record.approval_id)
    assert revoked.state is ApprovalState.REVOKED
    assert revoked.revoked_at == clock.now()
    decision = manager.authorize_action(
        revoked.approval_id,
        request.action,
        request.target,
        OperatingMode.WORKSPACE_WRITE,
        clock.now(),
    )
    assert decision.allowed is False
    assert decision.reason_code is PolicyReasonCode.APPROVAL_REVOKED


def test_revoke_consumed_rejected(clock):
    manager = InMemoryApprovalManager(clock)
    request = _request(clock)
    manager.request(request)
    record = manager.record_decision(
        request.request_id, ApprovalDecision.APPROVED, "human", "ok"
    )
    manager.consume(record.approval_id)
    with pytest.raises(ApprovalLifecycleError):
        manager.revoke(record.approval_id)


def test_expiration_detected(clock):
    manager = InMemoryApprovalManager(clock)
    request = _request(
        clock, expires_at=clock.now() + datetime.timedelta(minutes=10)
    )
    manager.request(request)
    record = manager.record_decision(
        request.request_id, ApprovalDecision.APPROVED, "human", "ok"
    )
    clock.advance(datetime.timedelta(minutes=11))
    decision = manager.authorize_action(
        record.approval_id,
        request.action,
        request.target,
        OperatingMode.WORKSPACE_WRITE,
        clock.now(),
    )
    assert decision.allowed is False
    assert decision.reason_code is PolicyReasonCode.APPROVAL_EXPIRED
    assert manager.get(record.approval_id).state is ApprovalState.EXPIRED


def test_consume_expired_rejected(clock):
    manager = InMemoryApprovalManager(clock)
    request = _request(
        clock, expires_at=clock.now() + datetime.timedelta(minutes=10)
    )
    manager.request(request)
    record = manager.record_decision(
        request.request_id, ApprovalDecision.APPROVED, "human", "ok"
    )
    clock.advance(datetime.timedelta(minutes=11))
    decision = manager.consume_action(
        record.approval_id,
        record.action,
        record.target,
        OperatingMode.WORKSPACE_WRITE,
        clock.now(),
    )
    assert decision.allowed is False
    assert decision.reason_code is PolicyReasonCode.APPROVAL_EXPIRED


def test_concurrent_consume_is_single_use(clock):
    import threading

    manager = InMemoryApprovalManager(clock)
    request = _request(clock)
    manager.request(request)
    record = manager.record_decision(
        request.request_id, ApprovalDecision.APPROVED, "human", "ok"
    )
    errors = []
    barrier = threading.Barrier(4)

    def attempt():
        barrier.wait()
        try:
            manager.consume(record.approval_id)
        except ApprovalLifecycleError:
            errors.append(True)

    threads = [threading.Thread(target=attempt) for _ in range(4)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    assert len(errors) == 3
    assert manager.get(record.approval_id).state is ApprovalState.CONSUMED


def test_concurrent_consume_action_is_single_use(clock):
    import threading

    manager = InMemoryApprovalManager(clock)
    request = _request(clock)
    manager.request(request)
    record = manager.record_decision(
        request.request_id, ApprovalDecision.APPROVED, "human", "ok"
    )
    successes = []
    errors = []
    barrier = threading.Barrier(8)

    def attempt():
        barrier.wait()
        decision = manager.consume_action(
            record.approval_id,
            request.action,
            request.target,
            OperatingMode.WORKSPACE_WRITE,
            clock.now(),
        )
        if decision.allowed:
            successes.append(decision)
        else:
            errors.append(decision)

    threads = [threading.Thread(target=attempt) for _ in range(8)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    assert len(successes) == 1
    assert len(errors) == 7
    assert all(d.reason_code is PolicyReasonCode.APPROVAL_CONSUMED for d in errors)
    assert manager.get(record.approval_id).state is ApprovalState.CONSUMED
