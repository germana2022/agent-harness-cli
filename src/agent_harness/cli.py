"""Typer CLI application and exit-code translation boundary."""

from __future__ import annotations

import platform
import sys
from typing import Callable, Optional

import typer
from pydantic import ValidationError

from .config import Settings
from .errors import AgentEnvironmentError, AgentHarnessError, ConfigurationError, sanitize_error
from .exit_codes import (
    CONFIGURATION_ERROR,
    ENVIRONMENT_ERROR,
    INTERNAL_ERROR,
    USAGE_ERROR,
)
from .logging_config import setup_logging
from .output import render_config_check, render_health, render_version
from .application.inspection_service import InspectionService
from .infrastructure.git_metadata import GitMetadataReader
from .infrastructure.inspector import Inspector
from .inspection.errors import InspectionError
from .inspection.request import (
    DEFAULT_MAX_DEPTH,
    DEFAULT_MAX_ENTRIES,
    HARD_MAX_DEPTH,
    HARD_MAX_ENTRIES,
    InspectionRequest,
)
from .inspection.serialization import to_json, to_text

app = typer.Typer(add_completion=False, no_args_is_help=True)

OUTPUT_FORMATS = ("text", "json")


class Invocation:
    """Per-invocation state: validated configuration and effective options."""

    def __init__(self, settings: Settings, output_format: str, verbose: bool, no_color: bool) -> None:
        self.settings = settings
        self.output_format = output_format
        self.verbose = verbose
        self.no_color = no_color


def python_supported(version_info: tuple[int, ...]) -> bool:
    """Return whether the runtime major/minor satisfies Python 3.11+."""
    return (version_info[0], version_info[1]) >= (3, 11)


def _fail(message: str, code: int) -> None:
    typer.echo(f"error: {message}", err=True)
    raise typer.Exit(code=code)


def _exit_code_for(exc: AgentHarnessError) -> int:
    if isinstance(exc, ConfigurationError):
        return CONFIGURATION_ERROR
    if isinstance(exc, AgentEnvironmentError):
        return ENVIRONMENT_ERROR
    return INTERNAL_ERROR


def _ensure_config_ok() -> None:
    try:
        Settings()
    except (AgentHarnessError, ValidationError) as exc:
        _fail(sanitize_error(exc), CONFIGURATION_ERROR)


def _execute(render: Callable[[Invocation], str], invocation: Invocation) -> None:
    try:
        typer.echo(render(invocation))
    except typer.Exit:
        raise
    except KeyboardInterrupt:
        raise
    except AgentHarnessError as exc:
        _fail(sanitize_error(exc), _exit_code_for(exc))
    except Exception:
        _fail("unexpected internal error", INTERNAL_ERROR)


@app.callback()
def _main(
    ctx: typer.Context,
    output: Optional[str] = typer.Option(
        None, "--output", help="Output format: 'text' or 'json'."
    ),
    verbose: bool = typer.Option(False, "--verbose", help="Enable verbose diagnostics."),
    no_color: bool = typer.Option(
        False, "--no-color", help="Disable ANSI color output."
    ),
) -> None:
    if output is not None and output not in OUTPUT_FORMATS:
        _fail(
            f"invalid output format {output!r}; must be one of {', '.join(OUTPUT_FORMATS)}",
            USAGE_ERROR,
        )
    try:
        settings = Settings()
    except (AgentHarnessError, ValidationError) as exc:
        _fail(sanitize_error(exc), CONFIGURATION_ERROR)
    effective_output = output if output is not None else settings.output_format
    setup_logging(settings.log_level, verbose)
    ctx.obj = Invocation(settings, effective_output, verbose, no_color)


@app.command("version")
def version_cmd(ctx: typer.Context) -> None:
    invocation: Invocation = ctx.obj
    _execute(lambda inv: render_version(inv.output_format), invocation)


@app.command("health")
def health_cmd(ctx: typer.Context) -> None:
    invocation: Invocation = ctx.obj
    _ensure_config_ok()
    python_version = platform.python_version()
    if not python_supported(sys.version_info):
        _fail(
            f"unsupported Python runtime {python_version}; "
            "Python 3.11 or newer is required",
            ENVIRONMENT_ERROR,
        )
    _execute(lambda inv: render_health(inv.output_format, python_version), invocation)


@app.command("config-check")
def config_check_cmd(ctx: typer.Context) -> None:
    invocation: Invocation = ctx.obj
    _ensure_config_ok()
    _execute(lambda inv: render_config_check(inv.output_format), invocation)


def _inspection_service() -> InspectionService:
    from .domain.allowlist import AllowlistEngine
    from .domain.clock import UtcClock
    from .domain.policy import DefaultPolicyEngine

    return InspectionService(
        inspector=Inspector(),
        git_reader=GitMetadataReader(),
        policy_engine=DefaultPolicyEngine(clock=UtcClock(), allowlist=AllowlistEngine()),
    )


@app.command("inspect")
def inspect_cmd(
    ctx: typer.Context,
    path: Optional[str] = typer.Option(
        None, "--path", help="Local directory to inspect (default: current directory)."
    ),
    max_entries: Optional[int] = typer.Option(
        None, "--max-entries", help="Maximum file entries (bounded)."
    ),
    max_depth: Optional[int] = typer.Option(
        None, "--max-depth", help="Maximum traversal depth (bounded)."
    ),
    use_git: Optional[bool] = typer.Option(
        None, "--git/--no-git", help="Include or skip read-only Git metadata."
    ),
) -> None:
    invocation: Invocation = ctx.obj
    try:
        result = _run_inspection(invocation, path, max_entries, max_depth, use_git)
    except InspectionError as exc:
        _fail(str(exc), exc.exit_code)
    except typer.Exit:
        raise
    except KeyboardInterrupt:
        raise
    except Exception:
        _fail("unexpected internal error", INTERNAL_ERROR)
    if invocation.output_format == "json":
        output = to_json(result)
    else:
        output = to_text(result)
    typer.echo(output)


def _run_inspection(
    invocation: Invocation,
    path: Optional[str],
    max_entries: Optional[int],
    max_depth: Optional[int],
    use_git: Optional[bool],
):
    if max_entries is not None and not (1 <= max_entries <= HARD_MAX_ENTRIES):
        _fail(
            f"invalid --max-entries {max_entries}; must be between 1 and {HARD_MAX_ENTRIES}",
            USAGE_ERROR,
        )
    if max_depth is not None and not (1 <= max_depth <= HARD_MAX_DEPTH):
        _fail(
            f"invalid --max-depth {max_depth}; must be between 1 and {HARD_MAX_DEPTH}",
            USAGE_ERROR,
        )
    git_mode = "auto"
    if use_git is True:
        git_mode = "on"
    elif use_git is False:
        git_mode = "off"
    request = InspectionRequest(
        requested_path=path or ".",
        max_entries=max_entries if max_entries is not None else DEFAULT_MAX_ENTRIES,
        max_depth=max_depth if max_depth is not None else DEFAULT_MAX_DEPTH,
        git_metadata=git_mode,
    )
    return _inspection_service().inspect(request)


def main() -> None:
    app()


if __name__ == "__main__":
    main()
