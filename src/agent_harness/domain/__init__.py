"""Domain contracts and policies for Agent Harness.

The domain layer depends only on the Python standard library and other domain
modules. It must never import CLI, framework, or infrastructure modules.
"""

from .actions import (
    CAPABILITY_CATEGORY,
    ActionCategory,
    ActionName,
    Capability,
    TargetResource,
)
from .allowlist import AllowlistEngine, AllowlistMatch, AllowlistRule, MatchMode, RuleKind
from .approval_manager import ApprovalManager, InMemoryApprovalManager
from .approvals import (
    TERMINAL_STATES,
    ApprovalDecision,
    ApprovalRecord,
    ApprovalRequest,
    ApprovalState,
)
from .clock import Clock, FixedClock, UtcClock
from .errors import (
    ApprovalLifecycleError,
    DomainError,
    InternalDomainError,
    InvalidDomainValue,
    InvalidTransition,
    PolicyConfigurationError,
)
from .modes import DEFAULT_MODE, OperatingMode, mode_allows_category, mode_requires_approval
from .policy import (
    REASON_MESSAGES,
    ApprovalAuthority,
    DefaultPolicyEngine,
    PolicyDecision,
    PolicyEngine,
    PolicyReasonCode,
    PolicyRequest,
    action_scope,
)
from .transitions import (
    ModeTransitionRequest,
    TransitionDecision,
    evaluate_transition,
    transition_scope,
)

__all__ = [
    "CAPABILITY_CATEGORY",
    "ActionCategory",
    "ActionName",
    "Capability",
    "TargetResource",
    "AllowlistEngine",
    "AllowlistMatch",
    "AllowlistRule",
    "MatchMode",
    "RuleKind",
    "ApprovalManager",
    "InMemoryApprovalManager",
    "TERMINAL_STATES",
    "ApprovalDecision",
    "ApprovalRecord",
    "ApprovalRequest",
    "ApprovalState",
    "Clock",
    "FixedClock",
    "UtcClock",
    "ApprovalLifecycleError",
    "DomainError",
    "InternalDomainError",
    "InvalidDomainValue",
    "InvalidTransition",
    "PolicyConfigurationError",
    "DEFAULT_MODE",
    "OperatingMode",
    "mode_allows_category",
    "mode_requires_approval",
    "REASON_MESSAGES",
    "ApprovalAuthority",
    "DefaultPolicyEngine",
    "PolicyDecision",
    "PolicyEngine",
    "PolicyReasonCode",
    "PolicyRequest",
    "action_scope",
    "ModeTransitionRequest",
    "TransitionDecision",
    "evaluate_transition",
    "transition_scope",
]
