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


def main() -> None:
    app()


if __name__ == "__main__":
    main()
