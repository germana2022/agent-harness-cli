import json

from agent_harness.output import render_config_check, render_health, render_version

_ANSI = "\x1b"


def test_version_text():
    assert render_version("text") == "agent-harness 0.1.0"


def test_version_json_fields():
    payload = json.loads(render_version("json"))
    assert payload == {"command": "version", "status": "ok", "version": "0.1.0"}


def test_health_text():
    output = render_health("text", "3.11.9")
    assert output == "status: healthy\nversion: 0.1.0\npython: 3.11.9"


def test_health_json_fields():
    payload = json.loads(render_health("json", "3.11.9"))
    assert payload == {
        "command": "health",
        "status": "healthy",
        "version": "0.1.0",
        "python_version": "3.11.9",
    }


def test_config_check_text():
    assert render_config_check("text") == "configuration: valid"


def test_config_check_json_fields():
    payload = json.loads(render_config_check("json"))
    assert payload == {
        "command": "config-check",
        "status": "ok",
        "configuration": "valid",
    }


def test_json_contains_no_ansi():
    outputs = (
        render_version("json"),
        render_health("json", "3.11.9"),
        render_config_check("json"),
    )
    for output in outputs:
        assert _ANSI not in output


def test_output_is_deterministic():
    assert render_version("text") == render_version("text")
    assert render_version("json") == render_version("json")
    assert render_health("text", "3.11.9") == render_health("text", "3.11.9")
    assert render_config_check("text") == render_config_check("text")
