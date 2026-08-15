"""Small deterministic text/JSON output abstraction for Phase 1.

Functional output is always plain text or JSON; no ANSI sequences are ever
emitted, so ``--no-color`` and JSON-without-ANSI guarantees are trivially met.
Diagnostics and logging are handled separately on stderr.
"""

from __future__ import annotations

import json
from typing import Any

from .version import __version__


def _to_json(payload: dict[str, Any]) -> str:
    return json.dumps(payload)


def render_version(output_format: str) -> str:
    if output_format == "json":
        return _to_json(
            {"command": "version", "status": "ok", "version": __version__}
        )
    return f"agent-harness {__version__}"


def render_health(output_format: str, python_version: str) -> str:
    if output_format == "json":
        return _to_json(
            {
                "command": "health",
                "status": "healthy",
                "version": __version__,
                "python_version": python_version,
            }
        )
    return "\n".join(
        (
            "status: healthy",
            f"version: {__version__}",
            f"python: {python_version}",
        )
    )


def render_config_check(output_format: str) -> str:
    if output_format == "json":
        return _to_json(
            {
                "command": "config-check",
                "status": "ok",
                "configuration": "valid",
            }
        )
    return "configuration: valid"
