"""Mode-transition state machine.

Escalations to a more permissive mode require a valid single-use approval bound
to that exact transition. Returns to a more restrictive mode never do.

Approvals are resolved through the injected :class:`ApprovalAuthority`; a raw
caller-supplied record is never authoritative.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from .modes import OperatingMode
from .policy import (
    REASON_MESSAGES,
    ApprovalAuthority,
    PolicyReasonCode,
)

# Maps (from_mode, to_mode) -> approval required for the transition.
_TRANSITION_SPECS: dict[tuple[OperatingMode, OperatingMode], bool] = {
    (OperatingMode.READ_ONLY, OperatingMode.WORKSPACE_WRITE): True,
    (OperatingMode.READ_ONLY, OperatingMode.DELIVERY): True,
    (OperatingMode.WORKSPACE_WRITE, OperatingMode.DELIVERY): True,
    (OperatingMode.WORKSPACE_WRITE, OperatingMode.READ_ONLY): False,
    (OperatingMode.DELIVERY, OperatingMode.WORKSPACE_WRITE): False,
    (OperatingMode.DELIVERY, OperatingMode.READ_ONLY): False,
}


@dataclass(frozen=True)
class ModeTransitionRequest:
    """A request to change the operating mode."""

    from_mode: OperatingMode
    to_mode: OperatingMode


@dataclass(frozen=True)
class TransitionDecision:
    """A deterministic, evidence-backed mode transition decision."""

    allowed: bool
    from_mode: OperatingMode
    to_mode: OperatingMode
    reason_code: PolicyReasonCode
    message: str
    approval_required: bool
    timestamp: datetime
    approval_id: str | None = None
    evidence: tuple[str, ...] = ()


def transition_scope(from_mode: OperatingMode, to_mode: OperatingMode) -> str:
    """Canonical scope binding an escalation approval to one transition."""
    return f"mode_transition:{from_mode.value}:{to_mode.value}"


def evaluate_transition(
    request: ModeTransitionRequest,
    authority: ApprovalAuthority | None,
    approval_id: str | None,
    at_time: datetime,
) -> TransitionDecision:
    """Evaluate a mode transition request with default-deny behavior.

    Escalations resolve ``approval_id`` through the authoritative
    ``authority``; without an authority an escalation fails closed.
    """
    requires_approval = _TRANSITION_SPECS.get((request.from_mode, request.to_mode))
    if requires_approval is None:
        return _denied(
            request,
            PolicyReasonCode.UNSUPPORTED_TRANSITION,
            approval_required=False,
            at_time=at_time,
        )
    if not requires_approval:
        return _allowed(request, approval_required=False, at_time=at_time)
    if approval_id is None:
        return _denied(
            request,
            PolicyReasonCode.APPROVAL_REQUIRED,
            approval_required=True,
            at_time=at_time,
        )
    if authority is None:
        return _denied(
            request,
            PolicyReasonCode.APPROVAL_MISSING,
            approval_required=True,
            at_time=at_time,
        )
    verdict = authority.authorize_transition(
        approval_id, request.from_mode, request.to_mode, at_time
    )
    return TransitionDecision(
        allowed=verdict.allowed,
        from_mode=request.from_mode,
        to_mode=request.to_mode,
        reason_code=verdict.reason_code,
        message=verdict.message,
        approval_required=True,
        timestamp=at_time,
        approval_id=approval_id,
        evidence=verdict.evidence,
    )


def _denied(
    request: ModeTransitionRequest,
    reason: PolicyReasonCode,
    *,
    approval_required: bool,
    at_time: datetime,
) -> TransitionDecision:
    return TransitionDecision(
        allowed=False,
        from_mode=request.from_mode,
        to_mode=request.to_mode,
        reason_code=reason,
        message=REASON_MESSAGES[reason],
        approval_required=approval_required,
        timestamp=at_time,
    )


def _allowed(
    request: ModeTransitionRequest,
    *,
    approval_required: bool,
    at_time: datetime,
) -> TransitionDecision:
    return TransitionDecision(
        allowed=True,
        from_mode=request.from_mode,
        to_mode=request.to_mode,
        reason_code=PolicyReasonCode.ALLOWED,
        message=REASON_MESSAGES[PolicyReasonCode.ALLOWED],
        approval_required=approval_required,
        timestamp=at_time,
    )
