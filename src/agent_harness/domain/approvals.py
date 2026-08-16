"""Approval request and record models.

Approval records are immutable and carry only metadata. They never contain
credentials, tokens, passwords, or raw sensitive values. Approver identity is
a modeled reference and is not treated as authenticated identity.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any

from .actions import ActionName, TargetResource
from .errors import InvalidDomainValue, validate_identifier, validate_utc
from .modes import OperatingMode


class ApprovalDecision(Enum):
    APPROVED = "approved"
    DENIED = "denied"


class ApprovalState(Enum):
    PENDING = "pending"
    APPROVED = "approved"
    DENIED = "denied"
    EXPIRED = "expired"
    REVOKED = "revoked"
    CONSUMED = "consumed"


TERMINAL_STATES = frozenset(
    {
        ApprovalState.DENIED,
        ApprovalState.EXPIRED,
        ApprovalState.REVOKED,
        ApprovalState.CONSUMED,
    }
)


@dataclass(frozen=True)
class ApprovalRequest:
    """An immutable request for human approval of a specific action."""

    request_id: str
    action: ActionName
    target: TargetResource
    required_mode: OperatingMode
    current_mode: OperatingMode
    scope: str
    requesting_component: str
    rationale: str
    created_at: datetime
    expires_at: datetime | None = None
    evidence_refs: tuple[str, ...] = ()
    is_external: bool = False
    is_destructive: bool = False

    def __post_init__(self) -> None:
        object.__setattr__(self, "request_id", validate_identifier(self.request_id, "request_id"))
        object.__setattr__(self, "scope", validate_identifier(self.scope, "scope"))
        object.__setattr__(
            self,
            "requesting_component",
            validate_identifier(self.requesting_component, "requesting_component"),
        )
        object.__setattr__(self, "rationale", validate_identifier(self.rationale, "rationale"))
        if not isinstance(self.action, ActionName):
            raise InvalidDomainValue("action must be an ActionName")
        if not isinstance(self.target, TargetResource):
            raise InvalidDomainValue("target must be a TargetResource")
        if not isinstance(self.required_mode, OperatingMode):
            raise InvalidDomainValue("required_mode must be an OperatingMode")
        if not isinstance(self.current_mode, OperatingMode):
            raise InvalidDomainValue("current_mode must be an OperatingMode")
        object.__setattr__(self, "created_at", validate_utc(self.created_at, "created_at"))
        if self.expires_at is not None:
            expires = validate_utc(self.expires_at, "expires_at")
            object.__setattr__(self, "expires_at", expires)
            if expires <= self.created_at:
                raise InvalidDomainValue("expires_at must be after created_at")
        if not isinstance(self.evidence_refs, tuple):
            raise InvalidDomainValue("evidence_refs must be a tuple")


@dataclass(frozen=True)
class ApprovalRecord:
    """An immutable record of an approval decision and its lifecycle."""

    approval_id: str
    request_id: str
    decision: ApprovalDecision
    scope: str
    action: ActionName
    target: TargetResource
    required_mode: OperatingMode
    approver: str
    decided_at: datetime
    expires_at: datetime | None
    state: ApprovalState
    consumed_at: datetime | None = None
    revoked_at: datetime | None = None
    reason: str = ""
    evidence_ref: str = ""
    correlation_id: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "approval_id", validate_identifier(self.approval_id, "approval_id"))
        object.__setattr__(self, "request_id", validate_identifier(self.request_id, "request_id"))
        object.__setattr__(self, "scope", validate_identifier(self.scope, "scope"))
        object.__setattr__(self, "approver", validate_identifier(self.approver, "approver"))
        object.__setattr__(self, "reason", validate_identifier(self.reason or "approved", "reason"))
        if not isinstance(self.decision, ApprovalDecision):
            raise InvalidDomainValue("decision must be an ApprovalDecision")
        if not isinstance(self.action, ActionName):
            raise InvalidDomainValue("action must be an ActionName")
        if not isinstance(self.target, TargetResource):
            raise InvalidDomainValue("target must be a TargetResource")
        if not isinstance(self.required_mode, OperatingMode):
            raise InvalidDomainValue("required_mode must be an OperatingMode")
        if not isinstance(self.state, ApprovalState):
            raise InvalidDomainValue("state must be an ApprovalState")
        object.__setattr__(self, "decided_at", validate_utc(self.decided_at, "decided_at"))
        if self.expires_at is not None:
            expires = validate_utc(self.expires_at, "expires_at")
            if expires < self.decided_at:
                raise InvalidDomainValue("expires_at must not be before decided_at")
            object.__setattr__(self, "expires_at", expires)
        for field in ("consumed_at", "revoked_at"):
            value: Any = getattr(self, field)
            if value is not None:
                object.__setattr__(self, field, validate_utc(value, field))
        if self.evidence_ref:
            object.__setattr__(
                self, "evidence_ref", validate_identifier(self.evidence_ref, "evidence_ref")
            )
        if self.correlation_id is not None:
            object.__setattr__(
                self,
                "correlation_id",
                validate_identifier(self.correlation_id, "correlation_id"),
            )
