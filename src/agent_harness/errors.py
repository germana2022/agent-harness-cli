"""Minimal expected-error hierarchy and sanitized message formatting."""

from __future__ import annotations

import re
from typing import Any

from pydantic import ValidationError

_CONTROL_CHARACTERS = re.compile(r"[\x00-\x1f\x7f]")


class AgentHarnessError(Exception):
    """Base class for expected, user-facing agent-harness errors."""


class ConfigurationError(AgentHarnessError):
    """Raised when agent-harness configuration is invalid."""


class AgentEnvironmentError(AgentHarnessError):
    """Raised when the runtime environment is unsupported."""


def sanitize_error(exc: Exception) -> str:
    """Return a concise, sanitized message without raw values or env dumps."""
    if isinstance(exc, ConfigurationError):
        return f"configuration: {exc}"
    if isinstance(exc, ValidationError):
        return _configuration_fields_message(exc)
    if isinstance(exc, AgentHarnessError):
        return str(exc)
    return "unexpected error"


def _safe_field_name(loc: Any) -> str:
    """Derive a safe field name from a validation location.

    Control characters and ANSI sequences are stripped so field-derived text
    cannot be used for terminal-control injection.
    """
    name = ".".join(str(part) for part in loc)
    return _CONTROL_CHARACTERS.sub("", name)


def _configuration_fields_message(exc: ValidationError) -> str:
    """Return a message identifying only invalid field names.

    Raw input values, ``input_value``, ``input_type``, complete Pydantic
    representations, and validation URLs are never included.
    """
    fields: set[str] = set()
    try:
        entries: list[dict[str, Any]] = exc.errors()
    except Exception:
        return "invalid configuration"
    for entry in entries:
        name = _safe_field_name(entry.get("loc", ()))
        if name:
            fields.add(name)
    ordered = sorted(fields)
    if not ordered:
        return "invalid configuration"
    if len(ordered) == 1:
        return f"invalid configuration field: {ordered[0]}"
    return f"invalid configuration fields: {', '.join(ordered)}"
