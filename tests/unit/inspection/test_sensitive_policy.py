import builtins
import json

import pytest

from agent_harness.infrastructure.inspector import Inspector, _has_sensitive_bounded_token
from agent_harness.inspection.request import InspectionRequest
from agent_harness.inspection.serialization import to_json, to_text

PROTECTED_POSITIVE = {
    # currently protected exact/suffix/prefix names must remain redacted
    ".env",
    ".env.local",
    ".env.production",
    ".env.development",
    ".env.test",
    "id_rsa",
    "id_ed25519",
    "id_dsa",
    "id_ecdsa",
    ".npmrc",
    ".pypirc",
    ".netrc",
    "credentials",
    "credentials.json",
    "credentials.toml",
    "client_secret.json",
    "service_account.json",
    "secrets.json",
    "cert.pem",
    "server.key",
    "app.p12",
    "client.pfx",
    "store.jks",
    "mastersecret.secret",
}

CRED_TOKEN_POSITIVE = {
    "cred",
    "creds",
    "creds.toml",
    "service-creds.json",
    "database_creds.yaml",
    "CREDENTIALS",
    "Creds",
    "Cred.toml",
    "DB-CREDS.yml",
    "prod_creds.ini",
    "creds ",
    " my.creds",
}

NEAR_MATCH_NEGATIVE = {
    "accredited.py",
    "accreditation.txt",
    "credit.py",
    "credito.yaml",
    "credentialing.py",
    "discredited.log",
    "secret_code.py",
    "token.py",
    "password_manager.py",
    "keyboard.py",
    "pem_builder.py",
    "id_rsa.pub",
}

ENV_EXAMPLE_VISIBLE = {".env.example", ".ENV.EXAMPLE", "Env.Example", ".env.exaMple"}

ENV_EXAMPLE_VARIANTS_STILL_PROTECTED = {
    ".env.example.local",
    ".env.example.bak",
    ".env.example.copy",
    ".env.example.2024",
    ".env.example.local.bak",
}

ORDINARY_VISIBLE = {
    "config.yaml",
    "settings.ini",
    "app.json",
    "README.md",
    "example.py",
    "examples.md",
}


def _is_sensitive(name):
    return Inspector._is_sensitive_name(name)


def test_cred_tokens_positive():
    for name in CRED_TOKEN_POSITIVE | PROTECTED_POSITIVE:
        assert _is_sensitive(name), name


def test_cred_tokens_negative_near_matches():
    for name in NEAR_MATCH_NEGATIVE:
        assert not _is_sensitive(name), name


def test_env_example_exception_visible():
    for name in ENV_EXAMPLE_VISIBLE:
        assert not _is_sensitive(name), name


def test_env_example_variants_still_protected():
    for name in ENV_EXAMPLE_VARIANTS_STILL_PROTECTED:
        assert _is_sensitive(name), name


def test_ordinary_config_visible():
    for name in ORDINARY_VISIBLE:
        assert not _is_sensitive(name), name


def test_bounded_token_helper_boundaries():
    assert _has_sensitive_bounded_token("creds") is True
    assert _has_sensitive_bounded_token("creds.toml") is True
    assert _has_sensitive_bounded_token("service-creds.json") is True
    assert _has_sensitive_bounded_token("accredited") is False
    assert _has_sensitive_bounded_token("credit") is False
    assert _has_sensitive_bounded_token("mycreds") is False
    assert _has_sensitive_bounded_token("credsfile") is False


def _walk_tree(tmp_path, names):
    (tmp_path / ".git").mkdir(exist_ok=True)
    for name in names:
        (tmp_path / name).write_text("synthetic-{}".format(name))
    return Inspector().inspect(tmp_path, InspectionRequest(include_hidden=True))


@pytest.mark.parametrize(
    "hidden_and_sensitive",
    [
        ".env",
        "creds.toml",
        "service-creds.json",
        "id_rsa",
        "server.key",
        ".env.example.bak",
    ],
)
def test_sensitive_entry_redacted_in_result(tmp_path, hidden_and_sensitive):
    summary = _walk_tree(tmp_path, [hidden_and_sensitive, "ok.py"])
    paths = [e.repository_relative_path for e in summary.entries]
    assert hidden_and_sensitive not in paths
    redacted = [e for e in summary.entries if e.redacted]
    assert len(redacted) >= 1
    assert redacted[0].repository_relative_path.startswith("<sensitive-")
    assert summary.sensitive_entries >= 1
    assert "ok.py" in paths


@pytest.mark.parametrize("visible", [".env.example", "config.yaml", "README.md"])
def test_exception_and_ordinary_visible_in_result(tmp_path, visible):
    summary = _walk_tree(tmp_path, [visible])
    paths = [e.repository_relative_path for e in summary.entries]
    assert visible.strip() in paths or visible in paths
    redacted = [e for e in summary.entries if e.redacted]
    assert redacted == []


def test_cross_output_text_and_json(tmp_path):
    names = ["creds.toml", "service-creds.json", ".env", ".env.example", "ok.py"]
    summary = _walk_tree(tmp_path, names)
    text = to_text(summary_result(summary))
    js = json.loads(to_json(summary_result(summary)))
    for leaked in ("creds.toml", "service-creds.json"):
        assert leaked not in text
        assert leaked not in js["entries"]
    assert "<sensitive-1>" in text or "<sensitive-" in text
    assert any(entry["redacted"] for entry in js["entries"])
    assert ".env.example" in text
    assert any(e["repository_relative_path"].endswith(".env.example") for e in js["entries"])


def test_deterministic_ordering(tmp_path):
    names = ["creds.toml", "ok.py", ".env", ".env.example", "id_rsa"]
    first = _walk_tree(tmp_path, names)
    second = _walk_tree(tmp_path, names)
    assert [e.repository_relative_path for e in first.entries] == [
        e.repository_relative_path for e in second.entries
    ]
    assert to_json(summary_result(first)) == to_json(summary_result(second))


def test_synthetic_contents_never_read(tmp_path):
    names = ["creds.toml", ".env.example", "service-creds.json", "ok.py"]
    _walk_tree(tmp_path, names)

    real_open = builtins.open
    calls = []

    def spy(*args, **kwargs):
        calls.append(args)
        return real_open(*args, **kwargs)

    builtins.open = spy
    try:
        summary = _walk_tree(tmp_path, names)
        _ = to_json(summary_result(summary)) + to_text(summary_result(summary))
    finally:
        builtins.open = real_open
    assert calls == []


def summary_result(summary):
    from agent_harness.inspection.result import InspectionResult

    return InspectionResult(
        status="ok",
        partial=False,
        repository_type="git_worktree",
        resolved_root=".",
        requested_path=str(summary.entries[0].repository_relative_path),
        file_count=summary.file_count,
        directory_count=summary.directory_count,
        total_metadata_size=summary.total_metadata_size,
        content_bytes_read=0,
        entries=summary.entries,
        language_summary=summary.language_summary,
        manifest_summary=summary.manifest_summary,
        test_directory_count=summary.test_directory_count,
        documentation_count=summary.documentation_count,
        sensitive_entries=summary.sensitive_entries,
        warnings=summary.warnings,
        limit=summary.limit,
    )