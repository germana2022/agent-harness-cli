"""Verify the domain package stays framework- and infrastructure-independent."""

import ast
import datetime
import pathlib

import pytest

from agent_harness.domain import (
    DEFAULT_MODE,
    ApprovalDecision,
    ApprovalRecord,
    ApprovalState,
    OperatingMode,
    TargetResource,
)

from conftest import make_action

DOMAIN_ROOT = pathlib.Path(__file__).resolve().parents[3] / "src" / "agent_harness" / "domain"

FORBIDDEN_IMPORTS = (
    "typer",
    "click",
    "pydantic",
    "pydantic_settings",
    "pytest",
    "requests",
    "httpx",
    "git",
    "github",
    "docker",
    "opencode",
    "agent_harness.cli",
    "subprocess",
    "socket",
    "os",
)


def _domain_modules():
    return sorted(DOMAIN_ROOT.glob("*.py"))


def test_domain_imports_only_stdlib_and_domain():
    for module in _domain_modules():
        if module.name == "__init__.py":
            continue
        tree = ast.parse(module.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    top = alias.name.split(".")[0]
                    if top in FORBIDDEN_IMPORTS:
                        pytest.fail(
                            f"{module.name} imports forbidden module {alias.name}"
                        )
            elif isinstance(node, ast.ImportFrom):
                if node.module is None:
                    continue
                top = node.module.split(".")[0]
                if top in FORBIDDEN_IMPORTS:
                    pytest.fail(
                        f"{module.name} imports forbidden module {node.module}"
                    )


def test_domain_has_no_framework_imports_in_init():
    tree = ast.parse((DOMAIN_ROOT / "__init__.py").read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module is not None:
            top = node.module.split(".")[0]
            assert top not in FORBIDDEN_IMPORTS, f"forbidden import {node.module}"


def test_default_mode_is_read_only():
    assert DEFAULT_MODE is OperatingMode.READ_ONLY


def test_policy_request_rejects_bad_context():
    from agent_harness.domain import PolicyRequest

    action = make_action()
    with pytest.raises(ValueError):
        PolicyRequest(
            mode=OperatingMode.READ_ONLY, action=action, context=["not-a-tuple"]
        )


def test_domain_objects_repr_do_not_expose_sensitive_values():
    record = ApprovalRecord(
        approval_id="appr-1",
        request_id="req-1",
        decision=ApprovalDecision.APPROVED,
        scope="scope-1",
        action=make_action(),
        target=TargetResource(ref="repo:main:src/lib.py"),
        required_mode=OperatingMode.WORKSPACE_WRITE,
        approver="human",
        decided_at=datetime.datetime(2026, 1, 1, tzinfo=datetime.timezone.utc),
        expires_at=None,
        state=ApprovalState.APPROVED,
    )
    text = repr(record)
    assert "secret" not in text.lower()
    assert "password" not in text.lower()
