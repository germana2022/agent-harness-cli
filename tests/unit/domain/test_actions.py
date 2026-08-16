import pytest

from agent_harness.domain import (
    CAPABILITY_CATEGORY,
    ActionCategory,
    ActionName,
    Capability,
    TargetResource,
)
from agent_harness.domain.errors import InvalidDomainValue


def test_every_capability_has_a_mapped_category():
    assert set(CAPABILITY_CATEGORY) == set(Capability)
    assert set(CAPABILITY_CATEGORY.values()) == set(ActionCategory)


def test_action_name_valid_construction():
    target = TargetResource(ref="repo:main:src/lib.py")
    action = ActionName(
        capability=Capability.EXACT_SEARCH,
        category=ActionCategory.READ,
        target=target,
    )
    assert action.capability is Capability.EXACT_SEARCH
    assert action.category is ActionCategory.READ
    assert action.target is target


def test_action_name_wrong_category_rejected():
    target = TargetResource(ref="repo:main:src/lib.py")
    with pytest.raises(InvalidDomainValue):
        ActionName(
            capability=Capability.EXACT_SEARCH,
            category=ActionCategory.EXTERNAL,
            target=target,
        )


def test_action_name_rejects_non_enum():
    target = TargetResource(ref="x")
    with pytest.raises(InvalidDomainValue):
        ActionName(capability="bad", category=ActionCategory.READ, target=target)
    with pytest.raises(InvalidDomainValue):
        ActionName(
            capability=Capability.EXACT_SEARCH, category="bad", target=target
        )


def test_action_name_rejects_invalid_target():
    with pytest.raises(InvalidDomainValue):
        ActionName(
            capability=Capability.EXACT_SEARCH,
            category=ActionCategory.READ,
            target="not-a-target",
        )


def test_target_resource_normalizes_whitespace_and_control():
    target = TargetResource(ref="  repo:main  ", resource_type="  target  ")
    assert target.ref == "repo:main"
    assert target.resource_type == "target"


def test_target_resource_rejects_empty():
    with pytest.raises(InvalidDomainValue):
        TargetResource(ref="   ")
    with pytest.raises(InvalidDomainValue):
        TargetResource(ref="\x1b")


def test_action_name_is_immutable():
    target = TargetResource(ref="repo:main:src/lib.py")
    action = ActionName(
        capability=Capability.EXACT_SEARCH,
        category=ActionCategory.READ,
        target=target,
    )
    with pytest.raises(Exception):
        action.category = ActionCategory.EXTERNAL  # type: ignore[misc]


def test_target_resource_is_immutable():
    target = TargetResource(ref="repo:main:src/lib.py")
    with pytest.raises(Exception):
        target.ref = "other"  # type: ignore[misc]
