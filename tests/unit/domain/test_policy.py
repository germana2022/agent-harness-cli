import datetime

import pytest

from agent_harness.domain import (
    ActionCategory,
    AllowlistEngine,
    AllowlistMatch,
    AllowlistRule,
    ApprovalDecision,
    ApprovalRequest,
    ApprovalState,
    Capability,
    DefaultPolicyEngine,
    InMemoryApprovalManager,
    MatchMode,
    OperatingMode,
    PolicyReasonCode,
    PolicyRequest,
    RuleKind,
    action_scope,
)
from agent_harness.domain.policy import _evaluate_approval_record

from conftest import make_action, make_target

_seq = [0]


def _approve(
    manager,
    clock,
    action,
    target,
    *,
    mode=OperatingMode.DELIVERY,
    scope=None,
    expires_at=None,
    request_id=None,
):
    _seq[0] += 1
    rid = request_id or f"req-{_seq[0]}"
    request = ApprovalRequest(
        request_id=rid,
        action=action,
        target=target,
        required_mode=mode,
        current_mode=mode,
        scope=scope or action_scope(action),
        requesting_component="tests",
        rationale="test approval",
        created_at=clock.now(),
        expires_at=expires_at,
    )
    manager.request(request)
    return manager.record_decision(
        rid, ApprovalDecision.APPROVED, approver="human", reason="ok"
    )


def _local_action():
    return make_action(Capability.LOCAL_WORKSPACE_WRITE)


def _external_action():
    return make_action(Capability.EXTERNAL_PUSH)


def _engine(clock, *, allowlist=None, authority=None, **kwargs):
    return DefaultPolicyEngine(
        clock=clock,
        allowlist=allowlist or AllowlistEngine(),
        approval_authority=authority,
        **kwargs,
    )


def _req(engine, mode, action, **kwargs):
    kwargs.setdefault("target", action.target)
    return engine.decide(PolicyRequest(mode=mode, action=action, **kwargs))


def test_read_allowed_in_read_only(engine, clock):
    action = make_action(Capability.ALLOWED_FILE_READ)
    decision = _req(engine, OperatingMode.READ_ONLY, action)
    assert decision.allowed is True
    assert decision.reason_code is PolicyReasonCode.ALLOWED
    assert decision.approval_required is False
    assert "mode:read_only" in decision.evidence


def test_missing_target_denies(engine, clock):
    action = make_action(Capability.EXACT_SEARCH)
    decision = _req(engine, OperatingMode.READ_ONLY, action, target=None)
    assert decision.allowed is False
    assert decision.reason_code is PolicyReasonCode.TARGET_MISSING


def test_unknown_action_denies(engine, clock):
    reduced = {Capability.REPOSITORY_METADATA_READ: ActionCategory.READ}
    limited = _engine(clock, capability_map=reduced)
    action = make_action(Capability.EXACT_SEARCH)
    decision = limited.decide(
        PolicyRequest(mode=OperatingMode.READ_ONLY, action=action, target=action.target)
    )
    assert decision.allowed is False
    assert decision.reason_code is PolicyReasonCode.ACTION_UNKNOWN


def test_hard_prohibited_capability_denies(engine, clock):
    hard = _engine(
        clock, hard_prohibited_capabilities=frozenset({Capability.EXACT_SEARCH})
    )
    action = make_action(Capability.EXACT_SEARCH)
    decision = hard.decide(
        PolicyRequest(mode=OperatingMode.READ_ONLY, action=action, target=action.target)
    )
    assert decision.allowed is False
    assert decision.reason_code is PolicyReasonCode.HARD_PROHIBITION


def test_hard_prohibited_category_denies(engine, clock):
    hard = _engine(
        clock, hard_prohibited_categories=frozenset({ActionCategory.EXECUTION})
    )
    action = make_action(Capability.COMMAND_EXECUTION)
    decision = hard.decide(
        PolicyRequest(
            mode=OperatingMode.WORKSPACE_WRITE,
            action=action,
            target=action.target,
        )
    )
    assert decision.allowed is False
    assert decision.reason_code is PolicyReasonCode.HARD_PROHIBITION


def test_local_write_denied_in_read_only(engine, clock):
    decision = _req(engine, OperatingMode.READ_ONLY, _local_action())
    assert decision.allowed is False
    assert decision.reason_code is PolicyReasonCode.MODE_PROHIBITS_ACTION


def test_external_denied_in_workspace_write(engine, clock):
    decision = _req(engine, OperatingMode.WORKSPACE_WRITE, _external_action())
    assert decision.allowed is False
    assert decision.reason_code is PolicyReasonCode.MODE_PROHIBITS_ACTION


def test_local_write_denied_without_allowlist(engine, clock):
    decision = _req(engine, OperatingMode.WORKSPACE_WRITE, _local_action())
    assert decision.allowed is False
    assert decision.reason_code is PolicyReasonCode.TARGET_NOT_ALLOWLISTED


def test_local_write_denied_by_explicit_deny_rule(clock):
    rules = [
        AllowlistRule(
            rule_id="deny-local",
            kind=RuleKind.DENY,
            capability=Capability.LOCAL_WORKSPACE_WRITE,
            target_pattern="repo:main:",
            match_mode=MatchMode.PREFIX,
        )
    ]
    engine = _engine(clock, allowlist=AllowlistEngine(rules))
    match = AllowlistEngine(rules).match(
        Capability.LOCAL_WORKSPACE_WRITE, "repo:main:src/"
    )
    action = _local_action()
    decision = engine.decide(
        PolicyRequest(
            mode=OperatingMode.WORKSPACE_WRITE,
            action=action,
            target=action.target,
            allowlist_result=match,
        )
    )
    assert decision.allowed is False
    assert decision.reason_code is PolicyReasonCode.TARGET_NOT_ALLOWLISTED


def test_local_write_denied_on_ambiguous_allowlist(clock):
    rules = [
        AllowlistRule(
            rule_id="allow-a",
            kind=RuleKind.ALLOW,
            capability=Capability.LOCAL_WORKSPACE_WRITE,
            target_pattern="repo:main:",
            match_mode=MatchMode.PREFIX,
            priority=5,
        ),
        AllowlistRule(
            rule_id="allow-b",
            kind=RuleKind.ALLOW,
            capability=Capability.LOCAL_WORKSPACE_WRITE,
            target_pattern="repo:main:src",
            match_mode=MatchMode.PREFIX,
            priority=5,
        ),
    ]
    allowlist = AllowlistEngine(rules)
    engine = _engine(clock, allowlist=allowlist)
    match = allowlist.match(Capability.LOCAL_WORKSPACE_WRITE, "repo:main:src/")
    assert match is not None and match.ambiguous is True
    action = _local_action()
    decision = engine.decide(
        PolicyRequest(
            mode=OperatingMode.WORKSPACE_WRITE,
            action=action,
            target=action.target,
            allowlist_result=match,
        )
    )
    assert decision.allowed is False
    assert decision.reason_code is PolicyReasonCode.POLICY_CONFIGURATION_ERROR


def test_workspace_write_local_allowed_with_allowlist(engine, clock):
    action = _local_action()
    match = AllowlistMatch(
        rule_id="allow-local",
        kind=RuleKind.ALLOW,
        evidence="allow rule allow-local matched",
    )
    decision = engine.decide(
        PolicyRequest(
            mode=OperatingMode.WORKSPACE_WRITE,
            action=action,
            target=action.target,
            allowlist_result=match,
        )
    )
    assert decision.allowed is True
    assert decision.reason_code is PolicyReasonCode.ALLOWED
    assert "allowlist:allow-local" in decision.evidence


def test_external_requires_approval_in_delivery(engine, clock):
    action = _external_action()
    match = AllowlistMatch(
        rule_id="allow-push", kind=RuleKind.ALLOW, evidence="matched"
    )
    decision = engine.decide(
        PolicyRequest(
            mode=OperatingMode.DELIVERY,
            action=action,
            target=action.target,
            allowlist_result=match,
        )
    )
    assert decision.allowed is False
    assert decision.reason_code is PolicyReasonCode.APPROVAL_REQUIRED
    assert decision.approval_required is True


def test_external_allowed_with_valid_approval(clock):
    manager = InMemoryApprovalManager(clock)
    engine = _engine(clock, authority=manager)
    action = _external_action()
    record = _approve(manager, clock, action, action.target)
    match = AllowlistMatch(
        rule_id="allow-push", kind=RuleKind.ALLOW, evidence="matched"
    )
    decision = engine.decide(
        PolicyRequest(
            mode=OperatingMode.DELIVERY,
            action=action,
            target=action.target,
            allowlist_result=match,
            approval=record.approval_id,
        )
    )
    assert decision.allowed is True
    assert decision.reason_code is PolicyReasonCode.ALLOWED
    assert decision.approval_required is True


def test_forged_approval_record_cannot_authorize(clock):
    """A directly constructed, manager-less ApprovalRecord cannot authorize."""
    manager = InMemoryApprovalManager(clock)
    engine = _engine(clock, authority=manager)
    action = _external_action()
    match = AllowlistMatch(rule_id="a", kind=RuleKind.ALLOW, evidence="m")
    # Passing a raw record is rejected by the request API.
    with pytest.raises(ValueError):
        PolicyRequest(
            mode=OperatingMode.DELIVERY,
            action=action,
            target=action.target,
            allowlist_result=match,
            approval=_evaluate_approval_record,  # type: ignore[arg-type]
        )
    # An identifier absent from the manager denies.
    decision = engine.decide(
        PolicyRequest(
            mode=OperatingMode.DELIVERY,
            action=action,
            target=action.target,
            allowlist_result=match,
            approval="appr-does-not-exist",
        )
    )
    assert decision.allowed is False
    assert decision.reason_code is PolicyReasonCode.APPROVAL_MISSING


def test_stale_approval_copy_denies_after_consumption(clock):
    manager = InMemoryApprovalManager(clock)
    engine = _engine(clock, authority=manager)
    action = _external_action()
    record = _approve(manager, clock, action, action.target)
    match = AllowlistMatch(rule_id="a", kind=RuleKind.ALLOW, evidence="m")
    manager.consume(record.approval_id)
    decision = engine.decide(
        PolicyRequest(
            mode=OperatingMode.DELIVERY,
            action=action,
            target=action.target,
            allowlist_result=match,
            approval=record.approval_id,
        )
    )
    assert decision.allowed is False
    assert decision.reason_code is PolicyReasonCode.APPROVAL_CONSUMED


def test_stale_approval_copy_denies_after_revocation(clock):
    manager = InMemoryApprovalManager(clock)
    engine = _engine(clock, authority=manager)
    action = _external_action()
    record = _approve(manager, clock, action, action.target)
    match = AllowlistMatch(rule_id="a", kind=RuleKind.ALLOW, evidence="m")
    manager.revoke(record.approval_id)
    decision = engine.decide(
        PolicyRequest(
            mode=OperatingMode.DELIVERY,
            action=action,
            target=action.target,
            allowlist_result=match,
            approval=record.approval_id,
        )
    )
    assert decision.allowed is False
    assert decision.reason_code is PolicyReasonCode.APPROVAL_REVOKED


def test_stale_approval_copy_denies_after_expiration(clock):
    manager = InMemoryApprovalManager(clock)
    engine = _engine(clock, authority=manager)
    action = _external_action()
    record = _approve(
        manager,
        clock,
        action,
        action.target,
        expires_at=clock.now() + datetime.timedelta(minutes=10),
    )
    match = AllowlistMatch(rule_id="a", kind=RuleKind.ALLOW, evidence="m")
    clock.advance(datetime.timedelta(minutes=11))
    decision = engine.decide(
        PolicyRequest(
            mode=OperatingMode.DELIVERY,
            action=action,
            target=action.target,
            allowlist_result=match,
            approval=record.approval_id,
        )
    )
    assert decision.allowed is False
    assert decision.reason_code is PolicyReasonCode.APPROVAL_EXPIRED


def test_transition_approval_cannot_authorize_action(clock):
    from agent_harness.domain import transition_scope

    manager = InMemoryApprovalManager(clock)
    engine = _engine(clock, authority=manager)
    action = _external_action()
    record = _approve(
        manager,
        clock,
        action,
        action.target,
        scope=transition_scope(OperatingMode.READ_ONLY, OperatingMode.WORKSPACE_WRITE),
    )
    match = AllowlistMatch(rule_id="a", kind=RuleKind.ALLOW, evidence="m")
    decision = engine.decide(
        PolicyRequest(
            mode=OperatingMode.DELIVERY,
            action=action,
            target=action.target,
            allowlist_result=match,
            approval=record.approval_id,
        )
    )
    assert decision.allowed is False
    assert decision.reason_code is PolicyReasonCode.APPROVAL_SCOPE_MISMATCH


def test_wrong_action_scope_denies(clock):
    manager = InMemoryApprovalManager(clock)
    engine = _engine(clock, authority=manager)
    action = _external_action()
    record = _approve(manager, clock, action, action.target, scope="action:deployment")
    match = AllowlistMatch(rule_id="a", kind=RuleKind.ALLOW, evidence="m")
    decision = engine.decide(
        PolicyRequest(
            mode=OperatingMode.DELIVERY,
            action=action,
            target=action.target,
            allowlist_result=match,
            approval=record.approval_id,
        )
    )
    assert decision.allowed is False
    assert decision.reason_code is PolicyReasonCode.APPROVAL_SCOPE_MISMATCH


def test_approval_without_authority_fails_closed(clock):
    engine = _engine(clock)  # no authority
    action = _external_action()
    match = AllowlistMatch(rule_id="a", kind=RuleKind.ALLOW, evidence="m")
    decision = engine.decide(
        PolicyRequest(
            mode=OperatingMode.DELIVERY,
            action=action,
            target=action.target,
            allowlist_result=match,
            approval="appr-any",
        )
    )
    assert decision.allowed is False
    assert decision.reason_code is PolicyReasonCode.APPROVAL_MISSING


def test_approval_denied_decision_denies(clock):
    manager = InMemoryApprovalManager(clock)
    engine = _engine(clock, authority=manager)
    action = _external_action()
    request = ApprovalRequest(
        request_id="denied-req",
        action=action,
        target=action.target,
        required_mode=OperatingMode.DELIVERY,
        current_mode=OperatingMode.DELIVERY,
        scope=action_scope(action),
        requesting_component="tests",
        rationale="test",
        created_at=clock.now(),
    )
    manager.request(request)
    record = manager.record_decision(
        "denied-req", ApprovalDecision.DENIED, "human", "no"
    )
    match = AllowlistMatch(rule_id="a", kind=RuleKind.ALLOW, evidence="m")
    decision = engine.decide(
        PolicyRequest(
            mode=OperatingMode.DELIVERY,
            action=action,
            target=action.target,
            allowlist_result=match,
            approval=record.approval_id,
        )
    )
    assert decision.allowed is False
    assert decision.reason_code is PolicyReasonCode.APPROVAL_DENIED


def test_approval_mode_mismatch_denies(clock):
    manager = InMemoryApprovalManager(clock)
    engine = _engine(clock, authority=manager)
    action = _external_action()
    record = _approve(manager, clock, action, action.target, mode=OperatingMode.WORKSPACE_WRITE)
    match = AllowlistMatch(rule_id="a", kind=RuleKind.ALLOW, evidence="m")
    decision = engine.decide(
        PolicyRequest(
            mode=OperatingMode.DELIVERY,
            action=action,
            target=action.target,
            allowlist_result=match,
            approval=record.approval_id,
        )
    )
    assert decision.allowed is False
    assert decision.reason_code is PolicyReasonCode.APPROVAL_SCOPE_MISMATCH


def test_approval_target_mismatch_denies(clock):
    manager = InMemoryApprovalManager(clock)
    engine = _engine(clock, authority=manager)
    action = _external_action()
    record = _approve(manager, clock, action, action.target)
    other_target = make_target(ref="repo:main:other")
    match = AllowlistMatch(rule_id="a", kind=RuleKind.ALLOW, evidence="m")
    decision = engine.decide(
        PolicyRequest(
            mode=OperatingMode.DELIVERY,
            action=action,
            target=other_target,
            allowlist_result=match,
            approval=record.approval_id,
        )
    )
    assert decision.allowed is False
    assert decision.reason_code is PolicyReasonCode.APPROVAL_SCOPE_MISMATCH


def test_delivery_local_write_requires_approval(engine, clock):
    action = _local_action()
    match = AllowlistMatch(
        rule_id="allow-local", kind=RuleKind.ALLOW, evidence="matched"
    )
    decision = engine.decide(
        PolicyRequest(
            mode=OperatingMode.DELIVERY,
            action=action,
            target=action.target,
            allowlist_result=match,
        )
    )
    assert decision.allowed is False
    assert decision.reason_code is PolicyReasonCode.APPROVAL_REQUIRED


def test_configured_approval_category_requires_approval(clock):
    engine = _engine(
        clock, approval_required_categories=frozenset({ActionCategory.LOCAL_WRITE})
    )
    action = _local_action()
    match = AllowlistMatch(rule_id="a", kind=RuleKind.ALLOW, evidence="m")
    decision = engine.decide(
        PolicyRequest(
            mode=OperatingMode.WORKSPACE_WRITE,
            action=action,
            target=action.target,
            allowlist_result=match,
        )
    )
    assert decision.allowed is False
    assert decision.reason_code is PolicyReasonCode.APPROVAL_REQUIRED


def test_read_ignores_allowlist_and_approval(engine, clock):
    action = make_action(Capability.ALLOWED_FILE_READ)
    decision = engine.decide(
        PolicyRequest(
            mode=OperatingMode.READ_ONLY,
            action=action,
            target=action.target,
            allowlist_result=None,
        )
    )
    assert decision.allowed is True


def test_decisions_are_deterministic_and_sanitized(engine, clock):
    action = _local_action()
    decision = _req(engine, OperatingMode.WORKSPACE_WRITE, action)
    assert decision.message == "target not allowlisted"
    assert "repo" not in decision.message
    decision2 = _req(engine, OperatingMode.WORKSPACE_WRITE, action)
    assert decision == decision2


def test_policy_request_validation():
    action = make_action()
    with pytest.raises(ValueError):
        PolicyRequest(mode="bad", action=action)
    with pytest.raises(ValueError):
        PolicyRequest(mode=OperatingMode.READ_ONLY, action=action, target="bad")
    with pytest.raises(ValueError):
        PolicyRequest(mode=OperatingMode.READ_ONLY, action="bad")
    with pytest.raises(ValueError):
        PolicyRequest(
            mode=OperatingMode.READ_ONLY,
            action=action,
            target=action.target,
            allowlist_result="bad",
        )
    with pytest.raises(ValueError):
        PolicyRequest(
            mode=OperatingMode.READ_ONLY,
            action=action,
            target=action.target,
            approval="   ",
        )


def test_policy_decision_defaults_message():
    from agent_harness.domain import PolicyDecision

    decision = PolicyDecision(
        allowed=True,
        reason_code=PolicyReasonCode.ALLOWED,
        message="",
        approval_required=False,
    )
    assert decision.message == "allowed"


def test_policy_decision_rejects_bad_reason_code():
    from agent_harness.domain import PolicyDecision

    with pytest.raises(ValueError):
        PolicyDecision(
            allowed=True,
            reason_code="bad",
            message="x",
            approval_required=False,
        )


def test_internal_evaluator_scope_branch_pending():
    """Internal helper branch: a PENDING record denies (defensive path)."""
    from agent_harness.domain import ApprovalRecord, ApprovalDecision

    action = _external_action()
    record = ApprovalRecord(
        approval_id="pending",
        request_id="r",
        decision=ApprovalDecision.APPROVED,
        scope=action_scope(action),
        action=action,
        target=action.target,
        required_mode=OperatingMode.DELIVERY,
        approver="human",
        decided_at=clock_now(),
        expires_at=None,
        state=ApprovalState.PENDING,
    )
    verdict = _evaluate_approval_record(
        record, action, action.target, action_scope(action), clock_now()
    )
    assert verdict.allowed is False
    assert verdict.reason_code is PolicyReasonCode.APPROVAL_PENDING


def test_internal_evaluator_time_based_expiry():
    """Internal helper branch: APPROVED state but time past expiry denies."""
    from agent_harness.domain import ApprovalRecord, ApprovalDecision

    action = _external_action()
    record = ApprovalRecord(
        approval_id="exp",
        request_id="r",
        decision=ApprovalDecision.APPROVED,
        scope=action_scope(action),
        action=action,
        target=action.target,
        required_mode=OperatingMode.DELIVERY,
        approver="human",
        decided_at=clock_now(),
        expires_at=clock_now() + datetime.timedelta(minutes=10),
        state=ApprovalState.APPROVED,
    )
    verdict = _evaluate_approval_record(
        record,
        action,
        action.target,
        action_scope(action),
        clock_now() + datetime.timedelta(minutes=11),
    )
    assert verdict.allowed is False
    assert verdict.reason_code is PolicyReasonCode.APPROVAL_EXPIRED


def clock_now():
    import datetime as _dt

    return _dt.datetime(2026, 1, 1, tzinfo=_dt.timezone.utc)
