import json
import os
import subprocess
import sys

import pytest
import typer
from typer.testing import CliRunner

import agent_harness.cli as cli
from agent_harness.cli import app
from agent_harness.exit_codes import (
    CONFIGURATION_ERROR,
    ENVIRONMENT_ERROR,
    INTERNAL_ERROR,
    USAGE_ERROR,
)

runner = CliRunner()

_ENV_VARS = (
    "AGENT_HARNESS_ENVIRONMENT",
    "AGENT_HARNESS_LOG_LEVEL",
    "AGENT_HARNESS_OUTPUT_FORMAT",
    "AGENT_HARNESS_READ_ONLY",
)


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch):
    for var in _ENV_VARS:
        monkeypatch.delenv(var, raising=False)


def invoke(*args, env=None):
    return runner.invoke(app, list(args), env=env or {})


def test_help():
    result = invoke("--help")
    assert result.exit_code == 0
    assert "Usage" in result.stdout


def test_version_text():
    result = invoke("version")
    assert result.exit_code == 0
    assert result.stdout.strip() == "agent-harness 0.1.0"


def test_version_json():
    result = invoke("--output", "json", "version")
    assert result.exit_code == 0
    assert json.loads(result.stdout) == {
        "command": "version",
        "status": "ok",
        "version": "0.1.0",
    }


def test_health_text():
    result = invoke("health")
    assert result.exit_code == 0
    lines = result.stdout.strip().splitlines()
    assert "status: healthy" in lines
    assert "version: 0.1.0" in lines
    assert any(line.startswith("python: ") for line in lines)


def test_health_json():
    result = invoke("--output", "json", "health")
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["command"] == "health"
    assert payload["status"] == "healthy"
    assert payload["version"] == "0.1.0"
    assert payload["python_version"]


def test_config_check_text():
    result = invoke("config-check")
    assert result.exit_code == 0
    assert result.stdout.strip() == "configuration: valid"


def test_config_check_json():
    result = invoke("--output", "json", "config-check")
    assert result.exit_code == 0
    assert json.loads(result.stdout) == {
        "command": "config-check",
        "status": "ok",
        "configuration": "valid",
    }


def test_invalid_command_is_usage_error():
    result = invoke("nonexistent")
    assert result.exit_code == USAGE_ERROR


def test_invalid_output_format_is_usage_error():
    result = invoke("--output", "xml", "version")
    assert result.exit_code == USAGE_ERROR
    assert "invalid output format" in result.stderr
    assert "agent-harness" not in result.stdout


def test_invalid_configuration_via_env():
    result = invoke("config-check", env={"AGENT_HARNESS_LOG_LEVEL": "VERBOSE"})
    assert result.exit_code == CONFIGURATION_ERROR
    assert "log_level" in result.stderr
    assert "VERBOSE" not in result.stderr
    assert "configuration: valid" not in result.stdout


def test_read_only_false_is_rejected():
    result = invoke(
        "config-check", env={"AGENT_HARNESS_READ_ONLY": "false"}
    )
    assert result.exit_code == CONFIGURATION_ERROR
    assert "read_only" in result.stderr
    assert "false" not in result.stderr
    assert "configuration: valid" not in result.stdout


def test_invalid_output_format_env_is_config_error():
    result = invoke(
        "config-check", env={"AGENT_HARNESS_OUTPUT_FORMAT": "xml"}
    )
    assert result.exit_code == CONFIGURATION_ERROR
    assert "output_format" in result.stderr
    assert "xml" not in result.stderr


def test_invalid_boolean_is_config_error():
    result = invoke(
        "config-check", env={"AGENT_HARNESS_READ_ONLY": "maybe"}
    )
    assert result.exit_code == CONFIGURATION_ERROR
    assert "read_only" in result.stderr
    assert "maybe" not in result.stderr


def test_multiple_invalid_fields_are_listed():
    result = invoke(
        "config-check",
        env={
            "AGENT_HARNESS_OUTPUT_FORMAT": "xml",
            "AGENT_HARNESS_READ_ONLY": "maybe",
        },
    )
    assert result.exit_code == CONFIGURATION_ERROR
    assert "output_format" in result.stderr
    assert "read_only" in result.stderr
    assert "xml" not in result.stderr
    assert "maybe" not in result.stderr


def test_ansi_in_invalid_value_is_sanitized():
    result = invoke(
        "config-check",
        env={"AGENT_HARNESS_OUTPUT_FORMAT": "\x1b[31mxml\x1b[0m"},
    )
    assert result.exit_code == CONFIGURATION_ERROR
    assert "output_format" in result.stderr
    assert "\x1b" not in result.stderr
    assert "xml" not in result.stderr


def test_health_unsupported_python(monkeypatch):
    monkeypatch.setattr(cli, "python_supported", lambda version_info: False)
    result = invoke("health")
    assert result.exit_code == ENVIRONMENT_ERROR
    assert "Python 3.11 or newer" in result.stderr


def test_unexpected_error_returns_internal(monkeypatch):
    def boom(invocation):
        raise RuntimeError("boom")

    monkeypatch.setattr(cli, "render_version", boom)
    result = invoke("version")
    assert result.exit_code == INTERNAL_ERROR
    assert "unexpected internal error" in result.stderr


def test_render_config_error_maps_to_exit_3(monkeypatch):
    from agent_harness.errors import ConfigurationError

    def boom(invocation):
        raise ConfigurationError("read_only cannot be disabled in Phase 1")

    monkeypatch.setattr(cli, "render_version", boom)
    result = invoke("version")
    assert result.exit_code == CONFIGURATION_ERROR
    assert "read_only" in result.stderr


def test_render_environment_error_maps_to_exit_4(monkeypatch):
    from agent_harness.errors import AgentEnvironmentError

    def boom(invocation):
        raise AgentEnvironmentError("unsupported runtime")

    monkeypatch.setattr(cli, "render_version", boom)
    result = invoke("version")
    assert result.exit_code == ENVIRONMENT_ERROR


def test_render_generic_agent_error_maps_to_internal(monkeypatch):
    from agent_harness.errors import AgentHarnessError

    def boom(invocation):
        raise AgentHarnessError("generic error")

    monkeypatch.setattr(cli, "render_version", boom)
    result = invoke("version")
    assert result.exit_code == INTERNAL_ERROR


def test_config_recheck_failure_is_config_error(monkeypatch):
    from agent_harness.errors import ConfigurationError

    real_settings = cli.Settings
    state = {"n": 0}

    def fake_settings():
        state["n"] += 1
        if state["n"] == 1:
            return real_settings()
        raise ConfigurationError("read_only cannot be disabled in Phase 1")

    monkeypatch.setattr(cli, "Settings", fake_settings)
    result = invoke("health")
    assert result.exit_code == CONFIGURATION_ERROR
    assert "read_only" in result.stderr


def test_keyboard_interrupt_is_not_swallowed(monkeypatch):
    def boom(invocation):
        raise KeyboardInterrupt()

    monkeypatch.setattr(cli, "render_version", boom)
    result = invoke("version")
    assert result.exit_code != 0
    assert result.exit_code != INTERNAL_ERROR


def test_exit_raised_by_render_propagates(monkeypatch):
    def boom(invocation):
        raise typer.Exit(code=7)

    monkeypatch.setattr(cli, "render_version", boom)
    result = invoke("version")
    assert result.exit_code == 7


def test_main_entry_function_runs_version_command(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["agent-harness", "version"])
    with pytest.raises(SystemExit) as exc_info:
        cli.main()
    assert exc_info.value.code == 0
    captured = capsys.readouterr()
    assert captured.out.strip() == "agent-harness 0.1.0"


def test_module_execution_parity():
    clean_env = {
        key: value
        for key, value in os.environ.items()
        if not key.startswith("AGENT_HARNESS_")
    }
    result = subprocess.run(
        [sys.executable, "-m", "agent_harness", "version"],
        capture_output=True,
        text=True,
        env=clean_env,
    )
    assert result.returncode == 0
    assert result.stdout.strip() == "agent-harness 0.1.0"
