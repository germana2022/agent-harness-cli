"""Allowlist model with exact and bounded matching.

Matching is exact by default. Prefix/suffix matching is bounded to a literal
prefix or suffix with no glob or substring semantics. Deny rules take
precedence over allow rules; conflicts within the same kind are resolved by
priority, and ties are treated as ambiguous (deny).
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Iterable

from .actions import Capability
from .errors import (
    InvalidDomainValue,
    PolicyConfigurationError,
    validate_identifier,
)

_PATTERN_MAX_LENGTH = 4096


class RuleKind(Enum):
    ALLOW = "allow"
    DENY = "deny"


class MatchMode(Enum):
    EXACT = "exact"
    PREFIX = "prefix"
    SUFFIX = "suffix"


@dataclass(frozen=True)
class AllowlistRule:
    """An immutable allowlist rule."""

    rule_id: str
    kind: RuleKind
    capability: Capability
    target_pattern: str
    match_mode: MatchMode = MatchMode.EXACT
    priority: int = 0
    constraint: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "rule_id",
            self._safe_identifier(self.rule_id, "rule_id"),
        )
        if not isinstance(self.kind, RuleKind):
            raise PolicyConfigurationError("kind must be a RuleKind")
        if not isinstance(self.capability, Capability):
            raise PolicyConfigurationError("capability must be a Capability")
        if not isinstance(self.match_mode, MatchMode):
            raise PolicyConfigurationError("match_mode must be a MatchMode")
        pattern = self._safe_identifier(self.target_pattern, "target_pattern")
        if len(pattern) > _PATTERN_MAX_LENGTH:
            raise PolicyConfigurationError("target_pattern is too long")
        object.__setattr__(self, "target_pattern", pattern)
        if self.constraint is not None:
            object.__setattr__(
                self,
                "constraint",
                self._safe_identifier(self.constraint, "constraint"),
            )

    @staticmethod
    def _safe_identifier(value: object, field: str) -> str:
        try:
            return validate_identifier(value, field)
        except InvalidDomainValue as exc:
            raise PolicyConfigurationError(str(exc)) from exc


@dataclass(frozen=True)
class AllowlistMatch:
    """The result of matching an allowlist rule."""

    rule_id: str
    kind: RuleKind
    evidence: str
    ambiguous: bool = False


def _pattern_matches(pattern: str, mode: MatchMode, target: str) -> bool:
    if mode is MatchMode.EXACT:
        return target == pattern
    if mode is MatchMode.PREFIX:
        return target.startswith(pattern)
    return target.endswith(pattern)


class AllowlistEngine:
    """Deterministic allowlist matching for a fixed rule set."""

    def __init__(self, rules: Iterable[AllowlistRule] = ()) -> None:
        self._rules = tuple(rules)

    @property
    def rules(self) -> tuple[AllowlistRule, ...]:
        return self._rules

    def match(self, capability: Capability, target: str) -> AllowlistMatch | None:
        """Return the winning match for ``capability``/``target`` or ``None``.

        Deny rules win over allow rules. Within the same kind the highest
        priority wins; an allow-rule tie is reported as ``ambiguous`` (deny).
        """
        candidates = [
            rule
            for rule in self._rules
            if rule.capability is capability
            and _pattern_matches(rule.target_pattern, rule.match_mode, target)
        ]
        if not candidates:
            return None
        deny_rules = [rule for rule in candidates if rule.kind is RuleKind.DENY]
        if deny_rules:
            winner = max(deny_rules, key=lambda rule: rule.priority)
            return AllowlistMatch(
                rule_id=winner.rule_id,
                kind=RuleKind.DENY,
                evidence=f"deny rule {winner.rule_id} matched",
            )
        allow_rules = [rule for rule in candidates if rule.kind is RuleKind.ALLOW]
        top_priority = max(rule.priority for rule in allow_rules)
        winners = [rule for rule in allow_rules if rule.priority == top_priority]
        winner = winners[0]
        if len(winners) > 1:
            return AllowlistMatch(
                rule_id=winner.rule_id,
                kind=RuleKind.ALLOW,
                evidence="conflicting allow rules at equal priority",
                ambiguous=True,
            )
        return AllowlistMatch(
            rule_id=winner.rule_id,
            kind=RuleKind.ALLOW,
            evidence=f"allow rule {winner.rule_id} matched",
        )
