"""Operating-mode model.

The default mode is ``READ_ONLY``. Escalations require approval; returns to a
more restrictive mode never do.
"""

from __future__ import annotations

from enum import Enum

from .actions import ActionCategory


class OperatingMode(Enum):
    """Operating modes of the harness."""

    READ_ONLY = "read_only"
    WORKSPACE_WRITE = "workspace_write"
    DELIVERY = "delivery"


DEFAULT_MODE = OperatingMode.READ_ONLY

_LOCAL_CATEGORIES = frozenset(
    {
        ActionCategory.LOCAL_WRITE,
        ActionCategory.EXECUTION,
        ActionCategory.GIT_MUTATION,
    }
)


def mode_allows_category(mode: OperatingMode, category: ActionCategory) -> bool:
    """Return whether ``category`` is permitted at the mode level.

    Approval and allowlist requirements are evaluated separately by the policy
    engine; this function answers only whether the mode permits the category.
    """
    if category is ActionCategory.READ:
        return True
    if mode is OperatingMode.READ_ONLY:
        return False
    if category is ActionCategory.EXTERNAL:
        return mode is OperatingMode.DELIVERY
    if category is ActionCategory.DESTRUCTIVE:
        return mode is OperatingMode.DELIVERY
    return mode in (OperatingMode.WORKSPACE_WRITE, OperatingMode.DELIVERY)


def mode_requires_approval(mode: OperatingMode, category: ActionCategory) -> bool:
    """Return whether the mode mandates approval for the category.

    ``WORKSPACE_WRITE`` local mutations are governed by policy configuration;
    the caller decides whether they require approval.
    """
    if category in (ActionCategory.EXTERNAL, ActionCategory.DESTRUCTIVE):
        return True
    if mode is OperatingMode.DELIVERY and category in _LOCAL_CATEGORIES:
        return True
    return False
