import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest
from typer.testing import CliRunner

from agent_harness.cli import app
from agent_harness.infrastructure.inspector import resolve_inspection_root
from agent_harness.inspection.request import HARD_MAX_DEPTH, HARD_MAX_ENTRIES

runner = CliRunner()


def invoke(*args):
    return runner.invoke(app, list(args))


@pytest.fixture
def git_repo(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / ".git").mkdir()
    (repo / "a.py").write_text("print(1)")
    (repo / "b.go").write_text("package main")
    (repo / "README.md").write_text("readme")
    return repo


@pytest.fixture
def non_git_dir(tmp_path):
    """Return a directory that is not inside any git repository."""
    probe = None
    try:
        probe = Path(tempfile.mkdtemp(dir=str(tmp_path)))
    except OSError:
        pass
    if probe is not None:
        root, _ = resolve_inspection_root(str(probe))
        if root == probe:
            yield probe
            shutil.rmtree(probe, ignore_errors=True)
            return
        shutil.rmtree(probe, ignore_errors=True)
    if os.name == "nt":
        try:
            probe = Path(tempfile.mkdtemp(dir="D:/"))
        except OSError:
            pytest.skip("no writable non-Git directory available")
        root, _ = resolve_inspection_root(str(probe))
        if root == probe:
            yield probe
            shutil.rmtree(probe, ignore_errors=True)
            return
        shutil.rmtree(probe, ignore_errors=True)
    pytest.skip("no writable non-Git directory available")


def test_inspect_help():
    result = invoke("inspect", "--help")
    assert result.exit_code == 0
    assert "--path" in result.stdout
    assert "--max-entries" in result.stdout


def test_inspect_json_git_repo(git_repo):
    result = invoke("--output", "json", "inspect", "--path", str(git_repo), "--no-git")
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["schema_version"] == 1
    assert payload["status"] == "ok"
    assert payload["repository_type"] == "git_worktree"
    assert payload["file_count"] == 3
    assert payload["content_bytes_read"] == 0
    assert "\x1b" not in result.stdout


def test_inspect_text_git_repo(git_repo):
    result = invoke("inspect", "--path", str(git_repo), "--no-git")
    assert result.exit_code == 0
    assert "Files: 3" in result.stdout
    assert "Repository type: git_worktree" in result.stdout


def test_inspect_non_git_directory(non_git_dir):
    result = invoke("--output", "json", "inspect", "--path", str(non_git_dir), "--no-git")
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["repository_type"] == "directory"


def test_inspect_default_path_is_project_repo():
    result = invoke("--output", "json", "inspect", "--no-git")
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["repository_type"] == "git_worktree"
    assert payload["file_count"] > 0


def test_inspect_missing_path(tmp_path):
    result = invoke("inspect", "--path", str(tmp_path / "missing"))
    assert result.exit_code == 2
    assert "path not found" in result.stderr
    assert "Traceback" not in result.stderr


def test_inspect_file_path(tmp_path):
    target = tmp_path / "f.txt"
    target.write_text("x")
    result = invoke("inspect", "--path", str(target))
    assert result.exit_code == 2
    assert "not a directory" in result.stderr


@pytest.mark.parametrize("value", [0, -1, HARD_MAX_ENTRIES + 1])
def test_invalid_max_entries(value, git_repo):
    result = invoke("inspect", "--path", str(git_repo), "--max-entries", str(value))
    assert result.exit_code == 2
    assert "invalid --max-entries" in result.stderr


@pytest.mark.parametrize("value", [0, -1, HARD_MAX_DEPTH + 1])
def test_invalid_max_depth(value, git_repo):
    result = invoke("inspect", "--path", str(git_repo), "--max-depth", str(value))
    assert result.exit_code == 2
    assert "invalid --max-depth" in result.stderr


def test_partial_limit_exit_zero(git_repo):
    result = invoke("--output", "json", "inspect", "--path", str(git_repo), "--max-entries", "1")
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["status"] == "partial"
    assert payload["partial"] is True
    assert payload["limit"]["code"] == "LIMIT_ENTRIES_EXCEEDED"


@pytest.fixture
def real_git_repo(tmp_path):
    repo = tmp_path / "real"
    repo.mkdir()
    env = dict(os.environ)
    env["GIT_AUTHOR_NAME"] = "Test"
    env["GIT_AUTHOR_EMAIL"] = "test@example.com"
    env["GIT_COMMITTER_NAME"] = "Test"
    env["GIT_COMMITTER_EMAIL"] = "test@example.com"
    subprocess.run(["git", "init", "-q"], cwd=str(repo), env=env, check=True)
    subprocess.run(
        ["git", "config", "user.email", "test@example.com"], cwd=str(repo), env=env, check=True
    )
    subprocess.run(
        ["git", "config", "user.name", "Test"], cwd=str(repo), env=env, check=True
    )
    (repo / "a.py").write_text("print(1)")
    subprocess.run(["git", "add", "a.py"], cwd=str(repo), env=env, check=True)
    subprocess.run(
        ["git", "commit", "-q", "-m", "init"], cwd=str(repo), env=env, check=True
    )
    return repo


def test_git_metadata_success(real_git_repo):
    result = invoke("--output", "json", "inspect", "--path", str(real_git_repo), "--git")
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["repository_type"] == "git_worktree"
    assert "git" in payload
    assert payload["git"]["commit"]
    assert "branch" in payload["git"]
    assert payload["git"]["dirty"] is False


def test_no_git_no_warning(git_repo):
    result = invoke("--output", "json", "inspect", "--path", str(git_repo), "--no-git")
    payload = json.loads(result.stdout)
    assert payload.get("warnings") is None
    assert "git" not in payload


def test_deterministic_output(git_repo):
    first = invoke("--output", "json", "inspect", "--path", str(git_repo), "--no-git")
    second = invoke("--output", "json", "inspect", "--path", str(git_repo), "--no-git")
    assert first.stdout == second.stdout


def test_json_has_no_absolute_paths(git_repo):
    result = invoke("--output", "json", "inspect", "--path", str(git_repo), "--no-git")
    assert str(git_repo) not in result.stdout
    assert ":/" not in result.stdout


def test_sensitive_names_redacted_in_cli(tmp_path):
    repo = tmp_path / "sensitive"
    repo.mkdir()
    (repo / ".git").mkdir()
    (repo / "secrets.json").write_text("{}")
    (repo / "ok.py").write_text("x")
    result = invoke("--output", "json", "inspect", "--path", str(repo), "--no-git")
    assert result.exit_code == 0
    assert "secrets.json" not in result.stdout
    assert "<sensitive-1>" in result.stdout


def test_cred_names_redacted_in_cli(tmp_path):
    repo = tmp_path / "creds"
    repo.mkdir()
    (repo / ".git").mkdir()
    (repo / "creds.toml").write_text("{}")
    (repo / "service-creds.json").write_text("{}")
    (repo / "ok.py").write_text("x")
    result = invoke("--output", "json", "inspect", "--path", str(repo), "--no-git")
    assert result.exit_code == 0
    assert "creds.toml" not in result.stdout
    assert "service-creds.json" not in result.stdout
    payload = json.loads(result.stdout)
    redacted = [e["repository_relative_path"] for e in payload["entries"] if e["redacted"]]
    assert len(redacted) >= 1
    assert all(path.startswith("<sensitive-") for path in redacted)
    assert payload["sensitive_entries"] >= 1


def test_accredited_visible_in_cli(tmp_path):
    repo = tmp_path / "visible"
    repo.mkdir()
    (repo / ".git").mkdir()
    (repo / "accredited.py").write_text("x")
    (repo / "credit.py").write_text("x")
    result = invoke("--output", "json", "inspect", "--path", str(repo), "--no-git")
    assert result.exit_code == 0
    assert "accredited.py" in result.stdout
    assert "credit.py" in result.stdout
    payload = json.loads(result.stdout)
    assert all(not e["redacted"] for e in payload["entries"])


def test_stdout_stderr_separation(git_repo):
    result = invoke("inspect", "--path", str(git_repo), "--no-git")
    assert result.exit_code == 0
    assert result.stdout
    assert result.stderr == ""


def test_internal_error_exit_10(git_repo, monkeypatch):
    import agent_harness.cli as cli

    def broken_service():
        raise RuntimeError("boom")

    monkeypatch.setattr(cli, "_inspection_service", broken_service)
    result = invoke("inspect", "--path", str(git_repo))
    assert result.exit_code == 10
    assert "unexpected internal error" in result.stderr


def test_permission_denied_exit_3(git_repo, monkeypatch):
    import agent_harness.cli as cli
    from agent_harness.inspection.errors import PermissionDeniedError

    def service():
        raise PermissionDeniedError("permission denied")

    monkeypatch.setattr(cli, "_inspection_service", service)
    result = invoke("inspect", "--path", str(git_repo))
    assert result.exit_code == 3
    assert "permission denied" in result.stderr


def test_link_error_exit_10(git_repo, monkeypatch):
    import agent_harness.cli as cli
    from agent_harness.inspection.errors import LinkEncounteredError

    def service():
        raise LinkEncounteredError("link")

    monkeypatch.setattr(cli, "_inspection_service", service)
    result = invoke("inspect", "--path", str(git_repo))
    assert result.exit_code == 10


def test_typer_exit_propagates(git_repo, monkeypatch):
    import typer

    import agent_harness.cli as cli

    def service():
        raise typer.Exit(code=7)

    monkeypatch.setattr(cli, "_inspection_service", service)
    result = invoke("inspect", "--path", str(git_repo))
    assert result.exit_code == 7


def test_keyboard_interrupt_not_swallowed(git_repo, monkeypatch):
    import agent_harness.cli as cli

    def service():
        raise KeyboardInterrupt()

    monkeypatch.setattr(cli, "_inspection_service", service)
    result = invoke("inspect", "--path", str(git_repo))
    assert result.exit_code != 10
    assert "unexpected internal error" not in result.stderr


def test_phase1_regression():
    result = invoke("version")
    assert result.exit_code == 0
    assert result.stdout.strip() == "agent-harness 0.1.0"
    result = invoke("config-check")
    assert result.exit_code == 0
    assert "configuration: valid" in result.stdout


def test_module_execution_parity(git_repo):
    clean_env = {
        key: value
        for key, value in os.environ.items()
        if not key.startswith("AGENT_HARNESS_")
    }
    proc = subprocess.run(
        [sys.executable, "-m", "agent_harness", "inspect", "--path", str(git_repo), "--no-git"],
        capture_output=True,
        text=True,
        env=clean_env,
    )
    assert proc.returncode == 0
    assert "Files: 3" in proc.stdout
