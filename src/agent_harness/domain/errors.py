"""Domain error taxonomy.

Ordinary policy denials are returned as :class:`PolicyDecision` objects and
are never raised. Exceptions are reserved for exceptional domain misuse or
invalid construction.
"""

from __future__ import annotations

import re
from datetime import datetime, timedelta

_CONTROL = re.compile(r"[\x00-\x1f\x7f]")


class DomainError(Exception):
    """Base class for domain errors."""


class InvalidDomainValue(DomainError):
    """Raised when a domain model is constructed with invalid values."""


class InvalidTransition(DomainError):
    """Raised on state-machine misuse that is not a normal denial."""


class ApprovalLifecycleError(DomainError):
    """Raised on approval lifecycle misuse."""


class PolicyConfigurationError(DomainError):
    """Raised when policy configuration is invalid at construction time."""


class InternalDomainError(DomainError):
    """Raised on unexpected internal domain failures."""


def validate_identifier(value: object, field: str) -> str:
    """Return a normalized nonempty identifier without control characters."""
    if not isinstance(value, str):
        raise InvalidDomainValue(f"{field} must be a nonempty string")
    normalized = _CONTROL.sub("", value).strip()
    if not normalized:
        raise InvalidDomainValue(f"{field} must be a nonempty string")
    return normalized


def validate_utc(value: datetime, field: str) -> datetime:
    """Return the timestamp if it is a UTC-offset-zero aware value, else raise."""
    if value.tzinfo is None or value.utcoffset() is None:
        raise InvalidDomainValue(f"{field} must be UTC-aware")
    if value.utcoffset() != timedelta(0):
        raise InvalidDomainValue(f"{field} must have a UTC offset of zero")
    return value
