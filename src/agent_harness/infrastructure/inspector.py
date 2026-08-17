"""Bounded, metadata-only filesystem inspector.

The inspector never opens or reads file content, never follows symlinks,
junctions, or reparse points, and enforces the root-containment invariant and
mandatory resource budgets. All entry metadata is captured once; races become
warnings or explicit partial results.
"""

from __future__ import annotations

import os
from collections import Counter, deque
from dataclasses import dataclass, field
from pathlib import Path

from ..inspection.errors import (
    InspectionInternalError,
    LinkEncounteredError,
    PathEscapeError,
    PathNotDirectoryError,
    PathNotFoundError,
    PermissionDeniedError,
    UnsupportedEntryError,
    sanitize_text,
)
from ..inspection.request import InspectionRequest
from ..inspection.result import (
    EntryKind,
    InspectionEntry,
    LimitInfo,
    WarningRecord,
)

# Hard safety and default generated-directory exclusions.
IGNORED_DIRECTORY_NAMES = frozenset(
    {
        ".git",
        ".venv",
        "venv",
        "node_modules",
        "bin",
        "obj",
        "dist",
        "build",
        "__pycache__",
        ".pytest_cache",
        ".mypy_cache",
        ".ruff_cache",
        ".tox",
        ".idea",
        ".vscode",
        "htmlcov",
        ".eggs",
    }
)
IGNORED_DIRECTORY_SUFFIXES = (".egg-info", ".dist-info")

TEST_DIRECTORY_NAMES = frozenset({"test", "tests", "__tests__", "spec", "specs"})

# Exact exception: the only environment-template filename allowed to remain
# visible (see docs/SECURITY_MODEL.md). Applied before any broad sensitive rule.
SENSITIVE_ENV_EXAMPLE_EXCEPTION = frozenset({".env.example"})

SENSITIVE_EXACT = frozenset(
    {
        ".env",
        "id_rsa",
        "id_ed25519",
        "id_dsa",
        "id_ecdsa",
        ".npmrc",
        ".pypirc",
        ".netrc",
        "credentials",
        "credentials.json",
        "credentials.toml",
        "client_secret.json",
        "service_account.json",
        "secrets.json",
    }
)
SENSITIVE_SUFFIXES = (".pem", ".key", ".p12", ".pfx", ".secret", ".jks", ".keystore")

# Credential-abbreviation tokens matched only on approved token boundaries so
# that `cred` / `creds` are treated like `credential` / `credentials` without
# redacting unrelated names that merely contain the character sequence.
SENSITIVE_TOKENS = frozenset({"cred", "creds"})

# Approved token-boundary characters between basename components.
_SENSITIVE_TOKEN_SEPARATORS = (".", "_", "-", " ")

BINARY_EXTENSIONS = frozenset(
    {
        ".png", ".jpg", ".jpeg", ".gif", ".ico", ".bmp", ".webp",
        ".pdf", ".zip", ".gz", ".tar", ".7z", ".rar", ".bz2", ".xz",
        ".exe", ".dll", ".so", ".dylib", ".bin", ".class", ".jar",
        ".pyc", ".pyo", ".woff", ".woff2", ".ttf", ".eot", ".otf",
        ".mp3", ".mp4", ".wav", ".ogg", ".webm", ".mov", ".avi",
        ".wasm", ".db", ".sqlite", ".sqlite3", ".o", ".a", ".obj",
    }
)

LANGUAGES: dict[str, str] = {
    ".py": "python",
    ".pyi": "python",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".js": "javascript",
    ".jsx": "javascript",
    ".mjs": "javascript",
    ".cjs": "javascript",
    ".go": "go",
    ".rs": "rust",
    ".java": "java",
    ".cs": "csharp",
    ".c": "c",
    ".h": "c",
    ".cpp": "cpp",
    ".cc": "cpp",
    ".hpp": "cpp",
    ".hh": "cpp",
    ".rb": "ruby",
    ".php": "php",
    ".swift": "swift",
    ".kt": "kotlin",
    ".kts": "kotlin",
    ".md": "markdown",
    ".markdown": "markdown",
    ".rst": "restructuredtext",
    ".json": "json",
    ".json5": "json",
    ".yaml": "yaml",
    ".yml": "yaml",
    ".toml": "toml",
    ".sh": "shell",
    ".bash": "shell",
    ".zsh": "shell",
    ".sql": "sql",
    ".html": "html",
    ".htm": "html",
    ".css": "css",
    ".scss": "scss",
    ".sass": "scss",
    ".vue": "vue",
    ".svelte": "svelte",
    ".ipynb": "jupyter",
    ".proto": "protobuf",
    ".tf": "terraform",
    ".xml": "xml",
    ".gradle": "gradle",
    ".txt": "text",
    ".lock": "lockfile",
    ".min.js": "javascript",
    ".test.js": "javascript",
    ".spec.js": "javascript",
}

EXACT_FILE_CLASSIFICATIONS: dict[str, str] = {
    "dockerfile": "dockerfile",
    "makefile": "makefile",
    "justfile": "justfile",
    "license": "license",
    "license.txt": "license",
    "license.md": "license",
    "readme": "documentation",
    "readme.md": "documentation",
    "readme.txt": "documentation",
    "readme.rst": "documentation",
}

MANIFEST_ECOSYSTEMS: dict[str, str] = {
    "pyproject.toml": "python",
    "package.json": "javascript",
    "pom.xml": "java",
    "go.mod": "go",
    "cargo.toml": "rust",
    "dockerfile": "container",
    "gemfile": "ruby",
    "composer.json": "php",
}

DOCUMENTATION_SUFFIXES = (".md", ".markdown", ".rst")

_IO_REPARSE_TAG_MOUNT_POINT = 0xA0000003


@dataclass
class _Walk:
    request: InspectionRequest
    entries: list[InspectionEntry] = field(default_factory=list)
    file_count: int = 0
    directory_count: int = 0
    total_size: int = 0
    warnings: list[WarningRecord] = field(default_factory=list)
    exclusions: Counter = field(default_factory=Counter)
    languages: Counter = field(default_factory=Counter)
    manifests: list[tuple[str, str]] = field(default_factory=list)
    test_directories: int = 0
    documentation: int = 0
    sensitive: int = 0
    limit: LimitInfo | None = None
    stop: bool = False
    _sensitive_index: int = 0
    _manifest_warned: bool = False


@dataclass(frozen=True)
class WalkSummary:
    entries: tuple[InspectionEntry, ...]
    file_count: int
    directory_count: int
    total_metadata_size: int
    language_summary: tuple[tuple[str, int], ...]
    manifest_summary: tuple[tuple[str, str], ...]
    test_directory_count: int
    documentation_count: int
    exclusion_summary: tuple[tuple[str, int], ...]
    sensitive_entries: int
    warnings: tuple[WarningRecord, ...]
    limit: LimitInfo | None = None


def resolve_inspection_root(
    requested_path: str, *, marker_exists=None
) -> tuple[Path, str]:
    """Return ``(inspection_root, repository_type)`` without following links.

    ``repository_type`` is ``"git_worktree"``, ``"git_bare"``, or
    ``"directory"``. The returned root's path must not traverse any symlink or
    junction; otherwise a :class:`PathEscapeError` is raised.
    """
    try:
        lexical_abs = Path(os.path.abspath(requested_path))
    except (OSError, ValueError) as exc:
        raise InspectionInternalError(f"could not resolve path: {exc}") from exc
    try:
        if not lexical_abs.exists():
            raise PathNotFoundError(f"path not found: {sanitize_text(requested_path)}")
        if not lexical_abs.is_dir():
            raise PathNotDirectoryError(
                f"path is not a directory: {sanitize_text(requested_path)}"
            )
    except (OSError, ValueError) as exc:
        raise InspectionInternalError(f"could not inspect path: {exc}") from exc
    if _contains_link_component(lexical_abs):
        raise PathEscapeError("requested path traverses a symbolic link or junction")
    return _find_repository_root(lexical_abs, marker_exists)


def _find_repository_root(lexical_abs: Path, marker_exists=None) -> tuple[Path, str]:
    if marker_exists is None:
        marker_exists = lambda path: path.exists()  # noqa: E731
    current = lexical_abs
    while True:
        if _contains_link_component(current):
            raise PathEscapeError("repository path traverses a symbolic link or junction")
        git_marker = current / ".git"
        try:
            if marker_exists(git_marker):
                return current, "git_worktree"
        except OSError:
            pass
        if _looks_like_bare_repository(current):
            return current, "git_bare"
        parent = current.parent
        if parent == current:
            break
        current = parent
    return lexical_abs, "directory"


def _looks_like_bare_repository(path: Path) -> bool:
    try:
        return (
            (path / "HEAD").is_file()
            and (path / "objects").is_dir()
            and (path / "refs").is_dir()
            and not (path / ".git").exists()
        )
    except OSError:
        return False


def _contains_link_component(path: Path) -> bool:
    parts = path.parts
    if not parts:
        return False
    current = Path(parts[0])
    for part in parts[1:]:
        current = current / part
        try:
            if os.path.islink(current):
                return True
        except OSError:
            return False
    return False


def _has_sensitive_bounded_token(lowered_name: str) -> bool:
    """Return whether any token equals a protected sensitive token.

    Tokens are split on approved boundaries only (``.``, ``_``, ``-``,
    whitespace, and basename edges). This deliberately rejects names that merely
    contain the character sequence inside an unrelated token (for example
    ``accredited`` or ``credit``) while still catching ``cred`` / ``creds`` as
    entire basename components.
    """
    normalized = lowered_name
    for separator in _SENSITIVE_TOKEN_SEPARATORS:
        normalized = normalized.replace(separator, " ")
    return any(token in SENSITIVE_TOKENS for token in normalized.split())


class Inspector:
    """Bounded, deterministic, metadata-only walker."""

    def inspect(self, root: Path, request: InspectionRequest) -> WalkSummary:
        walk = _Walk(request)
        queue: deque[tuple[Path, int]] = deque()
        queue.append((root, 0))
        while queue and not walk.stop:
            current, depth = queue.popleft()
            if depth > request.max_depth:
                walk.limit = LimitInfo("LIMIT_DEPTH_EXCEEDED", request.max_depth, depth)
                walk.stop = True
                break
            children = self._list_children(current, walk, request)
            if children is None:
                continue
            for entry in children:
                if walk.stop:
                    break
                self._visit(entry, root, walk, request, queue, depth)
        return self._summary(walk)

    def _list_children(self, current: Path, walk: _Walk, request: InspectionRequest):
        try:
            with os.scandir(current) as it:
                return sorted(it, key=lambda child: child.name)
        except PermissionError:
            if request.error_policy == "fail":
                raise PermissionDeniedError(
                    f"permission denied reading directory {current}"
                )
            self._add_warning(walk, "INSPECTION_PERMISSION_DENIED", "permission denied")
            return None
        except OSError as exc:
            if request.error_policy == "fail":
                raise InspectionInternalError(f"could not read directory: {exc}") from exc
            self._add_warning(walk, "FILESYSTEM_CHANGED", "directory could not be read")
            return None

    def _visit(
        self,
        entry,
        root: Path,
        walk: _Walk,
        request: InspectionRequest,
        queue,
        depth: int,
    ) -> None:
        name = entry.name
        rel_path = self._relative_path(entry.path, root)
        if len(rel_path) > request.max_path_length:
            self._add_warning(walk, "PATH_TOO_LONG", "entry path exceeds the path limit")
            return
        if self._is_hard_excluded(entry, name):
            walk.exclusions["ignored"] += 1
            return
        if not request.include_ignored and self._is_generated_directory(entry, name):
            walk.exclusions["ignored"] += 1
            return
        if not request.include_hidden and name.startswith("."):
            walk.exclusions["hidden"] += 1
            return
        kind = self._classify_kind(entry)
        if kind in (EntryKind.SYMLINK, EntryKind.JUNCTION, EntryKind.REPARSE_POINT):
            if request.link_policy == "error":
                raise LinkEncounteredError(
                    f"link encountered and link_policy is error: {rel_path}"
                )
            self._add_warning(walk, "LINK_NOT_FOLLOWED", "link classified, not followed")
            size = self._entry_size(entry, walk, request)
            walk.entries.append(
                InspectionEntry(
                    repository_relative_path=rel_path,
                    kind=kind,
                    size=size,
                    classification="link",
                )
            )
            return
        if kind is EntryKind.SPECIAL:
            if request.error_policy == "fail":
                raise UnsupportedEntryError(f"unsupported entry type: {rel_path}")
            self._add_warning(walk, "UNSUPPORTED_ENTRY", "special entry skipped")
            walk.entries.append(
                InspectionEntry(
                    repository_relative_path=rel_path,
                    kind=kind,
                    size=0,
                    classification="special",
                )
            )
            return
        if kind is EntryKind.DIRECTORY:
            self._visit_directory(entry, root, walk, request, queue, depth)
            return
        self._visit_file(entry, root, walk, request)

    def _visit_directory(
        self,
        entry,
        root: Path,
        walk: _Walk,
        request: InspectionRequest,
        queue,
        depth: int,
    ) -> None:
        if walk.directory_count >= request.max_directories:
            walk.limit = LimitInfo(
                "LIMIT_DIRECTORIES_EXCEEDED", request.max_directories, walk.directory_count
            )
            walk.stop = True
            return
        walk.directory_count += 1
        if entry.name.lower() in TEST_DIRECTORY_NAMES:
            walk.test_directories += 1
        if self._is_nested_repository(entry.path):
            walk.exclusions["nested_repository"] += 1
            return
        walk.entries.append(
            InspectionEntry(
                repository_relative_path=self._relative_path(entry.path, root),
                kind=EntryKind.DIRECTORY,
                size=0,
                classification="directory",
            )
        )
        queue.append((Path(entry.path), depth + 1))

    def _visit_file(self, entry, root: Path, walk: _Walk, request: InspectionRequest) -> None:
        if walk.file_count >= request.max_entries:
            walk.limit = LimitInfo("LIMIT_ENTRIES_EXCEEDED", request.max_entries, walk.file_count)
            walk.stop = True
            return
        walk.file_count += 1
        size = self._entry_size(entry, walk, request)
        if request.max_total_bytes and walk.total_size + size > request.max_total_bytes:
            walk.limit = LimitInfo(
                "LIMIT_TOTAL_BYTES_EXCEEDED", request.max_total_bytes, walk.total_size + size
            )
            walk.stop = True
            return
        walk.total_size += size
        rel_path = self._relative_path(entry.path, root)
        if self._is_sensitive_name(entry.name):
            walk.sensitive += 1
            walk._sensitive_index += 1
            redacted_path = self._redact_path(rel_path, walk._sensitive_index)
            walk.entries.append(
                InspectionEntry(
                    repository_relative_path=redacted_path,
                    kind=EntryKind.FILE,
                    size=size,
                    classification="sensitive",
                    redacted=True,
                )
            )
            return
        classification, is_manifest, ecosystem = self._classify_file(entry.name)
        if is_manifest:
            walk.manifests.append((rel_path, ecosystem))
            if len(walk.manifests) > request.max_manifests:
                walk.manifests.pop()
                if not walk._manifest_warned:
                    walk._manifest_warned = True
                    self._add_warning(walk, "LIMIT_MANIFESTS_EXCEEDED", "manifest limit reached")
        if classification in ("documentation", "markdown", "restructuredtext"):
            walk.documentation += 1
        if classification not in (
            "manifest",
            "dockerfile",
            "makefile",
            "justfile",
            "license",
            "documentation",
            "binary",
            "unknown",
        ):
            walk.languages[classification] += 1
        walk.entries.append(
            InspectionEntry(
                repository_relative_path=rel_path,
                kind=EntryKind.FILE,
                size=size,
                classification=classification,
            )
        )

    def _summary(self, walk: _Walk) -> WalkSummary:
        top_languages = sorted(
            walk.languages.items(), key=lambda item: (-item[1], item[0])
        )[0 : walk.request.max_languages]
        return WalkSummary(
            entries=tuple(walk.entries),
            file_count=walk.file_count,
            directory_count=walk.directory_count,
            total_metadata_size=walk.total_size,
            language_summary=tuple(top_languages),
            manifest_summary=tuple(walk.manifests),
            test_directory_count=walk.test_directories,
            documentation_count=walk.documentation,
            exclusion_summary=tuple(sorted(walk.exclusions.items())),
            sensitive_entries=walk.sensitive,
            warnings=tuple(walk.warnings),
            limit=walk.limit,
        )

    def _add_warning(self, walk: _Walk, code: str, message: str) -> None:
        if len(walk.warnings) >= walk.request.max_warnings:
            if walk.limit is None:
                walk.limit = LimitInfo(
                    "LIMIT_WARNINGS_EXCEEDED",
                    walk.request.max_warnings,
                    len(walk.warnings),
                )
            return
        walk.warnings.append(WarningRecord(code=code, message=sanitize_text(message)))

    @staticmethod
    def _relative_path(path: str, root: Path) -> str:
        try:
            return Path(path).relative_to(root).as_posix()
        except ValueError:
            return Path(path).name

    @staticmethod
    def _redact_path(rel_path: str, index: int) -> str:
        parent = rel_path.rsplit("/", 1)[0] if "/" in rel_path else ""
        token = f"<sensitive-{index}>"
        return f"{parent}/{token}" if parent else token

    @staticmethod
    def _is_sensitive_name(name: str) -> bool:
        """Classify a filename as sensitive using explicit precedence.

        Precedence (highest first):

        1. Exact approved exception (``.env.example``) -> visible.
        2. Exact protected names (``SENSITIVE_EXACT``) -> sensitive.
        3. Protected bounded tokens or extensions (``.env.*`` prefix,
           ``SENSITIVE_SUFFIXES``, ``SENSITIVE_TOKENS`` on approved boundaries)
           -> sensitive.
        4. Non-sensitive default -> visible.

        The classifier is name-based only; it never opens or reads file content.
        """
        lowered = name.lower()
        if lowered in SENSITIVE_ENV_EXAMPLE_EXCEPTION:
            return False
        if lowered in SENSITIVE_EXACT:
            return True
        if lowered.startswith(".env."):
            return True
        if lowered.endswith(SENSITIVE_SUFFIXES):
            return True
        return _has_sensitive_bounded_token(lowered)

    @staticmethod
    def _is_hard_excluded(entry, name: str) -> bool:
        try:
            is_dir = entry.is_dir(follow_symlinks=False)
        except OSError:
            is_dir = False
        return is_dir and name == ".git"

    @staticmethod
    def _is_generated_directory(entry, name: str) -> bool:
        try:
            is_dir = entry.is_dir(follow_symlinks=False)
        except OSError:
            is_dir = False
        if not is_dir:
            return False
        lowered = name.lower()
        if lowered in IGNORED_DIRECTORY_NAMES:
            return True
        return lowered.endswith(IGNORED_DIRECTORY_SUFFIXES)

    @staticmethod
    def _is_nested_repository(dir_path: str) -> bool:
        try:
            return os.path.exists(os.path.join(dir_path, ".git"))
        except OSError:
            return False

    def _entry_size(self, entry, walk: _Walk, request: InspectionRequest) -> int:
        try:
            st = entry.stat(follow_symlinks=False)
        except OSError:
            self._add_warning(walk, "FILESYSTEM_CHANGED", "entry could not be stat'ed")
            return 0
        if (
            request.max_individual_file_bytes
            and st.st_size > request.max_individual_file_bytes
        ):
            self._add_warning(walk, "FILE_TOO_LARGE", "entry exceeds the individual file size limit")
        return int(st.st_size)

    def _classify_kind(self, entry) -> EntryKind:
        try:
            if entry.is_symlink():
                tag = self._reparse_tag(entry)
                if tag is not None:
                    if tag == _IO_REPARSE_TAG_MOUNT_POINT:
                        return EntryKind.JUNCTION
                    return EntryKind.REPARSE_POINT
                return EntryKind.SYMLINK
            if entry.is_dir(follow_symlinks=False):
                return EntryKind.DIRECTORY
            if entry.is_file(follow_symlinks=False):
                return EntryKind.FILE
            return EntryKind.SPECIAL
        except OSError:
            return EntryKind.SPECIAL

    @staticmethod
    def _reparse_tag(entry):
        try:
            return getattr(entry.stat(follow_symlinks=False), "st_reparse_tag", None)
        except (OSError, AttributeError):
            return None

    @classmethod
    def _classify_file(cls, name: str):
        lowered = name.lower()
        if lowered in MANIFEST_ECOSYSTEMS:
            return "manifest", True, MANIFEST_ECOSYSTEMS[lowered]
        if lowered.startswith("requirements") and lowered.endswith(".txt"):
            return "manifest", True, "python"
        if lowered.endswith((".csproj", ".sln")):
            return "manifest", True, "dotnet"
        if lowered.startswith("build.gradle"):
            return "manifest", True, "java"
        if lowered.endswith(".tf"):
            return "manifest", True, "terraform"
        if lowered.startswith("docker-compose") or lowered.startswith("compose"):
            if lowered.endswith((".yml", ".yaml")):
                return "manifest", True, "container"
        exact = EXACT_FILE_CLASSIFICATIONS.get(lowered)
        if exact is not None:
            return exact, False, ""
        suffix = cls._suffix(name)
        if suffix in BINARY_EXTENSIONS:
            return "binary", False, ""
        language = LANGUAGES.get(suffix)
        if language is not None:
            return language, False, ""
        return "unknown", False, ""

    @staticmethod
    def _suffix(name: str) -> str:
        for suffix in (".min.js", ".test.js", ".spec.js"):
            if name.endswith(suffix):
                return suffix
        index = name.rfind(".")
        if index < 0:
            return ""
        return name[index:].lower()
