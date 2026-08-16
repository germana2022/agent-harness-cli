from agent_harness.domain import (
    DEFAULT_MODE,
    ActionCategory,
    OperatingMode,
    mode_allows_category,
    mode_requires_approval,
)

MODES = (
    OperatingMode.READ_ONLY,
    OperatingMode.WORKSPACE_WRITE,
    OperatingMode.DELIVERY,
)

CATEGORIES = (
    ActionCategory.READ,
    ActionCategory.LOCAL_WRITE,
    ActionCategory.EXECUTION,
    ActionCategory.GIT_MUTATION,
    ActionCategory.EXTERNAL,
    ActionCategory.DESTRUCTIVE,
)


def test_default_mode_is_read_only():
    assert DEFAULT_MODE is OperatingMode.READ_ONLY


def test_exact_mode_names():
    assert {mode.value for mode in MODES} == {
        "read_only",
        "workspace_write",
        "delivery",
    }


def test_read_allowed_in_all_modes():
    for mode in MODES:
        assert mode_allows_category(mode, ActionCategory.READ) is True


def test_read_only_denies_all_non_read():
    for category in CATEGORIES:
        if category is not ActionCategory.READ:
            assert mode_allows_category(OperatingMode.READ_ONLY, category) is False


def test_workspace_write_allows_local_but_not_external():
    for category in (
        ActionCategory.LOCAL_WRITE,
        ActionCategory.EXECUTION,
        ActionCategory.GIT_MUTATION,
    ):
        assert mode_allows_category(OperatingMode.WORKSPACE_WRITE, category) is True
    assert mode_allows_category(OperatingMode.WORKSPACE_WRITE, ActionCategory.EXTERNAL) is False
    assert (
        mode_allows_category(OperatingMode.WORKSPACE_WRITE, ActionCategory.DESTRUCTIVE)
        is False
    )


def test_delivery_allows_all_categories():
    for category in CATEGORIES:
        assert mode_allows_category(OperatingMode.DELIVERY, category) is True


def test_external_and_destructive_only_in_delivery():
    for category in (ActionCategory.EXTERNAL, ActionCategory.DESTRUCTIVE):
        assert mode_allows_category(OperatingMode.READ_ONLY, category) is False
        assert mode_allows_category(OperatingMode.WORKSPACE_WRITE, category) is False
        assert mode_allows_category(OperatingMode.DELIVERY, category) is True


def test_mode_requires_approval_for_external_and_destructive_everywhere():
    for mode in MODES:
        assert mode_requires_approval(mode, ActionCategory.EXTERNAL) is True
        assert mode_requires_approval(mode, ActionCategory.DESTRUCTIVE) is True


def test_delivery_requires_approval_for_local_mutations():
    for category in (
        ActionCategory.LOCAL_WRITE,
        ActionCategory.EXECUTION,
        ActionCategory.GIT_MUTATION,
    ):
        assert mode_requires_approval(OperatingMode.DELIVERY, category) is True


def test_workspace_write_does_not_force_approval_for_local_mutations():
    for category in (
        ActionCategory.LOCAL_WRITE,
        ActionCategory.EXECUTION,
        ActionCategory.GIT_MUTATION,
    ):
        assert mode_requires_approval(OperatingMode.WORKSPACE_WRITE, category) is False


def test_read_never_requires_approval():
    for mode in MODES:
        assert mode_requires_approval(mode, ActionCategory.READ) is False
