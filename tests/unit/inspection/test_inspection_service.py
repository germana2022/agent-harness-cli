import pytest

from agent_harness.application.inspection_service import InspectionService
from agent_harness.domain import AllowlistEngine, UtcClock
from agent_harness.domain.policy import DefaultPolicyEngine
from agent_harness.inspection import InspectionRequest
from agent_harness.inspection.errors import PolicyDeniedError
from agent_harness.inspection.result import GitInfo


@pytest.fixture
def policy_engine():
    return DefaultPolicyEngine(clock=UtcClock(), allowlist=AllowlistEngine())


def make_service(policy_engine, inspector=None, git_reader=None, resolver=None):
    return InspectionService(
        inspector=inspector or _spy_inspector(_walk()),
        git_reader=git_reader or _spy_git(GitInfo()),
        policy_engine=policy_engine,
        resolver=resolver,
    )


def _spy_inspector(walk):
    class SpyInspector:
        def __init__(self):
            self.called = False
            self.root = None

        def inspect(self, root, request):
            self.called = True
            self.root = root
            return walk

    return SpyInspector()


def _spy_git(info):
    class SpyGit:
        def __init__(self):
            self.called = False
            self.root = None

        def read(self, root):
            self.called = True
            self.root = root
            return info

    return SpyGit()


def _walk(entries=(), **kwargs):
    from agent_harness.infrastructure.inspector import WalkSummary

    return WalkSummary(
        entries=entries,
        file_count=len(entries),
        directory_count=0,
        total_metadata_size=0,
        language_summary=(),
        manifest_summary=(),
        test_directory_count=0,
        documentation_count=0,
        exclusion_summary=(),
        sensitive_entries=0,
        warnings=(),
        **kwargs,
    )


def test_orchestration_order(tmp_path, policy_engine):
    inspector = _spy_inspector(_walk())
    git = _spy_git(GitInfo(branch="main"))
    service = make_service(
        policy_engine,
        inspector=inspector,
        git_reader=git,
        resolver=lambda p: (tmp_path, "git_worktree"),
    )
    result = service.inspect(InspectionRequest(git_metadata="auto"))
    assert inspector.called is True
    assert git.called is True
    assert result.repository_type == "git_worktree"
    assert result.git.branch == "main"


def test_policy_denied_prevents_traversal(tmp_path, policy_engine):
    inspector = _spy_inspector(_walk())
    service = make_service(
        policy_engine,
        inspector=inspector,
        resolver=lambda p: (tmp_path, "directory"),
    )

    def deny(_root):
        raise PolicyDeniedError("policy denied inspection")

    service._assert_allowed = deny
    try:
        service.inspect(InspectionRequest())
    except PolicyDeniedError:
        pass
    else:
        raise AssertionError("expected PolicyDeniedError")
    assert inspector.called is False


def test_git_off_skips_adapter(tmp_path, policy_engine):
    git = _spy_git(GitInfo(branch="main"))
    service = make_service(
        policy_engine,
        git_reader=git,
        resolver=lambda p: (tmp_path, "git_worktree"),
    )
    result = service.inspect(InspectionRequest(git_metadata="off"))
    assert git.called is False
    assert result.git is None


def test_git_unavailable_adds_warning(tmp_path, policy_engine):
    git = _spy_git(None)
    service = make_service(
        policy_engine,
        git_reader=git,
        resolver=lambda p: (tmp_path, "git_worktree"),
    )
    result = service.inspect(InspectionRequest(git_metadata="auto"))
    assert any(w.code == "GIT_METADATA_UNAVAILABLE" for w in result.warnings)


def test_non_git_directory_no_git_adapter(tmp_path, policy_engine):
    git = _spy_git(GitInfo(branch="main"))
    service = make_service(
        policy_engine,
        git_reader=git,
        resolver=lambda p: (tmp_path, "directory"),
    )
    result = service.inspect(InspectionRequest(git_metadata="auto"))
    assert git.called is False
    assert result.repository_type == "directory"
    assert result.git is None


def test_partial_result(tmp_path, policy_engine):
    from agent_harness.inspection.result import LimitInfo

    walk = _walk(limit=LimitInfo("LIMIT_ENTRIES_EXCEEDED", 1, 2))
    inspector = _spy_inspector(walk)
    service = make_service(
        policy_engine,
        inspector=inspector,
        resolver=lambda p: (tmp_path, "directory"),
    )
    result = service.inspect(InspectionRequest(git_metadata="off"))
    assert result.partial is True
    assert result.status == "partial"
    assert result.limit.code == "LIMIT_ENTRIES_EXCEEDED"


def test_no_private_cli_dependency(tmp_path, policy_engine):
    service = make_service(policy_engine, resolver=lambda p: (tmp_path, "directory"))
    assert isinstance(service, InspectionService)


class _DenyingEngine:
    def decide(self, request):
        from agent_harness.domain import PolicyDecision, PolicyReasonCode

        return PolicyDecision(
            allowed=False,
            reason_code=PolicyReasonCode.MODE_PROHIBITS_ACTION,
            message="denied",
            approval_required=False,
        )


def test_real_policy_denial_raises_before_traversal(tmp_path):
    from agent_harness.infrastructure.inspector import Inspector

    inspector = _spy_inspector(_walk())
    service = InspectionService(
        inspector=inspector,
        git_reader=_spy_git(None),
        policy_engine=_DenyingEngine(),
        resolver=lambda p: (tmp_path, "directory"),
    )
    try:
        service.inspect(InspectionRequest(git_metadata="off"))
    except PolicyDeniedError as exc:
        assert "denied" in str(exc)
    else:
        raise AssertionError("expected PolicyDeniedError")
    assert inspector.called is False
