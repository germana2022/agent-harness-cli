import pytest
from pydantic import ValidationError

from agent_harness.config import Settings
from agent_harness.errors import AgentHarnessError, ConfigurationError, sanitize_error

_ENV_VARS = (
    "AGENT_HARNESS_ENVIRONMENT",
    "AGENT_HARNESS_LOG_LEVEL",
    "AGENT_HARNESS_OUTPUT_FORMAT",
    "AGENT_HARNESS_READ_ONLY",
)


def _clean_env(monkeypatch):
    for var in _ENV_VARS:
        monkeypatch.delenv(var, raising=False)


def test_default_settings(monkeypatch):
    _clean_env(monkeypatch)
    settings = Settings()
    assert settings.environment == "development"
    assert settings.log_level == "INFO"
    assert settings.output_format == "text"
    assert settings.read_only is True


def test_environment_overrides_defaults(monkeypatch):
    _clean_env(monkeypatch)
    monkeypatch.setenv("AGENT_HARNESS_ENVIRONMENT", "staging")
    monkeypatch.setenv("AGENT_HARNESS_LOG_LEVEL", "DEBUG")
    monkeypatch.setenv("AGENT_HARNESS_OUTPUT_FORMAT", "json")
    monkeypatch.setenv("AGENT_HARNESS_READ_ONLY", "true")
    settings = Settings()
    assert settings.environment == "staging"
    assert settings.log_level == "DEBUG"
    assert settings.output_format == "json"
    assert settings.read_only is True


def test_read_only_false_is_rejected(monkeypatch):
    _clean_env(monkeypatch)
    monkeypatch.setenv("AGENT_HARNESS_READ_ONLY", "false")
    with pytest.raises(ConfigurationError):
        Settings()


def test_invalid_log_level_is_rejected(monkeypatch):
    _clean_env(monkeypatch)
    monkeypatch.setenv("AGENT_HARNESS_LOG_LEVEL", "VERBOSE")
    with pytest.raises(ConfigurationError):
        Settings()


def test_invalid_output_format_is_rejected(monkeypatch):
    _clean_env(monkeypatch)
    monkeypatch.setenv("AGENT_HARNESS_OUTPUT_FORMAT", "xml")
    with pytest.raises(ValidationError):
        Settings()


def test_unknown_env_variables_are_ignored(monkeypatch):
    _clean_env(monkeypatch)
    monkeypatch.setenv("AGENT_HARNESS_UNKNOWN_VALUE", "something")
    monkeypatch.setenv("UNRELATED_VALUE", "x")
    settings = Settings()
    assert settings.environment == "development"
    assert settings.log_level == "INFO"


def test_constructs_with_init_values(monkeypatch):
    _clean_env(monkeypatch)
    settings = Settings(environment="prod", output_format="json")
    assert settings.environment == "prod"
    assert settings.output_format == "json"


def test_agent_environment_error_exists_and_inherits():
    from agent_harness.errors import AgentEnvironmentError

    assert issubclass(AgentEnvironmentError, AgentHarnessError)


def test_project_environment_error_alias_removed():
    import agent_harness.errors as errors_module

    assert not hasattr(errors_module, "EnvironmentError")


def test_sanitize_configuration_error():
    message = sanitize_error(
        ConfigurationError("read_only cannot be disabled in Phase 1")
    )
    assert message == "configuration: read_only cannot be disabled in Phase 1"


def test_sanitize_generic_agent_error():
    assert sanitize_error(AgentHarnessError("boom")) == "boom"


def test_sanitize_unexpected_error():
    assert sanitize_error(RuntimeError("boom")) == "unexpected error"


def test_sanitize_validation_error():
    with pytest.raises(ValidationError) as exc_info:
        Settings(output_format="xml")
    message = sanitize_error(exc_info.value)
    assert message == "invalid configuration field: output_format"
    assert "xml" not in message
    assert "input_value" not in message


def test_sanitize_validation_error_fallback(monkeypatch):
    with pytest.raises(ValidationError) as exc_info:
        Settings(output_format="xml")
    error = exc_info.value

    def boom():
        raise RuntimeError("no errors")

    monkeypatch.setattr(error, "errors", boom)
    assert sanitize_error(error) == "invalid configuration"


def test_sanitize_validation_error_without_loc(monkeypatch):
    with pytest.raises(ValidationError) as exc_info:
        Settings(output_format="xml")
    error = exc_info.value

    monkeypatch.setattr(
        error, "errors", lambda: [{"msg": "invalid value", "loc": ()}]
    )
    assert sanitize_error(error) == "invalid configuration"


def test_sanitize_multiple_validation_fields(monkeypatch):
    _clean_env(monkeypatch)
    monkeypatch.setenv("AGENT_HARNESS_OUTPUT_FORMAT", "xml")
    monkeypatch.setenv("AGENT_HARNESS_READ_ONLY", "maybe")
    with pytest.raises(ValidationError) as exc_info:
        Settings()
    message = sanitize_error(exc_info.value)
    assert message == "invalid configuration fields: output_format, read_only"
    assert "xml" not in message
    assert "maybe" not in message


def test_sanitize_control_characters_stripped(monkeypatch):
    with pytest.raises(ValidationError) as exc_info:
        Settings(output_format="xml")
    error = exc_info.value

    monkeypatch.setattr(
        error,
        "errors",
        lambda: [{"msg": "bad", "loc": ("\x1b[31mfield\x1b[0m",)}],
    )
    message = sanitize_error(error)
    assert message.startswith("invalid configuration field:")
    assert "\x1b" not in message


def test_invalid_log_level_error_does_not_echo_value(monkeypatch):
    _clean_env(monkeypatch)
    monkeypatch.setenv("AGENT_HARNESS_LOG_LEVEL", "AH01_CANARY_DO_NOT_ECHO")
    with pytest.raises(ConfigurationError) as exc_info:
        Settings()
    message = str(exc_info.value)
    assert "log_level" in message
    assert "AH01_CANARY_DO_NOT_ECHO" not in message


def test_invalid_log_level_long_value_not_echoed(monkeypatch):
    _clean_env(monkeypatch)
    long_value = "X" * 5000
    monkeypatch.setenv("AGENT_HARNESS_LOG_LEVEL", long_value)
    with pytest.raises(ConfigurationError) as exc_info:
        Settings()
    message = str(exc_info.value)
    assert "log_level" in message
    assert long_value not in message


def test_invalid_log_level_newline_value_not_echoed(monkeypatch):
    _clean_env(monkeypatch)
    monkeypatch.setenv("AGENT_HARNESS_LOG_LEVEL", "bad\nreset\nclear")
    with pytest.raises(ConfigurationError) as exc_info:
        Settings()
    message = str(exc_info.value)
    assert "\n" not in message
    assert "bad" not in message


def test_invalid_log_level_ansi_value_not_echoed(monkeypatch):
    _clean_env(monkeypatch)
    monkeypatch.setenv("AGENT_HARNESS_LOG_LEVEL", "\x1b[31mBAD\x1b[0m")
    with pytest.raises(ConfigurationError) as exc_info:
        Settings()
    message = str(exc_info.value)
    assert "\x1b" not in message
    assert "BAD" not in message
