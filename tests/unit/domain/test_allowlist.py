import pytest

from agent_harness.domain import (
    AllowlistEngine,
    AllowlistRule,
    Capability,
    MatchMode,
    RuleKind,
)
from agent_harness.domain.errors import PolicyConfigurationError


def rule(
    rule_id="r1",
    kind=RuleKind.ALLOW,
    capability=Capability.LOCAL_WORKSPACE_WRITE,
    pattern="repo:main:",
    mode=MatchMode.PREFIX,
    priority=0,
    constraint=None,
):
    return AllowlistRule(
        rule_id=rule_id,
        kind=kind,
        capability=capability,
        target_pattern=pattern,
        match_mode=mode,
        priority=priority,
        constraint=constraint,
    )


def test_exact_match():
    rules = [
        rule(
            rule_id="exact",
            pattern="repo:main:src/lib.py",
            mode=MatchMode.EXACT,
        )
    ]
    match = AllowlistEngine(rules).match(
        Capability.LOCAL_WORKSPACE_WRITE, "repo:main:src/lib.py"
    )
    assert match is not None
    assert match.rule_id == "exact"
    assert match.kind is RuleKind.ALLOW
    assert match.ambiguous is False


def test_exact_non_match_returns_none():
    rules = [rule(rule_id="exact", pattern="a.py", mode=MatchMode.EXACT)]
    assert AllowlistEngine(rules).match(Capability.LOCAL_WORKSPACE_WRITE, "b.py") is None


def test_prefix_match():
    rules = [rule(rule_id="pre", pattern="repo:main:src/", mode=MatchMode.PREFIX)]
    match = AllowlistEngine(rules).match(
        Capability.LOCAL_WORKSPACE_WRITE, "repo:main:src/foo.py"
    )
    assert match is not None and match.rule_id == "pre"


def test_prefix_requires_actual_prefix():
    rules = [rule(rule_id="pre", pattern="repo:main:src/", mode=MatchMode.PREFIX)]
    assert (
        AllowlistEngine(rules).match(Capability.LOCAL_WORKSPACE_WRITE, "repo:main:lib/") is None
    )


def test_suffix_match():
    rules = [rule(rule_id="suf", pattern="_tests.py", mode=MatchMode.SUFFIX)]
    match = AllowlistEngine(rules).match(
        Capability.LOCAL_WORKSPACE_WRITE, "repo:main:test_thing_tests.py"
    )
    assert match is not None and match.rule_id == "suf"


def test_suffix_requires_actual_suffix():
    rules = [rule(rule_id="suf", pattern="_tests.py", mode=MatchMode.SUFFIX)]
    assert (
        AllowlistEngine(rules).match(
            Capability.LOCAL_WORKSPACE_WRITE, "repo:main:tests_thing.py"
        )
        is None
    )


def test_deny_rule_takes_precedence():
    rules = [
        rule(rule_id="allow", pattern="repo:main:", mode=MatchMode.PREFIX, priority=10),
        rule(
            rule_id="deny",
            kind=RuleKind.DENY,
            pattern="repo:main:src/secret",
            mode=MatchMode.PREFIX,
        ),
    ]
    match = AllowlistEngine(rules).match(
        Capability.LOCAL_WORKSPACE_WRITE, "repo:main:src/secret/x"
    )
    assert match is not None
    assert match.kind is RuleKind.DENY
    assert match.rule_id == "deny"


def test_deny_tie_is_deterministic_deny():
    rules = [
        rule(rule_id="deny-a", kind=RuleKind.DENY, pattern="repo:main:", priority=3),
        rule(rule_id="deny-b", kind=RuleKind.DENY, pattern="repo:main:src", priority=3),
    ]
    engine = AllowlistEngine(rules)
    first = engine.match(Capability.LOCAL_WORKSPACE_WRITE, "repo:main:src/x")
    second = engine.match(Capability.LOCAL_WORKSPACE_WRITE, "repo:main:src/x")
    assert first is not None and first.kind is RuleKind.DENY
    assert first == second


def test_allow_conflict_at_equal_priority_is_ambiguous():
    rules = [
        rule(rule_id="allow-a", pattern="repo:main:", priority=5),
        rule(rule_id="allow-b", pattern="repo:main:src", priority=5),
    ]
    match = AllowlistEngine(rules).match(
        Capability.LOCAL_WORKSPACE_WRITE, "repo:main:src/x"
    )
    assert match is not None
    assert match.ambiguous is True
    assert "conflicting" in match.evidence


def test_higher_priority_allow_wins():
    rules = [
        rule(rule_id="low", pattern="repo:main:", priority=1),
        rule(rule_id="high", pattern="repo:main:", priority=9),
    ]
    match = AllowlistEngine(rules).match(
        Capability.LOCAL_WORKSPACE_WRITE, "repo:main:src/x"
    )
    assert match is not None
    assert match.rule_id == "high"
    assert match.ambiguous is False


def test_capability_is_scoped():
    rules = [rule(rule_id="only-local", pattern="repo:main:", mode=MatchMode.PREFIX)]
    engine = AllowlistEngine(rules)
    assert (
        engine.match(Capability.EXTERNAL_PUSH, "repo:main:src/x")
        is None
    )
    assert (
        engine.match(Capability.LOCAL_WORKSPACE_WRITE, "repo:main:src/x")
        is not None
    )


def test_empty_allowlist_returns_none():
    assert AllowlistEngine().match(Capability.LOCAL_WORKSPACE_WRITE, "anything") is None


def test_rules_property_exposes_fixed_rules():
    rules = [rule(rule_id="r1", pattern="repo:main:")]
    engine = AllowlistEngine(rules)
    assert engine.rules == (rules[0],)


def test_malformed_rule_rejected():
    with pytest.raises(PolicyConfigurationError):
        AllowlistRule(
            rule_id="",
            kind=RuleKind.ALLOW,
            capability=Capability.LOCAL_WORKSPACE_WRITE,
            target_pattern="x",
        )
    with pytest.raises(PolicyConfigurationError):
        AllowlistRule(
            rule_id="r",
            kind=RuleKind.ALLOW,
            capability=Capability.LOCAL_WORKSPACE_WRITE,
            target_pattern="   ",
        )
    with pytest.raises(PolicyConfigurationError):
        AllowlistRule(
            rule_id="r",
            kind="bad",
            capability=Capability.LOCAL_WORKSPACE_WRITE,
            target_pattern="x",
        )
    with pytest.raises(PolicyConfigurationError):
        AllowlistRule(
            rule_id="r",
            kind=RuleKind.ALLOW,
            capability="bad",
            target_pattern="x",
        )
    with pytest.raises(PolicyConfigurationError):
        AllowlistRule(
            rule_id="r",
            kind=RuleKind.ALLOW,
            capability=Capability.LOCAL_WORKSPACE_WRITE,
            target_pattern="x",
            match_mode="bad",
        )


def test_overlong_pattern_rejected():
    with pytest.raises(PolicyConfigurationError):
        AllowlistRule(
            rule_id="r",
            kind=RuleKind.ALLOW,
            capability=Capability.LOCAL_WORKSPACE_WRITE,
            target_pattern="x" * 5000,
        )


def test_rule_with_constraint_is_accepted():
    r = rule(rule_id="constrained", pattern="repo:main:", constraint="lock=1")
    assert r.constraint == "lock=1"


def test_rule_rejects_empty_constraint():
    with pytest.raises(PolicyConfigurationError):
        rule(rule_id="c", pattern="repo:main:", constraint="   ")


def test_control_characters_stripped_from_pattern():
    r = AllowlistRule(
        rule_id="r",
        kind=RuleKind.ALLOW,
        capability=Capability.LOCAL_WORKSPACE_WRITE,
        target_pattern="  repo\x1b[31mmain:  ",
    )
    assert "\x1b" not in r.target_pattern
    assert r.target_pattern == "repo[31mmain:"
