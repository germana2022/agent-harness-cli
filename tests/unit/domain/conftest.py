"""Shared fixtures and factories for Phase 2 domain tests."""

import datetime

import pytest

from agent_harness.domain import (
    CAPABILITY_CATEGORY,
    ActionName,
    AllowlistEngine,
    Capability,
    DefaultPolicyEngine,
    FixedClock,
    TargetResource,
)

START = datetime.datetime(2026, 1, 1, tzinfo=datetime.timezone.utc)


@pytest.fixture
def clock() -> FixedClock:
    return FixedClock(START)


@pytest.fixture
def engine(clock: FixedClock) -> DefaultPolicyEngine:
    return DefaultPolicyEngine(clock=clock, allowlist=AllowlistEngine())


def make_target(ref: str = "repo:main:src/lib.py") -> TargetResource:
    return TargetResource(ref=ref)


def make_action(
    capability: Capability = Capability.ALLOWED_FILE_READ,
    target: TargetResource | None = None,
) -> ActionName:
    return ActionName(
        capability=capability,
        category=CAPABILITY_CATEGORY[capability],
        target=target if target is not None else make_target(),
    )
