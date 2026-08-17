# Phase 3 — Safe Repository Inspection Design

## 1. Phase purpose

Phase 3 adds a minimal, read-only, metadata-only repository inspection capability to Agent Harness CLI. It lets a user inspect a local repository and obtain a deterministic inventory of repository structure, entry metadata, classification summaries (languages, manifests, tests, documentation), ignore/exclusion summaries, and optional read-only Git metadata — without modifying the repository, reading file content, invoking a model, or touching the network.

User problem solved: establish a trustworthy, bounded structural snapshot of a local repository that later phases (search, reading, repository map, ticket analysis, LLM reasoning) can build on.

Minimal useful capability: `agent-harness inspect` reports repository-relative entries and bounded metadata from the current directory (or an explicitly supplied path), in READ_ONLY mode, never mutating anything.

Explicit non-goals: no content reading, no search, no repository map, no semantic analysis, no Git mutation, no remote inspection, no RAG, no model calls.

Relationship to later phases: Phase 4 adds exact search and controlled file reading; Phase 5 adds repository map and symbol analysis; Phase 6 adds trajectories/evidence; Phase 7 adds the model adapter. Phase 3 deliberately stops at metadata inventory.

## 2. Terminology

- Requested path: the path the user asks to inspect (default: current working directory).
- Repository root: the topmost directory considered the inspected repository (Git worktree root when a Git worktree is detected, otherwise the resolved requested directory).
- Inspection root: the directory actually traversed; it equals the repository root for Git worktrees and equals the requested directory for non-Git inspection.
- Logical path: a path as given by the user (may be relative, contain `.`/`..`).
- Physical/resolved path: the absolute, normalized path after resolution.
- Repository-relative path: a path expressed relative to the inspection root using the platform separator, normalized and deterministic.
- Entry: a single filesystem object encountered during traversal (file or directory in Phase 3; symlinks and special entries are classified, not traversed).
- File entry / directory entry: entries classified by type.
- Symbolic link: a POSIX symlink or a Windows symlink entry.
- Junction: a Windows reparse point (directory junction).
- Reparse point: a Windows filesystem tag (symlink, junction, mount point, or other).
- Mount boundary: a point where a different volume or filesystem is mounted.
- Traversal: the deterministic walk over entries under the inspection root.
- Snapshot: the bounded, immutable result model produced by one inspection.
- Inspection budget: the mandatory resource limits constraining the walk.
- Excluded entry: an entry skipped because of a safety exclusion, ignore rule, or deny rule; not reported as inspected.
- Redacted entry: an entry whose metadata is reported with the filename redacted or sanitized (used for sensitive names).
- Binary file: an entry whose name or content signature indicates binary data (Phase 3 uses name/extension heuristics only; content is not read).
- Generated file: an entry under a default generated-directory rule (e.g., build output, caches).
- Sensitive file: an entry whose name matches the sensitive-file policy (e.g., `.env`, keys).
- Unsupported entry: an entry type the inspector cannot safely process (e.g., special device, FIFO, socket); skipped with a warning.
- Partial result: a result that stopped because a budget was exceeded or an error policy allowed continuation; explicitly marked.

## 3. Phase scope

| Item | Classification |
|---|---|
| Repository root (resolved) | IN_SCOPE |
| Repository type (Git worktree / non-Git directory) | IN_SCOPE |
| File and directory inventory (metadata) | IN_SCOPE |
| Repository-relative paths | IN_SCOPE |
| File sizes | IN_SCOPE |
| File types (extension-based classification) | IN_SCOPE |
| Detected programming languages (extension/filename heuristics) | IN_SCOPE |
| Detected manifests (filename matching, no parsing) | IN_SCOPE |
| Detected test directories | IN_SCOPE |
| Detected documentation | IN_SCOPE |
| Git worktree presence | IN_SCOPE (metadata only) |
| Current branch | IN_SCOPE (read-only Git adapter) |
| Current commit | IN_SCOPE (read-only Git adapter) |
| Dirty or clean state | IN_SCOPE (read-only Git status adapter, bounded) |
| Ignore/exclusion summary | IN_SCOPE |
| Limit/truncation summary | IN_SCOPE |
| Warning summary | IN_SCOPE |
| File content | DEFERRED (Phase 4) |
| Exact search | DEFERRED (Phase 4) |
| Repository map / symbol analysis | DEFERRED (Phase 5) |
| Command execution | PROHIBITED in Phase 3 |
| Git mutation / staging / commit | PROHIBITED |
| Remote Git / GitHub inspection | PROHIBITED |
| Network access | PROHIBITED |
| Model invocation | PROHIBITED |

## 4. Non-goals

Deferred (with the owning phase or responsibility):

- File modification (all phases after write authorization; never Phase 3).
- Formatting (later tooling phases).
- Dependency installation (Phase 12+ build/test).
- Build and test execution (Phase 12).
- Git mutation, staging, or commit (future write phases).
- Remote Git inspection (Phase 16).
- GitHub inspection (Phase 16).
- Ticket analysis (Phase 9).
- Semantic code analysis (Phase 8).
- AST parsing beyond Phase 3 need (Phase 5/8).
- Embeddings and RAG (Phase 17).
- LLM invocation (Phase 7+).
- Network access (never during inspection).
- Sandbox execution (Phase 11).
- Worktree creation (Phase 11).
- Secret extraction or credential validation (future security phases).
- Following links outside the repository (never).

## 5. Functional use cases

1. Inspect current repository — input: none (default cwd); resolves the cwd Git root; READ_ONLY policy decision; bounded metadata walk; text or JSON result; exit 0; no side effects.
2. Inspect an explicitly supplied local path — input: `--path <dir>`; resolves and validates; same pipeline.
3. Inspect a non-repository directory — supported: inspection root is the requested directory; `repository_type="directory"`; no Git metadata.
4. Inspect an empty repository — valid Git root with zero entries; result with file_count=0; exit 0.
5. Inspect a repository with multiple stacks — manifests from several ecosystems aggregated in deterministic order.
6. Inspect a repository with ignored directories — ignored/generated dirs excluded from entries; exclusion summary counts them.
7. Inspect a repository containing symlinks/reparse points — symlinks classified (not followed), reported as metadata with a warning; link escapes never traversed.
8. Inspect a repository exceeding limits — budget exceeded → partial result with a stable `limit` reason and truncation summary; exit 0 unless an explicit error policy makes it a failure.
9. Inspect a path without read permission — resolved but not listable → `INSPECTION_PERMISSION_DENIED` error; sanitized message; exit code 3 (environment/config) — see §25.
10. Inspect a missing path — `PATH_NOT_FOUND`; exit code 2 (usage) or 3 depending on whether the path was explicit (see §25).
11. Text output — deterministic headings and summaries; no ANSI in JSON; ANSI disabled in text unless color requested.
12. JSON output — schema-versioned document; stable fields; no ANSI; sanitized paths.

For every flow: inputs, preconditions, policy decision, processing steps, result, warnings, exit behavior, side effects (none).

## 6. CLI contract

Command: `agent-harness inspect`

Arguments and options:

- `--path <PATH>` (optional; default: current working directory).
- `--output text|json` (Phase 1 global option, before the subcommand).
- `--verbose` (Phase 1 global option).
- `--no-color` (Phase 1 global option).
- `--max-entries <N>` (optional override; bounded; cannot disable mandatory limits).
- `--max-depth <N>` (optional override; bounded).
- `--git` (include read-only Git metadata; default on when a Git worktree is detected and git adapter succeeds).
- `--no-git` (explicitly skip Git metadata).

No content-reading option exists in Phase 3.

Exit codes (Phase 1 contract extended): `0` success (including partial results), `2` usage errors (invalid option/path argument), `3` configuration/environment errors (permission denied, invalid request bounds), `10` unexpected internal error. Git-metadata-unavailable is a warning, not an error, unless `--git` was explicitly required.

stdout: functional text or JSON. stderr: diagnostics and warnings (warnings also appear in the JSON result as a stable field). JSON has no ANSI. Deterministic ordering: entries sorted lexicographically by repository-relative path; summaries sorted by key.

Partial results: explicit `"partial": true` and a stable `limit` reason; exit 0.

## 7. Layering and dependency direction

- Domain/value contracts: `agent_harness/domain` (Phase 2) — reused; new inspection value objects live under `agent_harness/inspection` as immutable dataclasses but must not import CLI or Typer.
- Application orchestration: `agent_harness/application/inspection_service.py` — constructs the Phase 2 policy request, runs the walker, aggregates, builds the result.
- Filesystem inspection adapter: `agent_harness/infrastructure/inspector.py` — pure stdlib walker with containment, budgets, and classification.
- Optional Git metadata adapter: `agent_harness/infrastructure/git_metadata.py` — injected, read-only, subprocess-based, argument arrays only.
- CLI integration: `agent_harness/cli.py` — a new `inspect` command wired into the existing Typer app; exit-code translation at the boundary.
- Output models: `agent_harness/inspection/result.py` and `agent_harness/inspection/serialization.py`.
- Error translation: `agent_harness/inspection/errors.py` maps inspection failures to the Phase 1/2 exit-code contract.

Dependency direction points inward: CLI → application → domain; infrastructure → domain interfaces. Typer never enters domain/inspection value modules. Filesystem types stay in infrastructure; domain policy contracts use `TargetResource`-style references only.

Phase 2 contracts are reused directly: `inspect` maps to `Capability.REPOSITORY_METADATA_READ` in `READ_ONLY` mode; the policy engine must return `ALLOWED` before traversal begins.

## 8. Proposed package structure

```text
src/agent_harness/
├── application/
│   └── inspection_service.py
├── infrastructure/
│   ├── inspector.py
│   └── git_metadata.py
├── inspection/
│   ├── __init__.py
│   ├── errors.py
│   ├── request.py
│   ├── result.py
│   └── serialization.py
└── cli.py            (modified: add inspect command)
```

File purposes, public objects, dependencies, side effects, tests:

- `inspection/request.py` — `InspectionRequest` (immutable, validated), `InspectionLimits`, `LinkPolicy`, `SensitivePolicy`. Dependencies: stdlib only. Side effects: none. Tests: `tests/unit/inspection/test_request.py`.
- `inspection/result.py` — `InspectionResult`, `InspectionEntry`, `EntryKind`, `InspectionSummary`, `WarningRecord`, `LimitInfo`, `GitInfo`. Immutable dataclasses. Tests: `tests/unit/inspection/test_result.py`.
- `inspection/errors.py` — `InspectionError` hierarchy; stable reason codes. Tests: `tests/unit/inspection/test_errors.py`.
- `inspection/serialization.py` — JSON and text serializers (schema-versioned, deterministic). Tests: `tests/unit/inspection/test_serialization.py`.
- `infrastructure/inspector.py` — `Inspector` (bounded walker, containment, budgets, classification). Tests: `tests/unit/inspection/test_inspector.py`, `tests/integration/inspection/test_inspector_fs.py`.
- `infrastructure/git_metadata.py` — `GitMetadataReader` (injected, subprocess, arg arrays, no prompts/fetch). Tests: `tests/unit/inspection/test_git_metadata.py`.
- `application/inspection_service.py` — `InspectionService` (policy check, orchestration, partial handling). Tests: `tests/unit/inspection/test_inspection_service.py`.
- `cli.py` (modified) — `inspect` command. Tests: `tests/integration/test_cli_inspect.py`.
- `inspection/__init__.py` — public exports.

Minimal file count, clear boundaries.

## 9. Inspection request contract

`InspectionRequest` (immutable) fields:

- `requested_path: str` (default: current directory).
- `max_entries: int` (default 20,000; hard max 1,000,000).
- `max_directories: int` (default 2,000; hard max 100,000).
- `max_depth: int` (default 64; hard max 1,024).
- `max_individual_file_bytes: int` (default 100 MB; metadata-only, used to cap `st_size` reporting).
- `include_hidden: bool` (default False).
- `include_ignored: bool` (default False; if False, ignored entries are excluded and counted).
- `git_metadata: Literal["auto","on","off"]` (default "auto").
- `link_policy: Literal["classify","error"]` (default "classify"; never "follow").
- `error_policy: Literal["skip_warn","fail"]` (default "skip_warn" for per-entry errors; root errors always fail).

Defaults, validation (nonnegative, within hard bounds), bounds (hard maxima cannot be exceeded via CLI override), stable serialization (fixed field order), zero semantics: `0` means "no limit" only for `max_individual_file_bytes` in metadata mode; entry/depth limits must be ≥1. Mandatory limits that cannot be disabled: entry count, directory count, depth, path length (4,096), warnings (1,000).

## 10. Repository root resolution

Deterministic algorithm:

1. Normalize the requested path (expand user `~` is not performed; resolve relative against cwd).
2. Convert to an absolute, normalized path using `Path.resolve(strict=False)` with component-aware handling; reject if the logical path contains escapes that cannot be resolved deterministically.
3. If the path is a file, fail with `PATH_NOT_DIRECTORY` (usage error) unless the design later supports single-file inspection.
4. Determine repository type: look for `.git` (directory) or `.git` (file referencing a worktree) at the requested path, then upward up to the filesystem root; the first match is the repository root. A `.git` file is parsed only for its `gitdir:` line (metadata) — no Git commands.
5. Bare repository detection: if `.git` is a directory and `HEAD` exists with no working tree, classify as a bare repository; inspection of a bare repository reports only metadata (no working-tree entries).
6. Nested Git repository: if a nested `.git` is found during traversal, it is excluded as a nested-repository boundary (see §15); the inspection root remains the outer root.
7. Non-Git directory: inspection root = requested directory, `repository_type="directory"`.
8. Missing path → `PATH_NOT_FOUND`; permission denied during resolution/list → `INSPECTION_PERMISSION_DENIED`.

Git root discovery precedence: pure filesystem inspection first (`.git` marker); a read-only Git adapter is used only for branch/commit/status metadata, never for root discovery. No root resolution mutates Git state.

## 11. Path safety and containment

Central invariant: every emitted repository-relative path maps to an entry physically contained within the inspection root; nothing above the root is traversed, and no link outside the root is followed.

- Containment is resolved and checked before any content metadata is recorded.
- Escapes are rejected or excluded (never authorized).
- Never authorize using a string prefix alone: use path-component-aware containment (resolve the parent, then verify the child is strictly inside via resolved components).
- Recheck containment after resolution wherever links are involved (Phase 3 does not follow links, so the only recheck applies to the resolved root itself and to junction/reparse detection).
- Avoid TOCTOU assumptions: entry metadata is captured once; races are handled by the error policy (skip_warn or partial), never by re-reading paths.
- Never traverse above the root (walk starts at the root; `..` is never emitted).

Handling by case:

- `..`: normalized away during path resolution; any residual `..` that would escape the root is rejected.
- Absolute injected paths: treated as user-requested paths, resolved, then containment-checked; if they point outside the root they cannot be children of the walk.
- Drive changes: on Windows, only the drive of the resolved root is traversed.
- UNC paths: resolved and treated as absolute; containment applies.
- Case-insensitive Windows paths: normalization uses casefold for comparison; containment uses resolved absolute paths.
- Symlinks/junctions/reparse points: classified, never followed (see §12).
- Mount points: traversed only if inside the root; entry metadata records the mount as a boundary marker when detectable; no cross-mount following beyond the root.
- Hard links: treated as regular entries (metadata only; no content); no deduplication needed because content is not read.
- Link cycles: impossible to encounter as a cycle because links are not followed.
- Broken links: classified and reported with a warning.
- Relative symlink targets: never resolved for traversal in Phase 3.

Stable outcomes: symlinks → classified metadata + warning; link escape → never traversed; unsafe entries → skipped with warning; budget exceeded → partial.

## 12. Symlink, junction, and reparse-point policy

Cross-platform policy matrix:

| Entry type | Default traversal | Metadata emitted | Warning | Content read |
|---|---|---|---|---|
| Regular file | yes | yes | no | no |
| Directory | yes | yes | no | no |
| Symlink to file inside root | NO (classified) | yes | yes | no |
| Symlink to directory inside root | NO (classified) | yes | yes | no |
| Symlink outside root | NO | yes (classified) | yes (escape) | no |
| Broken symlink | NO | yes (classified) | yes | no |
| Windows junction | NO (classified) | yes | yes | no |
| Other reparse point | NO (classified) | yes | yes | no |
| Mount boundary | traversed only if inside root | yes (marker) | informational | no |
| Special device/FIFO/socket | NO | classified | yes | no |

Phase 3 never follows links; Windows junctions and reparse points are detected via `os.path.islink`/`stat` and the Windows `FILE_ATTRIBUTE_REPARSE_POINT` bit where the stdlib exposes it, and are treated exactly like POSIX symlinks (classified, not traversed). This avoids Unix-only assumptions.

## 13. Traversal algorithm

Deterministic pseudocode:

```
1. resolve_root(request) -> (inspection_root, repo_type)
2. policy = phase2.decide(READ_ONLY, REPOSITORY_METADATA_READ, root)   # must be ALLOWED
3. if policy not allowed: fail with policy reason
4. queue = [inspection_root]; entries = []; dirs_seen = 0; files_seen = 0; warnings = []
5. while queue and budgets not exceeded:
      path = queue.pop(0)            # FIFO, deterministic BFS
      if depth(path) > max_depth: mark and continue
      for child in sorted(listdir(path)):    # sorted lexicographically
          classify(child)
          if excluded/ignored: exclusion_summary += 1; continue
          if sensitive-name: add redacted entry; continue
          if unsupported type: warning += 1; continue
          if link/reparse: add classified entry + warning; continue
          if directory: dirs_seen += 1; if dirs_seen > max_directories: partial; else queue.append(child)
          if file: files_seen += 1; record metadata (path, size, type); if files_seen > max_entries: partial
6. if any budget exceeded: result.partial = true; result.limit = reason
7. aggregate languages, manifests, tests, docs, git metadata (adapter, if on)
8. sort entries and summaries; build result
```

- Traversal order: BFS FIFO; child order sorted by name (lexicographic, platform-independent casefold tie-break).
- Depth: BFS levels.
- Budget checks before recording each entry; limits stop cleanly with a partial result.
- Permission errors per entry → warning (or failure under `error_policy="fail"`).
- Race handling: stat-once; errors → skip_warn/partial.
- Duplicate physical entries: not possible because links are not followed and each real path is visited once.
- Cancellation point: none needed for bounded BFS (budgets bound the walk); timeouts are not part of Phase 3 (deferred).
- Memory bounds: entries stored as compact metadata; content never stored.

## 14. Inspection budgets

Mandatory safe limits:

| Limit | Default | Hard max | Disable allowed |
|---|---|---|---|
| Max entries | 20,000 | 1,000,000 | No |
| Max directories | 2,000 | 100,000 | No |
| Max depth | 64 | 1,024 | No |
| Max individual file bytes (metadata cap) | 100 MB | 10 GB | No |
| Max accepted path length | 4,096 | 4,096 | No |
| Max warnings retained | 1,000 | 1,000 | No |
| Max manifest count | 500 | 5,000 | No |
| Max language classifications | 100 | 1,000 | No |
| Time/cancellation boundary | not in Phase 3 (deferred) | — | — |

Defaults are configurable via request fields; CLI overrides are bounded by the hard maxima; a user can never request an effectively unbounded scan. Limit-exceeded outcomes are stable reason codes (`LIMIT_ENTRIES_EXCEEDED`, `LIMIT_DIRECTORIES_EXCEEDED`, `LIMIT_DEPTH_EXCEEDED`, `LIMIT_WARNINGS_EXCEEDED`) and always produce a partial result (not a silent failure).

## 15. Ignore and exclusion policy

Precedence (highest first):

1. Hard safety exclusions (never traversed, never reported): `.git/`; nested repository boundaries (`.git` markers); the inspection root itself is not an entry.
2. Explicit deny rules (Phase 2 allowlist deny rules, if applied to inspection targets).
3. User/project ignore rules: `.gitignore` only if the design opts into interpretation (decision: Phase 3 interprets a bounded subset — see below) and only when `include_ignored=False`.
4. Default generated-directory rules: `.venv/`, `venv/`, `node_modules/`, `bin/`, `obj/`, `dist/`, `build/`, `__pycache__/`, `.pytest_cache/`, `.mypy_cache/`, `.ruff_cache/`, `.coverage`, `htmlcov/`, `.tox/`, `.idea/`, `.vscode/`, package caches, temp files.
5. Explicit include requests: not supported in Phase 3 (include_hidden is metadata-only; ignored entries remain excluded).

Decision: `.gitignore` is NOT fully interpreted in Phase 3. Only the bounded default generated-directory rules and `.git/`/nested-repo exclusion are applied. Full `.gitignore` semantics are deferred to Phase 4. A future user-ignore option is deferred.

Git submodules: treated as nested repository boundaries → excluded.

## 16. Sensitive-file policy

Phase 3 never reads content. Sensitive-file handling is name-based only:

- Names matched: `.env`, `.env.*`, `*.pem`, `*.key`, `*.p12`, `*.pfx`, `id_rsa`, `id_ed25519`, `*.secret`, `credentials*`, `*token*`, cloud credential config names, SSH material, certificate/key stores, `*.jks`, `*.keystore`, `.npmrc`/`.pypirc` (may contain tokens).
- Behavior: the entry is listed with metadata, but the filename is redacted to a stable token (`<sensitive:<sanitized-index>>`) in output; a `sensitive_entries` count is reported; no content is read or printed.
- The inspector never prints file contents merely because a filename is discovered.
- Secret scanning and secret extraction are distinct future responsibilities, not part of inspection.

## 17. Content-reading policy

Phase 3 does NOT read file content. The roadmap explicitly defers reading to Phase 4 ("Deferred: Search, reading, mapping, command execution"). Therefore:

- No text/binary/encoding detection from content.
- No shebang parsing.
- Binary detection is name/extension heuristic only (`BINARY_EXTENSIONS` set and NUL-byte-free name assumption is not used because content is not read).
- No truncation of content (no content).
- No model or network receives file content.

This is a deliberate scope decision aligned with the roadmap.

## 18. File-type and language detection

Deterministic, metadata-only classification:

- File extension mapping to a stable language identifier (`LANGUAGES` map: `.py→python`, `.ts→typescript`, `.js→javascript`, `.go→go`, `.rs→rust`, `.java→java`, `.cs→csharp`, `.c→c`, `.h→c`, `.cpp→cpp`, `.rb→ruby`, `.php→php`, `.swift→swift`, `.kt→kotlin`, `.md→markdown`, `.json→json`, `.yaml/.yml→yaml`, `.toml→toml`, `.sh→shell`, `.sql→sql`, `.html→html`, `.css→css`, `.scss→scss`, `.vue→vue`, `.svelte→svelte`, `.ipynb→jupyter`, `.proto→protobuf`, etc.).
- Exact filenames: `Dockerfile`, `Makefile`, `Justfile`, `LICENSE`, `README*`.
- No shebang (no content read).
- Multiple possible languages: first deterministic match by priority; unknown types → `unknown`.
- Generated/minified/template/notebook/lock-file entries are classified as generated or specific types; minified `.min.js` → `javascript`; lock files → `lockfile`.
- Stable identifiers and aggregation: language counts sorted by count desc then name asc.

No semantic understanding is claimed.

## 19. Manifest and stack detection

Phase 3 recognizes manifests by exact filename (no parsing, no content read):

- `pyproject.toml` (python)
- `requirements*.txt` (python)
- `package.json` (javascript)
- `*.csproj` (dotnet)
- `*.sln` (dotnet)
- `pom.xml` (java)
- `build.gradle*` (java)
- `go.mod` (go)
- `Cargo.toml` (rust)
- `Dockerfile` (container)
- `docker-compose*.yml` / `compose*.yml` (container)
- Terraform files: `*.tf` (terraform)

Matching: exact/prefix filename matching within budgets; contents never parsed; invalid manifests are not detected (no parsing); duplicates and nested projects are all reported (bounded by manifest count); output lists each manifest with its repository-relative path and detected ecosystem.

## 20. Git metadata boundary

Read-only Git metadata in Phase 3:

| Item | Classification |
|---|---|
| Is a Git worktree | IN_SCOPE (filesystem `.git` marker) |
| Repository root | IN_SCOPE |
| Current branch / detached HEAD | IN_SCOPE (adapter) |
| Current commit | IN_SCOPE (adapter) |
| Dirty state | IN_SCOPE (adapter: `git status --porcelain` bounded) |
| Tracked/untracked counts | IN_SCOPE (derived from bounded status output) |
| Submodule presence | DEFERRED (nested-repo exclusion only) |

Git adapter constraints: injected `GitMetadataReader`; uses only non-mutating commands (`rev-parse --abbrev-ref HEAD`, `rev-parse --short HEAD`, `status --porcelain`, `symbolic-ref --quiet --short HEAD`); argument arrays (never shell strings); `GIT_TERMINAL_PROMPT=0` and `GIT_ASKPASS=/bin/true`-style no-prompt guard where available; bounded output (status capped at a line limit); sanitized errors; `--no-optional-locks` to avoid touching index/refs where supported; timeouts when supported; never fetch; never contact remotes; never alter configuration; never traverse credential helpers. If the adapter fails, Git metadata is omitted with a warning (unless `--git` was explicit, in which case the warning is still non-fatal).

## 21. Phase 2 policy integration

- Capability: `Capability.REPOSITORY_METADATA_READ` (already in the Phase 2 taxonomy).
- Action name: `ActionName(Capability.REPOSITORY_METADATA_READ, ActionCategory.READ, target)`.
- Category: `READ`.
- Target: `TargetResource(ref=repository_relative_or_absolute_root, resource_type="repository")`.
- Required mode: `READ_ONLY` (default).
- Canonical scope: `action_scope(action)` (already defined) — approvals are never required for reads.
- Hard prohibitions: none by default for this capability; the configured engine applies them.
- Allowlist application: reads are governed by mode; the Phase 2 engine returns `ALLOWED` for READ in `READ_ONLY` without allowlist/approval.
- Policy request construction: `PolicyRequest(mode=READ_ONLY, action=..., target=..., allowlist_result=None, approval=None)`.
- Decision handling: if not `ALLOWED`, inspection is not performed and the policy reason is surfaced; inspection never authorizes write, delivery, Git mutation, network, or model actions.

No Phase 2 contract modification is required.

## 22. Result model

`InspectionResult` (immutable) contains:

- `schema_version: int` (1)
- `requested_path` (sanitized; absolute only if privacy model permits — see §29)
- `resolved_root` (repository-relative representation; absolute only with `--output text` and opt-in; JSON omits machine-specific absolute paths by default)
- `repository_type: "git_worktree" | "git_bare" | "directory"`
- `inspection_status: "ok" | "partial"`
- `partial: bool`
- `file_count`, `directory_count`
- `total_metadata_size` (sum of st_size where available)
- `content_bytes_read: 0` (Phase 3 never reads content)
- `language_summary` (sorted)
- `manifest_summary` (sorted)
- `test_directory_count`
- `documentation_count`
- `git` (GitInfo: branch, commit, dirty, tracked/untracked counts, or absent)
- `exclusion_summary` (counts by category)
- `sensitive_entries` (count)
- `limit_info` (partial reason when partial)
- `warnings` (bounded list of `WarningRecord`)
- `entries` (bounded list of `InspectionEntry` — repository-relative path, kind, size, classification)

Deterministic ordering everywhere. No timestamps (or injected clocks only if required by a future phase).

## 23. JSON contract

- Schema version: 1 (field `schema_version`).
- Required fields: schema_version, status, partial, counts, entries.
- Optional fields: language_summary, manifest_summary, git, warnings, limit_info.
- Null behavior: absent optional fields omitted (no `null` for empty; empty collections serialize as `[]`/`{}`).
- Path separators normalized to the platform separator in `repository_relative_path`; JSON strings use forward-compatible escaping.
- Ordering: entries and summaries deterministic (sorted).
- Numeric bounds: counts as ints; sizes as ints.
- Enum serialization: stable string values (e.g., `"file"`, `"directory"`, `"symlink"`).
- Warning representation: `{"code": "...", "message": "..."}` sanitized.
- Partial-result representation: `"status": "partial"`, `"partial": true`, `"limit": {"code": "...", "limit": N, "count": M}`.
- Error representation: `{"error": {"code": "...", "message": "..."}}` on stderr/stdout per exit contract.
- ANSI prohibition: JSON output never contains ANSI.
- Secret redaction: sensitive entries are redacted in output.
- Forward-compatibility: additive-only fields; unknown fields ignored.

Examples:

Successful minimal:

```json
{"schema_version": 1, "status": "ok", "partial": false, "repository_type": "directory", "file_count": 1, "directory_count": 0, "total_metadata_size": 12, "content_bytes_read": 0, "entries": [{"repository_relative_path": "README.md", "kind": "file", "size": 12, "classification": "documentation"}]}
```

Multi-stack partial/truncated and failure examples are provided in the serialization unit tests (no real sensitive data).

## 24. Text-output contract

- Headings: stable (e.g., `Repository`, `Status`, `Files`, `Directories`, `Languages`, `Manifests`, `Git`, `Warnings`, `Limits`).
- Summary fields stable and deterministic.
- Entry display limited to a bounded number of lines (default 200) followed by a truncation note.
- Warning formatting: `warning: <code>: <message>` on stderr and in text output.
- Partial marker: `status: partial (reason: <code>)`.
- Path sanitization: sensitive filenames redacted; no machine-specific absolute paths unless opted in.
- stdout/stderr separation: functional output on stdout; diagnostics/warnings on stderr.
- Verbose: additional detail on stderr only.
- No ANSI in JSON; text color only when color enabled (Phase 1 `--no-color` honored).
- Deterministic ordering.

## 25. Error taxonomy

New errors under `inspection/errors.py` (subclass `DomainError` where domain-facing, or application errors at the boundary):

| Error | Domain/App | Reason code | Exit | Text | JSON | Partial allowed |
|---|---|---|---|---|---|---|
| Path not found | App | `PATH_NOT_FOUND` | 2 | sanitized | error object | no |
| Path not a directory | App | `PATH_NOT_DIRECTORY` | 2 | sanitized | error object | no |
| Not a repository (non-Git directory) | App | `NOT_A_REPOSITORY` (informational; treated as directory inspection) | 0 | note | repository_type="directory" | n/a |
| Permission denied | App | `INSPECTION_PERMISSION_DENIED` | 3 | sanitized | error object | no |
| Root resolution failure | App | `ROOT_RESOLUTION_FAILED` | 3 | sanitized | error object | no |
| Path escape | App | `PATH_ESCAPE` | 2 | sanitized | error object | no |
| Unsupported entry | App | `UNSUPPORTED_ENTRY` | 0 (skip_warn) / 10 (fail) | warning/error | warning/error | yes |
| Link/reparse warning | App | `LINK_NOT_FOLLOWED` | 0 | warning | warning | yes |
| Budget exceeded | App | `LIMIT_<...>_EXCEEDED` | 0 | partial note | limit object | yes |
| Too many warnings | App | `LIMIT_WARNINGS_EXCEEDED` | 0 | partial note | limit object | yes |
| Invalid request/config | App | `INVALID_INSPECTION_REQUEST` | 3 | sanitized | error object | no |
| Git metadata unavailable | App | `GIT_METADATA_UNAVAILABLE` | 0 | warning | warning | yes |
| Concurrent filesystem change | App | `FILESYSTEM_CHANGED` | 0 | warning | warning | yes |
| Unexpected inspection failure | App | `INSPECTION_INTERNAL_ERROR` | 10 | sanitized | error object | no |

Raw path values are sanitized (control chars stripped, sensitive names redacted) in all error and warning output.

## 26. Filesystem race behavior

- File deleted after enumeration: metadata may still be emitted (from the stat snapshot); no retry.
- File replaced by symlink: the walker classifies on first stat; if a race changes the type, the recorded snapshot stands; no re-read.
- Directory replaced: same rule.
- Permission changes: per-entry errors → skip_warn (or partial).
- File size changes: recorded size is the stat-once value; no re-stat.
- Content changes: not read; no effect.
- Link target changes: links are not followed; no effect beyond classification snapshot.
- Entry type changes: snapshot rule.

No unsafe retry loops; races produce warnings or partial results, never authorization changes.

## 27. Determinism

For an unchanged repository and identical request:

- Entry ordering stable (sorted).
- Summary ordering stable (sorted).
- Warning ordering stable (encounter order, which is deterministic BFS).
- Language ordering stable (count desc, name asc).
- Manifest ordering stable (path asc).
- JSON bytes stable where practical (fixed field order, sorted collections).
- Machine-specific nondeterminism documented: absolute paths are excluded from JSON by default; `git commit` short hash may vary only if the repository changes; no timestamps are emitted.
- Timestamps excluded from output entirely in Phase 3.

## 28. Performance and memory

- Complexity: O(entries) with bounded budgets; BFS queue is bounded by directories and depth.
- Large monorepositories: budgets produce partial results before resource exhaustion.
- Deep trees: depth budget.
- Many small files: entry budget.
- Large binary files: metadata-only; size cap prevents oversized stat reporting only if enabled.
- Network-mounted directories: no special handling; budgets apply; slow entries are bounded by the walk stopping at limits.
- Memory: compact per-entry metadata; content never stored.
- Incremental aggregation: languages/manifests/warnings aggregated during traversal.
- No parallel traversal (deterministic single walk); concurrency is deferred to later phases.

## 29. Privacy model

- Displayed paths: repository-relative paths by default.
- Absolute paths: omitted from JSON by default; text output may show the resolved root only when explicitly requested (`--show-root` is not added; instead text output may print the root, which is the user's own path).
- Redacted filenames: sensitive entries redacted.
- Repository contents: never appear (no content read).
- File hashes: not calculated in Phase 3 (deferred).
- User identity / machine names: not collected; absolute paths excluded from JSON.
- Git remote URLs: NOT inspected.
- Git author data: NOT inspected.

Default minimizes personal and environmental disclosure.

## 30. Threat model

| Threat | Boundary | Prevention | Detection | Residual risk | Future owner |
|---|---|---|---|---|---|
| Path traversal (`../`) | root | component-aware containment, normalization | budget/walk validation | low | Phase 4 |
| Symlink escape | root | links never followed | classification | none in Phase 3 | Phase 4 |
| Junction/reparse escape | root | never followed | Windows reparse detection | low on exotic filesystems | Phase 4 |
| Link cycles | root | links not followed | n/a | none | — |
| Special/device files | traversal | classified, skipped | unsupported-entry warning | none | sandbox phase |
| Oversized repositories | budgets | mandatory limits | partial result | acceptable | Phase 11 |
| Zip bombs / archives | content | no content read | n/a | none | Phase 4 |
| Secret disclosure | output | sensitive-name redaction | sensitive-file policy | name-based only | security phase |
| Binary disclosure | output | no content read | n/a | none | Phase 4 |
| Error-message injection | output | sanitized messages | control-char stripping | low | — |
| ANSI/control injection | output | sanitization, no ANSI in JSON | tests | low | — |
| Unicode path confusion | containment | exact-component comparison | tests | low on exotic encodings | Phase 5 |
| TOCTOU | traversal | stat-once snapshot | race warnings | acceptable | Phase 11 |
| Permission races | traversal | error policy | warnings | acceptable | — |
| Git prompt/credential helper | git adapter | no-prompt env, arg arrays, no fetch | adapter tests | low | Phase 16 |
| Malicious manifest content | manifest | no content parsing | n/a | none | Phase 5 |
| Malicious filenames | output | sanitized output | tests | low | — |
| Denial of service | budgets | mandatory limits | partial result | acceptable | — |
| Hidden network access | root | none; no network code | static scan | none | — |
| Hidden model invocation | root | none; no model code | static scan | none | Phase 7 |

## 31. Security invariants

1. Inspection never modifies the repository.
2. Inspection never follows a link outside the root.
3. Inspection never traverses above the root.
4. Inspection never invokes a model.
5. Inspection never accesses the network.
6. Inspection never mutates Git.
7. Inspection never prints sensitive content by default.
8. Inspection always uses finite budgets.
9. Unknown entry types fail closed.
10. Malformed paths do not broaden access.
11. JSON contains no ANSI.
12. Expected errors contain no traceback.
13. Partial results are explicitly marked.
14. Repository-relative paths are deterministic.
15. Phase 2 policy authorizes the inspection before traversal.

## 32. Testing strategy

### Unit tests

- Request validation (defaults, bounds, zero semantics).
- Root resolution (cwd, explicit path, nested path, `.git` file worktree, bare repo, non-Git dir, missing path).
- Path containment (component-aware, `..`, absolute injection, drive/UNC, casefold).
- Relative-path normalization and sorting.
- Budgets (each limit, partial marking, reason codes).
- Ignore precedence (hard exclusions > deny > default generated rules).
- Sensitive-file classification and redaction.
- Binary detection (name/extension heuristics).
- Language detection (map coverage, unknown, minified, lockfiles).
- Manifest detection (each recognized manifest, nested, duplicates, budget).
- Result serialization (JSON fields, ordering, redaction, partial/error representation).
- Error mapping (each error → reason code + exit code).
- Phase 2 policy mapping (READ_ONLY ALLOWED; denial blocks inspection).

### Filesystem integration tests

- Empty repository.
- Small mixed repository.
- Nested repository (outer root, inner excluded).
- Missing path.
- Permission denied (where the platform supports it).
- Deep tree (depth budget).
- Large file (metadata only).
- Many files (entry budget).
- Symlink inside root (classified, not followed).
- Symlink outside root (classified, never traversed).
- Broken symlink.
- Symlink cycle (impossible to follow; classification path tested).
- Junction/reparse point on Windows where feasible (classification).
- Concurrent deletion (skip_warn/partial).
- File-to-link replacement where feasible.
- Special file on supported platforms (FIFO/socket classification).
- Hidden files.
- Ignored directories (excluded + counted).
- Sensitive filenames (redacted).
- Unicode filenames.
- Control-character filenames where supported (sanitized).

### CLI tests

- Help.
- Text success.
- JSON success.
- Invalid path (exit 2).
- Partial result (limit exceeded, exit 0, marked partial).
- Limit exceeded via option.
- Deterministic output (two runs identical).
- stdout/stderr separation.
- Exit codes.
- No ANSI in JSON.
- Sanitized errors.
- Phase 1 command regression.

### Security tests

- Path traversal attempts.
- Root escape attempts.
- Symlink escape.
- Prefix-collision containment.
- Case behavior.
- UNC or drive changes (Windows).
- Malicious manifest (no parsing).
- Secret-bearing filename (redacted, no content).
- Oversized input (bounded).
- Control-character injection (sanitized).
- No Git mutation (state checks around the adapter).
- No network (static scan + no sockets).
- No model call (static scan).
- No working-directory side effect.

## 33. Coverage requirements

- Full suite passes.
- Line coverage ≥90%.
- Branch coverage ≥85%.
- Changed-lines coverage 100% where practical.
- Path containment and link-handling branches 100%.
- Security-critical error branches 100%.
- No platform-specific branch left unexplained (Windows-only branches documented and covered by platform-gated tests where CI supports them).

## 34. Implementation sequence

1. Contracts and request/result models (`inspection/request.py`, `inspection/result.py`, `inspection/errors.py`).
2. Path normalization and containment.
3. Entry classification.
4. Bounded traversal (`infrastructure/inspector.py`).
5. Ignore and sensitive-file policy.
6. Language and manifest aggregation.
7. Optional read-only Git metadata adapter (`infrastructure/git_metadata.py`).
8. Application orchestration (`application/inspection_service.py`).
9. Phase 2 policy integration.
10. CLI integration (`cli.py` `inspect` command).
11. Output formatting (`inspection/serialization.py`).
12. Unit, integration, CLI, and security tests.
13. Documentation update only if the implementation phase authorizes it.
14. Independent QA and security review.

## 35. Exact implementation file plan

Production files (create unless noted):

- `src/agent_harness/inspection/__init__.py` — public exports.
- `src/agent_harness/inspection/request.py` — `InspectionRequest`, `InspectionLimits`, `LinkPolicy`, `SensitivePolicy`.
- `src/agent_harness/inspection/result.py` — `InspectionResult`, `InspectionEntry`, `EntryKind`, `InspectionSummary`, `WarningRecord`, `LimitInfo`, `GitInfo`.
- `src/agent_harness/inspection/errors.py` — `InspectionError` hierarchy + reason codes.
- `src/agent_harness/inspection/serialization.py` — JSON/text serializers.
- `src/agent_harness/infrastructure/inspector.py` — `Inspector`.
- `src/agent_harness/infrastructure/git_metadata.py` — `GitMetadataReader`.
- `src/agent_harness/application/inspection_service.py` — `InspectionService`.
- `src/agent_harness/cli.py` (MODIFIED) — add `inspect` command.

Test files (create):

- `tests/unit/inspection/test_request.py`
- `tests/unit/inspection/test_result.py`
- `tests/unit/inspection/test_errors.py`
- `tests/unit/inspection/test_serialization.py`
- `tests/unit/inspection/test_inspector.py`
- `tests/unit/inspection/test_git_metadata.py`
- `tests/unit/inspection/test_inspection_service.py`
- `tests/integration/inspection/test_inspector_fs.py`
- `tests/integration/test_cli_inspect.py`

No other production or test files are authorized.

## 36. Dependency decision

- Decision: `NO_NEW_DEPENDENCY`.
- The standard library (`pathlib`, `os`, `stat`, `enum`, `dataclasses`, `subprocess` for the injected Git adapter) is sufficient for Phase 3.
- If implementation reveals a need, the dependency must be justified separately, approved, and added only in the implementation phase.

## 37. Deferred decisions

- Semantic code analysis.
- AST parsers.
- Build-system execution.
- Dependency graph resolution.
- Test execution.
- Persistent snapshots.
- Hashing.
- Repository index.
- File watchers.
- Remote repositories.
- GitHub.
- Tickets.
- RAG.
- LLM.
- Worktrees.
- Sandboxes.
- Write actions.
- Delivery actions.

## 38. Acceptance criteria for implementation

`AH-03-IMP-01` is accepted only when:

- `agent-harness inspect` (text and JSON) works for a Git worktree and a non-Git directory.
- Inspection never modifies the repository (asserted by tests: file mtimes/contents and Git state unchanged).
- Repository-relative paths are emitted deterministically and sorted.
- Symlinks, junctions/reparse points (where detectable), and special entries are classified and never followed.
- Path escapes, root escapes, and prefix-collision containment attempts are rejected.
- Sensitive filenames are redacted; no file content is ever read or printed.
- All mandatory budgets are enforced; exceeding any budget yields an explicit partial result with a stable reason code.
- `.git/` and nested repository boundaries are excluded.
- `README`/manifests/languages/test/docs classification is deterministic and matches the spec maps.
- Phase 2 policy (READ_ONLY, `REPOSITORY_METADATA_READ`) is evaluated before traversal; a non-ALLOWED decision blocks inspection.
- Phase 1 CLI commands and exit codes are unchanged.
- Full suite passes; line ≥90%; branch ≥85%; containment/link/security branches 100%.
- No dependency, network, model, or Git mutation.
