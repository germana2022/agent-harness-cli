import json

from agent_harness.output import render_version
from agent_harness.version import __version__


def test_version_is_expected():
    assert __version__ == "0.1.0"


def test_version_is_single_source_for_text_output():
    assert render_version("text") == f"agent-harness {__version__}"


def test_version_is_single_source_for_json_output():
    payload = json.loads(render_version("json"))
    assert payload["version"] == __version__
