"""Policy engine contract and deterministic default-deny evaluation.

Ordinary denials are returned as :class:`PolicyDecision` objects; exceptions
are never used for policy denial.

Approval-required authorization is never granted from a caller-supplied
``ApprovalRecord``. The engine resolves approval identifiers through an
injected authoritative :class:`ApprovalAuthority` so that registration,
lifecycle state, expiration, revocation, and binding are checked against the
manager's stored record at decision time.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Protocol

from .actions import CAPABILITY_CATEGORY, ActionCategory, ActionName, TargetResource
from .allowlist import AllowlistEngine, AllowlistMatch, RuleKind
from .approvals import ApprovalRecord, ApprovalState
from .clock import Clock
from .modes import OperatingMode, mode_allows_category, mode_requires_approval


class PolicyReasonCode(Enum):
    """Stable machine-readable policy reason codes."""

    ALLOWED = "allowed"
    MODE_PROHIBITS_ACTION = "mode_prohibits_action"
    ACTION_UNKNOWN = "action_unknown"
    TARGET_MISSING = "target_missing"
    TARGET_NOT_ALLOWLISTED = "target_not_allowlisted"
    HARD_PROHIBITION = "hard_prohibition"
    APPROVAL_REQUIRED = "approval_required"
    APPROVAL_MISSING = "approval_missing"
    APPROVAL_PENDING = "approval_pending"
    APPROVAL_DENIED = "approval_denied"
    APPROVAL_EXPIRED = "approval_expired"
    APPROVAL_REVOKED = "approval_revoked"
    APPROVAL_CONSUMED = "approval_consumed"
    APPROVAL_SCOPE_MISMATCH = "approval_scope_mismatch"
    UNSUPPORTED_TRANSITION = "unsupported_transition"
    INVALID_POLICY_REQUEST = "invalid_policy_request"
    POLICY_CONFIGURATION_ERROR = "policy_configuration_error"


REASON_MESSAGES: dict[PolicyReasonCode, str] = {
    PolicyReasonCode.ALLOWED: "allowed",
    PolicyReasonCode.MODE_PROHIBITS_ACTION: "action not permitted in current mode",
    PolicyReasonCode.ACTION_UNKNOWN: "unknown action",
    PolicyReasonCode.TARGET_MISSING: "missing target",
    PolicyReasonCode.TARGET_NOT_ALLOWLISTED: "target not allowlisted",
    PolicyReasonCode.HARD_PROHIBITION: "action is hard prohibited",
    PolicyReasonCode.APPROVAL_REQUIRED: "approval required",
    PolicyReasonCode.APPROVAL_MISSING: "approval not found",
    PolicyReasonCode.APPROVAL_PENDING: "approval is pending",
    PolicyReasonCode.APPROVAL_DENIED: "approval was denied",
    PolicyReasonCode.APPROVAL_EXPIRED: "approval expired",
    PolicyReasonCode.APPROVAL_REVOKED: "approval revoked",
    PolicyReasonCode.APPROVAL_CONSUMED: "approval already consumed",
    PolicyReasonCode.APPROVAL_SCOPE_MISMATCH: "approval scope does not match",
    PolicyReasonCode.UNSUPPORTED_TRANSITION: "unsupported mode transition",
    PolicyReasonCode.INVALID_POLICY_REQUEST: "invalid policy request",
    PolicyReasonCode.POLICY_CONFIGURATION_ERROR: "ambiguous policy configuration",
}


@dataclass(frozen=True)
class PolicyDecision:
    """A deterministic, evidence-backed policy decision."""

    allowed: bool
    reason_code: PolicyReasonCode
    message: str
    approval_required: bool
    evidence: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.reason_code, PolicyReasonCode):
            raise ValueError("reason_code must be a PolicyReasonCode")
        if not self.message:
            object.__setattr__(self, "message", REASON_MESSAGES[self.reason_code])


@dataclass(frozen=True)
class PolicyRequest:
    """Input to a policy decision.

    ``approval`` carries an approval identifier resolved by the injected
    authority; a raw approval record is never authoritative.
    """

    mode: OperatingMode
    action: ActionName
    target: TargetResource | None = None
    allowlist_result: AllowlistMatch | None = None
    approval: str | None = None
    external: bool = False
    destructive: bool = False
    context: tuple[tuple[str, str], ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.mode, OperatingMode):
            raise ValueError("mode must be an OperatingMode")
        if not isinstance(self.action, ActionName):
            raise ValueError("action must be an ActionName")
        if self.target is not None and not isinstance(self.target, TargetResource):
            raise ValueError("target must be a TargetResource")
        if self.allowlist_result is not None and not isinstance(
            self.allowlist_result, AllowlistMatch
        ):
            raise ValueError("allowlist_result must be an AllowlistMatch")
        if self.approval is not None and (
            not isinstance(self.approval, str) or not self.approval.strip()
        ):
            raise ValueError("approval must be a nonempty approval identifier")
        if not isinstance(self.context, tuple):
            raise ValueError("context must be a tuple")


class PolicyEngine(Protocol):
    """Protocol for policy evaluation."""

    def decide(self, request: PolicyRequest) -> PolicyDecision:
        """Return a deterministic decision for ``request``."""
        ...


class ApprovalAuthority(Protocol):
    """Authoritative approval validation backed by the approval manager.

    Implementations resolve the approval identifier against stored state and
    validate lifecycle, expiration, binding, and the canonical scope for the
    requested purpose. Caller-supplied approval records are never consulted.
    """

    def authorize_action(
        self,
        approval_id: str,
        action: ActionName,
        target: TargetResource,
        mode: OperatingMode,
        at_time: datetime,
    ) -> PolicyDecision:
        """Validate an approval as authorization for ``action`` at ``mode``."""
        ...

    def authorize_transition(
        self,
        approval_id: str,
        from_mode: OperatingMode,
        to_mode: OperatingMode,
        at_time: datetime,
    ) -> PolicyDecision:
        """Validate an approval as authorization for a mode escalation."""
        ...


def action_scope(action: ActionName) -> str:
    """Canonical approval scope binding an approval to one action capability."""
    return f"action:{action.capability.value}"


def _decision(
    allowed: bool,
    reason: PolicyReasonCode,
    *,
    approval_required: bool,
    message: str | None = None,
    evidence: tuple[str, ...] = (),
) -> PolicyDecision:
    return PolicyDecision(
        allowed=allowed,
        reason_code=reason,
        message=message or REASON_MESSAGES[reason],
        approval_required=approval_required,
        evidence=evidence,
    )


def _state_and_expiration_reason(
    record: ApprovalRecord, at_time: datetime
) -> PolicyReasonCode | None:
    if record.state is ApprovalState.PENDING:
        return PolicyReasonCode.APPROVAL_PENDING
    if record.state is ApprovalState.DENIED:
        return PolicyReasonCode.APPROVAL_DENIED
    if record.state is ApprovalState.REVOKED:
        return PolicyReasonCode.APPROVAL_REVOKED
    if record.state is ApprovalState.CONSUMED:
        return PolicyReasonCode.APPROVAL_CONSUMED
    if record.state is ApprovalState.EXPIRED:
        return PolicyReasonCode.APPROVAL_EXPIRED
    if record.expires_at is not None and record.expires_at <= at_time:
        return PolicyReasonCode.APPROVAL_EXPIRED
    return None


def _evaluate_approval_record(
    record: ApprovalRecord,
    action: ActionName,
    target: TargetResource,
    expected_scope: str,
    at_time: datetime,
) -> PolicyDecision:
    """Validate an authoritative record against action, target, and scope.

    This is an internal helper used only by the approval manager; it is never
    the final authorization entry point.
    """
    reason = _state_and_expiration_reason(record, at_time)
    if reason is not None:
        return _decision(False, reason, approval_required=True)
    if (
        record.action != action
        or record.target != target
        or record.scope != expected_scope
    ):
        return _decision(
            False,
            PolicyReasonCode.APPROVAL_SCOPE_MISMATCH,
            approval_required=True,
        )
    return _decision(
        True,
        PolicyReasonCode.ALLOWED,
        approval_required=True,
        evidence=(record.approval_id,),
    )


class DefaultPolicyEngine:
    """Deterministic policy engine implementing the approved evaluation order.

    Evaluation precedence:

    ``hard prohibition → mode capability → allowlist → approval requirement
    → approval validity → final decision``

    Approval validity is resolved through the injected
    :class:`ApprovalAuthority`; without an authority, approval-required
    actions fail closed.
    """

    def __init__(
        self,
        clock: Clock,
        allowlist: AllowlistEngine,
        *,
        approval_authority: ApprovalAuthority | None = None,
        capability_map: dict | None = None,
        approval_required_categories: frozenset[ActionCategory] | None = None,
        hard_prohibited_capabilities: frozenset | None = None,
        hard_prohibited_categories: frozenset[ActionCategory] | None = None,
    ) -> None:
        self._clock = clock
        self._allowlist = allowlist
        self._approval_authority = approval_authority
        self._capability_map = capability_map or CAPABILITY_CATEGORY
        self._approval_required_categories = (
            approval_required_categories if approval_required_categories is not None else frozenset()
        )
        self._hard_capabilities = hard_prohibited_capabilities or frozenset()
        self._hard_categories = hard_prohibited_categories or frozenset()

    def decide(self, request: PolicyRequest) -> PolicyDecision:
        if request.target is None:
            return _decision(False, PolicyReasonCode.TARGET_MISSING, approval_required=False)
        capability = request.action.capability
        if capability not in self._capability_map:
            return _decision(False, PolicyReasonCode.ACTION_UNKNOWN, approval_required=False)
        category = self._capability_map[capability]
        if capability in self._hard_capabilities or category in self._hard_categories:
            return _decision(False, PolicyReasonCode.HARD_PROHIBITION, approval_required=False)
        if not mode_allows_category(request.mode, category):
            return _decision(
                False,
                PolicyReasonCode.MODE_PROHIBITS_ACTION,
                approval_required=False,
            )
        if category is not ActionCategory.READ:
            if request.allowlist_result is None:
                return _decision(
                    False,
                    PolicyReasonCode.TARGET_NOT_ALLOWLISTED,
                    approval_required=False,
                )
            if request.allowlist_result.ambiguous:
                return _decision(
                    False,
                    PolicyReasonCode.POLICY_CONFIGURATION_ERROR,
                    approval_required=False,
                )
            if request.allowlist_result.kind is not RuleKind.ALLOW:
                return _decision(
                    False,
                    PolicyReasonCode.TARGET_NOT_ALLOWLISTED,
                    approval_required=False,
                )
        approval_required = mode_requires_approval(request.mode, category) or (
            category in self._approval_required_categories
        )
        if approval_required:
            if request.approval is None:
                return _decision(
                    False,
                    PolicyReasonCode.APPROVAL_REQUIRED,
                    approval_required=True,
                )
            if self._approval_authority is None:
                return _decision(
                    False,
                    PolicyReasonCode.APPROVAL_MISSING,
                    approval_required=True,
                )
            verdict = self._approval_authority.authorize_action(
                request.approval,
                request.action,
                request.target,
                request.mode,
                self._clock.now(),
            )
            if not verdict.allowed:
                return _decision(
                    False,
                    verdict.reason_code,
                    approval_required=True,
                )
            return _decision(
                True,
                PolicyReasonCode.ALLOWED,
                approval_required=True,
                evidence=verdict.evidence,
            )
        evidence = (f"mode:{request.mode.value}", f"category:{category.value}")
        if request.allowlist_result is not None:
            evidence = evidence + (f"allowlist:{request.allowlist_result.rule_id}",)
        return _decision(
            True,
            PolicyReasonCode.ALLOWED,
            approval_required=False,
            evidence=evidence,
        )
