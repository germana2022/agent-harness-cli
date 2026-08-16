"""Approval manager contract and a locked in-memory implementation.

The manager is the authoritative approval store. Caller-supplied approval
records are never authoritative; authorization always resolves the current
stored record by identifier and validates lifecycle, expiration, action,
target, canonical scope, and required mode.
"""

from __future__ import annotations

import threading
from dataclasses import replace
from datetime import datetime
from typing import Protocol

from .actions import ActionName, TargetResource
from .approvals import (
    ApprovalDecision,
    ApprovalRecord,
    ApprovalRequest,
    ApprovalState,
)
from .clock import Clock
from .errors import ApprovalLifecycleError
from .policy import (
    REASON_MESSAGES,
    ApprovalAuthority,
    PolicyDecision,
    PolicyReasonCode,
    _evaluate_approval_record,
    _state_and_expiration_reason,
    action_scope,
)
from .transitions import transition_scope


class ApprovalManager(Protocol):
    """Protocol for approval lifecycle management and authorization."""

    def request(self, request: ApprovalRequest) -> ApprovalRequest: ...

    def record_decision(
        self,
        request_id: str,
        decision: ApprovalDecision,
        approver: str,
        reason: str,
    ) -> ApprovalRecord: ...

    def get(self, approval_id: str) -> ApprovalRecord: ...

    def consume(self, approval_id: str) -> ApprovalRecord: ...

    def revoke(self, approval_id: str) -> ApprovalRecord: ...

    def authorize_action(
        self,
        approval_id: str,
        action: ActionName,
        target: TargetResource,
        mode: object,
        at_time: datetime,
    ) -> PolicyDecision: ...

    def authorize_transition(
        self,
        approval_id: str,
        from_mode: object,
        to_mode: object,
        at_time: datetime,
    ) -> PolicyDecision: ...

    def consume_action(
        self,
        approval_id: str,
        action: ActionName,
        target: TargetResource,
        mode: object,
        at_time: datetime,
    ) -> PolicyDecision: ...

    def consume_transition(
        self,
        approval_id: str,
        from_mode: object,
        to_mode: object,
        at_time: datetime,
    ) -> PolicyDecision: ...


class InMemoryApprovalManager:
    """Single-process, thread-safe approval manager backed by dictionaries.

    Implements :class:`ApprovalAuthority`; all authorization resolves stored
    records under one lock so that validation and consumption are atomic.
    """

    def __init__(self, clock: Clock) -> None:
        self._clock = clock
        self._lock = threading.Lock()
        self._requests: dict[str, ApprovalRequest] = {}
        self._records: dict[str, ApprovalRecord] = {}
        self._by_request: dict[str, str] = {}

    # --- lifecycle ---

    def request(self, request: ApprovalRequest) -> ApprovalRequest:
        with self._lock:
            if request.request_id in self._requests:
                raise ApprovalLifecycleError("duplicate approval request id")
            self._requests[request.request_id] = request
            return request

    def record_decision(
        self,
        request_id: str,
        decision: ApprovalDecision,
        approver: str,
        reason: str,
    ) -> ApprovalRecord:
        with self._lock:
            existing_request = self._requests.get(request_id)
            if existing_request is None:
                raise ApprovalLifecycleError("unknown approval request id")
            if request_id in self._by_request:
                raise ApprovalLifecycleError("decision already recorded for request")
            approval_id = f"appr-{request_id}"
            now = self._clock.now()
            state = (
                ApprovalState.APPROVED
                if decision is ApprovalDecision.APPROVED
                else ApprovalState.DENIED
            )
            record = ApprovalRecord(
                approval_id=approval_id,
                request_id=request_id,
                decision=decision,
                scope=existing_request.scope,
                action=existing_request.action,
                target=existing_request.target,
                required_mode=existing_request.required_mode,
                approver=approver,
                decided_at=now,
                expires_at=existing_request.expires_at,
                state=state,
                reason=reason,
            )
            self._records[approval_id] = record
            self._by_request[request_id] = approval_id
            return record

    def get(self, approval_id: str) -> ApprovalRecord:
        with self._lock:
            record = self._records.get(approval_id)
            if record is None:
                raise ApprovalLifecycleError("unknown approval id")
            refreshed = self._refresh(record)
            self._records[approval_id] = refreshed
            return refreshed

    def consume(self, approval_id: str) -> ApprovalRecord:
        """Raw lifecycle primitive: mark an approved record consumed.

        This is not an authorization gate; use ``consume_action`` or
        ``consume_transition`` for scoped, authoritative consumption.
        """
        with self._lock:
            record = self._records.get(approval_id)
            if record is None:
                raise ApprovalLifecycleError("unknown approval id")
            refreshed = self._refresh(record)
            if refreshed.state is not ApprovalState.APPROVED:
                raise ApprovalLifecycleError(
                    f"only approved approvals can be consumed (state={refreshed.state.value})"
                )
            consumed = replace(
                refreshed, state=ApprovalState.CONSUMED, consumed_at=self._clock.now()
            )
            self._records[approval_id] = consumed
            return consumed

    def revoke(self, approval_id: str) -> ApprovalRecord:
        with self._lock:
            record = self._records.get(approval_id)
            if record is None:
                raise ApprovalLifecycleError("unknown approval id")
            refreshed = self._refresh(record)
            if refreshed.state is not ApprovalState.APPROVED:
                raise ApprovalLifecycleError(
                    f"only approved approvals can be revoked (state={refreshed.state.value})"
                )
            revoked = replace(
                refreshed, state=ApprovalState.REVOKED, revoked_at=self._clock.now()
            )
            self._records[approval_id] = revoked
            return revoked

    # --- authorization (ApprovalAuthority) ---

    def authorize_action(
        self,
        approval_id: str,
        action: ActionName,
        target: TargetResource,
        mode: object,
        at_time: datetime,
    ) -> PolicyDecision:
        with self._lock:
            return self._authorize_action_locked(approval_id, action, target, mode, at_time)

    def authorize_transition(
        self,
        approval_id: str,
        from_mode: object,
        to_mode: object,
        at_time: datetime,
    ) -> PolicyDecision:
        with self._lock:
            return self._authorize_transition_locked(approval_id, from_mode, to_mode, at_time)

    def consume_action(
        self,
        approval_id: str,
        action: ActionName,
        target: TargetResource,
        mode: object,
        at_time: datetime,
    ) -> PolicyDecision:
        with self._lock:
            verdict = self._authorize_action_locked(approval_id, action, target, mode, at_time)
            if not verdict.allowed:
                return verdict
            self._mark_consumed_locked(approval_id)
            return self._allow(approval_id)

    def consume_transition(
        self,
        approval_id: str,
        from_mode: object,
        to_mode: object,
        at_time: datetime,
    ) -> PolicyDecision:
        with self._lock:
            verdict = self._authorize_transition_locked(approval_id, from_mode, to_mode, at_time)
            if not verdict.allowed:
                return verdict
            self._mark_consumed_locked(approval_id)
            return self._allow(approval_id)

    # --- internal helpers (must be called under the lock) ---

    def _authorize_action_locked(
        self,
        approval_id: str,
        action: ActionName,
        target: TargetResource,
        mode: object,
        at_time: datetime,
    ) -> PolicyDecision:
        record, missing = self._lookup_locked(approval_id)
        if missing is not None:
            return missing
        if record.required_mode is not mode:
            return self._deny(PolicyReasonCode.APPROVAL_SCOPE_MISMATCH)
        return _evaluate_approval_record(
            record, action, target, action_scope(action), at_time
        )

    def _authorize_transition_locked(
        self,
        approval_id: str,
        from_mode: object,
        to_mode: object,
        at_time: datetime,
    ) -> PolicyDecision:
        record, missing = self._lookup_locked(approval_id)
        if missing is not None:
            return missing
        expected_scope = transition_scope(from_mode, to_mode)
        reason = _state_and_expiration_reason(record, at_time)
        if reason is not None:
            return self._deny(reason)
        if record.scope != expected_scope or record.required_mode is not to_mode:
            return self._deny(PolicyReasonCode.APPROVAL_SCOPE_MISMATCH)
        return self._allow(approval_id)

    def _lookup_locked(self, approval_id: str):
        record = self._records.get(approval_id)
        if record is None:
            return None, self._deny(PolicyReasonCode.APPROVAL_MISSING)
        refreshed = self._refresh(record)
        if refreshed is not record:
            self._records[approval_id] = refreshed
        return refreshed, None

    def _mark_consumed_locked(self, approval_id: str) -> None:
        record = self._records[approval_id]
        self._records[approval_id] = replace(
            record, state=ApprovalState.CONSUMED, consumed_at=self._clock.now()
        )

    def _deny(self, reason: PolicyReasonCode) -> PolicyDecision:
        return PolicyDecision(
            allowed=False,
            reason_code=reason,
            message=REASON_MESSAGES[reason],
            approval_required=True,
        )

    @staticmethod
    def _allow(approval_id: str) -> PolicyDecision:
        return PolicyDecision(
            allowed=True,
            reason_code=PolicyReasonCode.ALLOWED,
            message=REASON_MESSAGES[PolicyReasonCode.ALLOWED],
            approval_required=True,
            evidence=(approval_id,),
        )

    def _refresh(self, record: ApprovalRecord) -> ApprovalRecord:
        if (
            record.state is ApprovalState.APPROVED
            and record.expires_at is not None
            and record.expires_at <= self._clock.now()
        ):
            return replace(record, state=ApprovalState.EXPIRED)
        return record
