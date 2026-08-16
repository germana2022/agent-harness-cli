import datetime

import pytest

from agent_harness.domain import FixedClock, UtcClock
from agent_harness.domain.errors import InvalidDomainValue

TZ = datetime.timezone.utc
NOW = datetime.datetime(2026, 1, 1, tzinfo=TZ)


def test_utc_clock_returns_aware_utc():
    stamp = UtcClock().now()
    assert stamp.tzinfo is not None
    assert stamp.utcoffset() == datetime.timedelta(0)


def test_fixed_clock_returns_start():
    clock = FixedClock(NOW)
    assert clock.now() == NOW


def test_fixed_clock_advances():
    clock = FixedClock(NOW)
    clock.advance(datetime.timedelta(minutes=5))
    assert clock.now() == NOW + datetime.timedelta(minutes=5)


def test_fixed_clock_rejects_naive_start():
    with pytest.raises(InvalidDomainValue):
        FixedClock(datetime.datetime(2026, 1, 1))


def test_fixed_clock_advance_is_deterministic():
    clock = FixedClock(NOW)
    values = [clock.now() for _ in range(3)]
    assert values[0] == values[1] == values[2]


def test_clock_is_injectable_into_manager(clock):
    from agent_harness.domain import ApprovalDecision, ApprovalRequest, InMemoryApprovalManager, OperatingMode
    from conftest import make_action

    action = make_action()
    request = ApprovalRequest(
        request_id="clock-req",
        action=action,
        target=action.target,
        required_mode=OperatingMode.WORKSPACE_WRITE,
        current_mode=OperatingMode.READ_ONLY,
        scope="scope",
        requesting_component="tests",
        rationale="test",
        created_at=clock.now(),
    )
    manager = InMemoryApprovalManager(clock)
    manager.request(request)
    record = manager.record_decision(
        "clock-req", ApprovalDecision.APPROVED, "human", "ok"
    )
    assert record.decided_at == clock.now()
