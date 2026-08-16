"""Deterministic time abstraction for the domain.

All lifecycle and expiration decisions use an injected :class:`Clock` so that
behavior is unit-testable without wall-clock dependence.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Protocol

from .errors import validate_utc


class Clock(Protocol):
    """Protocol for UTC-aware time sources."""

    def now(self) -> datetime:
        """Return the current UTC-aware timestamp."""
        ...


class UtcClock:
    """Production clock returning the current UTC time."""

    def now(self) -> datetime:
        return datetime.now(timezone.utc)


class FixedClock:
    """Deterministic clock for tests and reproducible scenarios.

    ``advance`` moves the clock forward so expiration boundaries can be
    exercised without sleeping.
    """

    def __init__(self, start: datetime) -> None:
        self._current = validate_utc(start, "start")

    def now(self) -> datetime:
        return self._current

    def advance(self, delta: timedelta) -> None:
        self._current = validate_utc(self._current + delta, "advanced time")
