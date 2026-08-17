import os
from pathlib import Path

import pytest

from agent_harness.infrastructure.inspector import (
    Inspector,
    _contains_link_component,
    resolve_inspection_root,
)
from agent_harness.inspection.errors import (
    PathEscapeError,
    PathNotDirectoryError,
    PathNotFoundError,
)
from agent_harness.inspection.request import InspectionRequest
from agent_harness.inspection.result import EntryKind, LimitInfo, WarningRecord

NO_MARKER = lambda _path: False  # noqa: E731


def _redact_path(path, index):
    return Inspector._redact_path(path, index)


def _relative_path(path, root):
    return Inspector._relative_path(path, root)


def _walk(root, **kwargs):
    return Inspector().inspect(root, InspectionRequest(**kwargs))


def test_classify_languages():
    cases = {
        "a.py": "python",
        "b.ts": "typescript",
        "c.js": "javascript",
        "d.go": "go",
        "e.rs": "rust",
        "f.md": "markdown",
        "g.yaml": "yaml",
        "h.toml": "toml",
        "i.unknownxyz": "unknown",
        "logo.png": "binary",
        "app.min.js": "javascript",
    }
    for name, expected in cases.items():
        classification, is_manifest, _ = Inspector._classify_file(name)
        assert classification == expected, name
        assert is_manifest is False


def test_classify_exact_filenames():
    assert Inspector._classify_file("Dockerfile") == ("manifest", True, "container")
    assert Inspector._classify_file("README.md")[0] == "documentation"
    assert Inspector._classify_file("LICENSE")[0] == "license"
    assert Inspector._classify_file("Makefile")[0] == "makefile"
    assert Inspector._classify_file("Justfile")[0] == "justfile"


def test_classify_manifests():
    assert Inspector._classify_file("pyproject.toml") == ("manifest", True, "python")
    assert Inspector._classify_file("package.json") == ("manifest", True, "javascript")
    assert Inspector._classify_file("requirements-dev.txt") == ("manifest", True, "python")
    assert Inspector._classify_file("app.csproj") == ("manifest", True, "dotnet")
    assert Inspector._classify_file("main.tf") == ("manifest", True, "terraform")
    assert Inspector._classify_file("docker-compose.yml") == ("manifest", True, "container")
    assert Inspector._classify_file("go.mod") == ("manifest", True, "go")


def test_sensitive_names():
    for name in (".env", ".env.local", "id_rsa", "server.key", "credentials.json", "secrets.json", "cert.pem"):
        assert Inspector._is_sensitive_name(name), name
    for name in ("tokenizer.py", "keyboard.py", "token.py", "README.md", "pem_builder.py"):
        assert not Inspector._is_sensitive_name(name), name


def test_redact_path():
    assert _redact_path(".env", 1) == "<sensitive-1>"
    assert _redact_path("config/.env", 2) == "config/<sensitive-2>"


def test_relative_path(tmp_path):
    root = tmp_path
    assert _relative_path(str(root / "a" / "b.py"), root) == "a/b.py"
    assert _relative_path(str(root / "top.py"), root) == "top.py"


def test_contains_link_component_rejects_link(tmp_path):
    target = tmp_path / "target"
    target.mkdir()
    link = tmp_path / "link"
    if os.name == "nt":
        pytest.skip("symlink creation requires privileges on Windows")
    link.symlink_to(target, target_is_directory=True)
    assert _contains_link_component(link) is True


def test_resolve_missing_path(tmp_path):
    with pytest.raises(PathNotFoundError):
        resolve_inspection_root(str(tmp_path / "does-not-exist"))


def test_resolve_file_path(tmp_path):
    file_path = tmp_path / "f.txt"
    file_path.write_text("x")
    with pytest.raises(PathNotDirectoryError):
        resolve_inspection_root(str(file_path))


def test_resolve_git_worktree_dir_marker(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / ".git").mkdir()
    root, repo_type = resolve_inspection_root(str(repo))
    assert root == repo
    assert repo_type == "git_worktree"


def test_resolve_git_worktree_file_marker(tmp_path):
    repo = tmp_path / "repo2"
    repo.mkdir()
    (repo / ".git").write_text("gitdir: ../.git-worktrees/repo2\n")
    root, repo_type = resolve_inspection_root(str(repo))
    assert root == repo
    assert repo_type == "git_worktree"


def test_resolve_nested_path_inside_repo(tmp_path):
    repo = tmp_path / "repo3"
    sub = repo / "src" / "deep"
    sub.mkdir(parents=True)
    (repo / ".git").mkdir()
    root, repo_type = resolve_inspection_root(str(sub))
    assert root == repo
    assert repo_type == "git_worktree"


def test_resolve_bare_repository(tmp_path):
    bare = tmp_path / "bare.git"
    bare.mkdir()
    (bare / "HEAD").write_text("ref: refs/heads/main\n")
    (bare / "objects").mkdir()
    (bare / "refs").mkdir()
    (bare / "config").write_text("[core]\n\tbare = true\n")
    root, repo_type = resolve_inspection_root(str(bare))
    assert repo_type == "git_bare"


def test_resolve_non_git_directory(tmp_path):
    root, repo_type = resolve_inspection_root(str(tmp_path), marker_exists=NO_MARKER)
    assert root == tmp_path
    assert repo_type == "directory"


def test_resolve_path_traversing_link_rejected(tmp_path):
    if os.name == "nt":
        pytest.skip("symlink creation requires privileges on Windows")
    target = tmp_path / "outside"
    target.mkdir()
    (target / ".git").mkdir()
    link = tmp_path / "linked"
    link.symlink_to(target, target_is_directory=True)
    with pytest.raises(PathEscapeError):
        resolve_inspection_root(str(link))


class FakeStat:
    def __init__(self, size=0, reparse_tag=None):
        self.st_size = size
        self.st_reparse_tag = reparse_tag


class FakeEntry:
    def __init__(
        self,
        name,
        path,
        is_symlink=False,
        is_dir=False,
        is_file=False,
        size=0,
        reparse_tag=None,
        stat_error=None,
    ):
        self.name = name
        self.path = path
        self._symlink = is_symlink
        self._dir = is_dir
        self._file = is_file
        self._size = size
        self._tag = reparse_tag
        self._stat_error = stat_error

    def is_symlink(self):
        return self._symlink

    def is_dir(self, follow_symlinks=True):
        return self._dir

    def is_file(self, follow_symlinks=True):
        return self._file

    def stat(self, follow_symlinks=True):
        if self._stat_error:
            raise self._stat_error
        return FakeStat(size=self._size, reparse_tag=self._tag)


def _classify(name, **kwargs):
    return Inspector()._classify_kind(FakeEntry(name, name, **kwargs))


def test_classify_kind_variants(tmp_path):
    assert _classify("f", is_file=True) is EntryKind.FILE
    assert _classify("d", is_dir=True) is EntryKind.DIRECTORY
    assert _classify("l", is_symlink=True) is EntryKind.SYMLINK
    assert _classify("j", is_symlink=True, reparse_tag=0xA0000003) is EntryKind.JUNCTION
    assert _classify("r", is_symlink=True, reparse_tag=0xA0000001) is EntryKind.REPARSE_POINT
    assert _classify("s") is EntryKind.SPECIAL


def test_contains_link_component_mocked(monkeypatch):
    import agent_harness.infrastructure.inspector as module

    real = os.path.islink

    def fake_islink(path):
        return str(path).endswith("linked")

    monkeypatch.setattr(os.path, "islink", fake_islink)
    assert _contains_link_component(Path("C:/x/linked")) is True
    assert _contains_link_component(Path("C:/x/normal")) is False
    monkeypatch.setattr(module.os.path, "islink", real)


def test_contains_link_component_oserror(monkeypatch):
    def fake_islink(path):
        raise OSError("boom")

    monkeypatch.setattr(os.path, "islink", fake_islink)
    assert _contains_link_component(Path("C:/x/y")) is False


def test_link_entry_visit_classifies_without_following(tmp_path):
    from agent_harness.infrastructure.inspector import _Walk
    from agent_harness.inspection.request import InspectionRequest

    root = tmp_path
    entry = FakeEntry("link", str(root / "link"), is_symlink=True)
    walk = _Walk(InspectionRequest())
    Inspector()._visit(entry, root, walk, walk.request, [], 0)
    assert len(walk.entries) == 1
    assert walk.entries[0].kind is EntryKind.SYMLINK
    assert any(w.code == "LINK_NOT_FOLLOWED" for w in walk.warnings)


def test_link_policy_error_raises(tmp_path):
    from agent_harness.infrastructure.inspector import _Walk
    from agent_harness.inspection.errors import LinkEncounteredError
    from agent_harness.inspection.request import InspectionRequest

    root = tmp_path
    entry = FakeEntry("link", str(root / "link"), is_symlink=True)
    walk = _Walk(InspectionRequest(link_policy="error"))
    with pytest.raises(LinkEncounteredError):
        Inspector()._visit(entry, root, walk, walk.request, [], 0)


def test_special_entry_skip_and_fail(tmp_path):
    from agent_harness.infrastructure.inspector import _Walk
    from agent_harness.inspection.errors import UnsupportedEntryError
    from agent_harness.inspection.request import InspectionRequest

    root = tmp_path
    entry = FakeEntry("pipe", str(root / "pipe"))
    walk = _Walk(InspectionRequest())
    Inspector()._visit(entry, root, walk, walk.request, [], 0)
    assert len(walk.entries) == 1
    assert walk.entries[0].kind is EntryKind.SPECIAL
    assert any(w.code == "UNSUPPORTED_ENTRY" for w in walk.warnings)
    walk_fail = _Walk(InspectionRequest(error_policy="fail"))
    with pytest.raises(UnsupportedEntryError):
        Inspector()._visit(entry, root, walk_fail, walk_fail.request, [], 0)


def test_list_children_permission(tmp_path, monkeypatch):
    from agent_harness.infrastructure.inspector import Inspector, _Walk
    from agent_harness.inspection.errors import PermissionDeniedError
    from agent_harness.inspection.request import InspectionRequest

    def deny(*args, **kwargs):
        raise PermissionError("denied")

    monkeypatch.setattr("agent_harness.infrastructure.inspector.os.scandir", deny)
    walk = _Walk(InspectionRequest())
    assert Inspector()._list_children(tmp_path, walk, walk.request) is None
    assert any(w.code == "INSPECTION_PERMISSION_DENIED" for w in walk.warnings)
    fail_walk = _Walk(InspectionRequest(error_policy="fail"))
    with pytest.raises(PermissionDeniedError):
        Inspector()._list_children(tmp_path, fail_walk, fail_walk.request)


def test_list_children_oserror(tmp_path, monkeypatch):
    from agent_harness.infrastructure.inspector import Inspector, _Walk
    from agent_harness.inspection.errors import InspectionInternalError
    from agent_harness.inspection.request import InspectionRequest

    def boom(*args, **kwargs):
        raise OSError("boom")

    monkeypatch.setattr("agent_harness.infrastructure.inspector.os.scandir", boom)
    walk = _Walk(InspectionRequest())
    assert Inspector()._list_children(tmp_path, walk, walk.request) is None
    assert any(w.code == "FILESYSTEM_CHANGED" for w in walk.warnings)
    fail_walk = _Walk(InspectionRequest(error_policy="fail"))
    with pytest.raises(InspectionInternalError):
        Inspector()._list_children(tmp_path, fail_walk, fail_walk.request)


def test_entry_size_oserror(tmp_path):
    from agent_harness.infrastructure.inspector import Inspector, _Walk
    from agent_harness.inspection.request import InspectionRequest

    entry = FakeEntry("f", str(tmp_path / "f"), is_file=True, stat_error=OSError("boom"))
    walk = _Walk(InspectionRequest())
    assert Inspector()._entry_size(entry, walk, walk.request) == 0
    assert any(w.code == "FILESYSTEM_CHANGED" for w in walk.warnings)


def test_entry_size_too_large_warns(tmp_path):
    from agent_harness.infrastructure.inspector import Inspector, _Walk
    from agent_harness.inspection.request import InspectionRequest

    entry = FakeEntry("f", str(tmp_path / "f"), is_file=True, size=5000)
    walk = _Walk(InspectionRequest(max_individual_file_bytes=100))
    size = Inspector()._entry_size(entry, walk, walk.request)
    assert size == 5000
    assert any(w.code == "FILE_TOO_LARGE" for w in walk.warnings)


def test_relative_path_fallback_outside_root(tmp_path):
    root = tmp_path
    outside = root.parent / "outside"
    assert _relative_path(str(outside / "x.py"), root) == "x.py"


def test_total_bytes_limit(tmp_path):
    (tmp_path / "big.bin").write_bytes(b"x" * 5000)
    summary = _walk(tmp_path, max_total_bytes=100)
    assert summary.limit is not None
    assert summary.limit.code == "LIMIT_TOTAL_BYTES_EXCEEDED"


def test_manifest_limit_warns(tmp_path):
    for i in range(5):
        (tmp_path / f"mod{i}" / "package.json").parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / f"mod{i}" / "package.json").write_text("{}")
    summary = _walk(tmp_path, max_manifests=2)
    assert any(w.code == "LIMIT_MANIFESTS_EXCEEDED" for w in summary.warnings)
    assert len(summary.manifest_summary) == 2


def test_path_too_long_warns(tmp_path):
    deep = tmp_path / ("d" * 60)
    deep.mkdir(parents=True)
    (deep / "x.py").write_text("x")
    summary = _walk(tmp_path, max_path_length=20)
    assert any(w.code == "PATH_TOO_LONG" for w in summary.warnings)


def test_nested_repository_detection(tmp_path, monkeypatch):
    from agent_harness.infrastructure.inspector import Inspector

    real_exists = os.path.exists

    def fake_exists(path):
        return path.replace("\\", "/").endswith("inner/.git")

    monkeypatch.setattr(os.path, "exists", fake_exists)
    assert Inspector._is_nested_repository(str(tmp_path / "inner")) is True
    assert Inspector._is_nested_repository(str(tmp_path / "plain")) is False
    monkeypatch.setattr(os.path, "exists", real_exists)


def test_nested_repository_oserror(tmp_path, monkeypatch):
    from agent_harness.infrastructure.inspector import Inspector

    def boom(path):
        raise OSError("boom")

    monkeypatch.setattr(os.path, "exists", boom)
    assert Inspector._is_nested_repository(str(tmp_path / "inner")) is False


def test_resolve_embedded_nul_rejected(tmp_path):
    from agent_harness.inspection.errors import InspectionError

    with pytest.raises(InspectionError):
        resolve_inspection_root("a\x00b")


def test_resolve_link_component_raise(tmp_path, monkeypatch):
    import agent_harness.infrastructure.inspector as module

    monkeypatch.setattr(module, "_contains_link_component", lambda _p: True)
    with pytest.raises(PathEscapeError):
        resolve_inspection_root(str(tmp_path))


def test_resolve_upward_link_raise(tmp_path, monkeypatch):
    import agent_harness.infrastructure.inspector as module

    calls = {"n": 0}

    def fake(path):
        calls["n"] += 1
        return calls["n"] >= 2

    monkeypatch.setattr(module, "_contains_link_component", fake)
    with pytest.raises(PathEscapeError):
        resolve_inspection_root(str(tmp_path))


def test_resolve_marker_oserror(tmp_path, monkeypatch):
    def raiser(_path):
        raise OSError("boom")

    root, repo_type = resolve_inspection_root(str(tmp_path), marker_exists=raiser)
    assert repo_type == "directory"
    assert root == tmp_path


def test_contains_link_component_empty_path():
    assert _contains_link_component(Path("")) is False


def test_scandir_continue_on_skip(tmp_path, monkeypatch):
    from agent_harness.infrastructure.inspector import Inspector

    def deny(*args, **kwargs):
        raise PermissionError("denied")

    monkeypatch.setattr("agent_harness.infrastructure.inspector.os.scandir", deny)
    summary = Inspector().inspect(tmp_path, InspectionRequest())
    assert summary.file_count == 0
    assert any(w.code == "INSPECTION_PERMISSION_DENIED" for w in summary.warnings)


def test_max_directories_partial(tmp_path):
    for i in range(5):
        (tmp_path / f"dir{i}").mkdir()
    summary = _walk(tmp_path, max_directories=2)
    assert summary.limit is not None
    assert summary.limit.code == "LIMIT_DIRECTORIES_EXCEEDED"


def test_add_warning_cap(tmp_path):
    from agent_harness.infrastructure.inspector import Inspector, _Walk

    walk = _Walk(InspectionRequest(max_warnings=1))
    walk.warnings.append(WarningRecord("A", "a"))
    Inspector()._add_warning(walk, "B", "b")
    assert len(walk.warnings) == 1
    assert walk.limit is not None
    assert walk.limit.code == "LIMIT_WARNINGS_EXCEEDED"
    walk.limit = None
    walk.warnings = []
    walk.warnings.append(WarningRecord("A", "a"))
    walk.limit = LimitInfo("X", 1, 1)
    Inspector()._add_warning(walk, "B", "b")
    assert walk.limit.code == "X"


def test_hard_excluded_oserror(tmp_path):
    from agent_harness.infrastructure.inspector import Inspector

    class _ErrEntry(FakeEntry):
        def is_dir(self, follow_symlinks=True):
            raise OSError("boom")

    entry = _ErrEntry(".git", str(tmp_path / ".git"))
    assert Inspector._is_hard_excluded(entry, ".git") is False
    assert Inspector._is_generated_directory(entry, "node_modules") is False


def test_classify_kind_oserror(tmp_path):
    class _ErrEntry(FakeEntry):
        def is_symlink(self):
            raise OSError("boom")

    entry = _ErrEntry("x", str(tmp_path / "x"))
    assert Inspector()._classify_kind(entry) is EntryKind.SPECIAL


def test_reparse_tag_oserror(tmp_path):
    class _StatErrEntry(FakeEntry):
        def stat(self, follow_symlinks=True):
            raise OSError("boom")

    entry = _StatErrEntry("x", str(tmp_path / "x"), is_symlink=True)
    assert Inspector._reparse_tag(entry) is None


def test_build_gradle_manifest():
    assert Inspector._classify_file("build.gradle") == ("manifest", True, "java")
    assert Inspector._classify_file("noext") == ("unknown", False, "")
