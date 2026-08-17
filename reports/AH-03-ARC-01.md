# AH-03-ARC-01 — Safe Repository Inspection Architecture Report

## 1. Result

- Status: COMPLETED
- Timestamp: 2026-08-14
- Repository: germana2022/agent-harness-cli
- Git root: D:/agente-harness
- Branch: feature/ah-03-repository-inspection
- Base commit: 7a46b54f47f542d1c6d37f8e38343958c917eb83
- Execution mode: WRITE_CONTROLLED_LOCAL

## 2. Preconditions

| Check | Result | Evidence |
|---|---|---|
| Git root | D:/agente-harness | `git rev-parse` |
| Starting branch | main | `git branch --show-current` |
| Local main | 7a46b54... | `git rev-parse main` |
| Origin main | 7a46b54... | `git rev-parse origin/main` |
| Remote main | 7a46b54... | `git ls-remote origin refs/heads/main` |
| Working tree | clean | `git status --short` |
| Staged files | none | `git diff --cached` |
| Unexpected untracked files | none | `git ls-files --others` |
| Local feature branch | absent | `git branch --list` |
| Remote feature branch | absent | `git ls-remote --heads` |
| Existing Pull Request | none | `gh pr list` |
| Phase 2 merge present | yes | domain package in main |

## 3. Files

### Created

- `docs/PHASE_03_SAFE_REPOSITORY_INSPECTION_DESIGN.md`
- `reports/AH-03-ARC-01.md`

### Modified

- None.

### Unexpected

- None.

## 4. Roadmap alignment

- Authoritative Phase 3 wording: "Read-only repository inspection with strict boundaries"; deliverables "Repository inspector, allowlist rules, safe traversal, metadata reporting"; exit gate "Inspector reports repository metadata without modifying anything"; deferred "Search, reading, mapping, command execution".
- In-scope capabilities: metadata inventory, repository-relative paths, sizes, extension-based type/language/manifest/test/docs classification, ignore/exclusion summaries, budgets, read-only Git metadata (branch/commit/dirty), READ_ONLY policy gating, `inspect` CLI command.
- Deferred capabilities: file content reading (Phase 4), exact search (Phase 4), repository map and symbol analysis (Phase 5), command execution (never in Phase 3).
- Prohibited capabilities: Git mutation, remote/GitHub inspection, network, model invocation, sandbox/worktree, secret extraction.
- Scope conclusion: aligned with the roadmap; content reading is explicitly deferred.

## 5. Architecture decisions

| Decision | Result | Rationale |
|---|---|---|
| Supported inspection roots | Git worktrees AND non-Git directories | roadmap "local repository inspection"; non-Git handled deterministically |
| Default path | current working directory | consistent with CLI-first use |
| Repository-root resolution | pure filesystem `.git` marker; read-only Git adapter only for branch/commit/status metadata | no Git mutation |
| Content-reading policy | NO content read in Phase 3 | roadmap defers reading to Phase 4 |
| Git metadata policy | read-only adapter (branch, short commit, porcelain dirty state); injected, arg arrays, no-prompt, no fetch | metadata only |
| Ignore policy | bounded default generated-directory rules + `.git/` + nested-repo exclusion; `.gitignore` NOT interpreted in Phase 3 | full Git ignore semantics deferred to Phase 4 |
| Symlink policy | classified, never followed | containment |
| Junction/reparse policy | detected and classified like symlinks (never followed) | cross-platform safety |
| Hard-link policy | treated as regular entries (metadata only) | no content read |
| Sensitive-file policy | name-based redaction of metadata; never content | secret-disclosure prevention |
| Resource budgets | mandatory bounded limits (entries 20k, dirs 2k, depth 64, path 4096, warnings 1k); hard maxima; cannot disable | denial-of-service prevention |
| Partial-result policy | budget exceedance → explicit partial result with stable reason code; exit 0 | deterministic outcomes |
| Determinism | sorted entries/summaries, no timestamps, absolute paths excluded from JSON | reproducibility |
| Absolute-path disclosure | repository-relative by default; JSON omits machine-specific absolute paths | privacy |
| JSON schema | version 1, additive-only, no ANSI, redaction, stable ordering | contract stability |
| CLI command | `agent-harness inspect` with `--path`, `--git/--no-git`, bounded `--max-entries/--max-depth` | minimal surface |
| Phase 2 policy mapping | `Capability.REPOSITORY_METADATA_READ` in READ_ONLY; policy checked before traversal | reuse existing contracts, no Phase 2 change |
| Dependency decision | NO_NEW_DEPENDENCY | stdlib sufficient |

## 6. Proposed implementation

### Production files

- `src/agent_harness/inspection/__init__.py`
- `src/agent_harness/inspection/request.py`
- `src/agent_harness/inspection/result.py`
- `src/agent_harness/inspection/errors.py`
- `src/agent_harness/inspection/serialization.py`
- `src/agent_harness/infrastructure/inspector.py`
- `src/agent_harness/infrastructure/git_metadata.py`
- `src/agent_harness/application/inspection_service.py`
- `src/agent_harness/cli.py` (MODIFIED: add `inspect` command)

### Test files

- `tests/unit/inspection/test_request.py`
- `tests/unit/inspection/test_result.py`
- `tests/unit/inspection/test_errors.py`
- `tests/unit/inspection/test_serialization.py`
- `tests/unit/inspection/test_inspector.py`
- `tests/unit/inspection/test_git_metadata.py`
- `tests/unit/inspection/test_inspection_service.py`
- `tests/integration/inspection/test_inspector_fs.py`
- `tests/integration/test_cli_inspect.py`

### Existing files to modify

- `src/agent_harness/cli.py` (add the `inspect` command only).

### Dependency direction

CLI → application → domain; infrastructure → domain interfaces; Typer never enters inspection value modules.

## 7. Security model

- Trust boundaries: the inspector treats the filesystem as untrusted; the domain/policy layer is the trust boundary; the Git adapter is read-only and promptless.
- Containment invariant: every emitted path is physically inside the inspection root; nothing above the root; no link followed.
- Link-escape prevention: symlinks/junctions/reparse points classified, never followed.
- Secret-disclosure prevention: sensitive names redacted; no content read; no secrets in output.
- Resource-exhaustion prevention: mandatory bounded budgets with partial results.
- Git/network/model prohibition: no fetch, no remotes, no network, no model; static scans enforce.
- Residual risks: name-based sensitive detection (content-based is future); exotic filesystem race handling (snapshot semantics); Windows-only reparse behavior platform-gated.

## 8. CLI and output contract

- Command: `agent-harness inspect`.
- Arguments: none positional; `--path <PATH>` optional.
- Options: `--git`, `--no-git`, bounded `--max-entries`, `--max-depth`; Phase 1 global `--output/--verbose/--no-color` before the subcommand.
- Text output: stable headings and summaries; bounded entry display; warnings on stderr; partial marker.
- JSON output: schema v1, deterministic, no ANSI, redacted sensitive names, partial/limit/error representations.
- Exit codes: 0 success (incl. partial), 2 usage, 3 config/environment, 10 internal.
- Partial results: `"status":"partial"` + `"limit"` reason; exit 0.
- Deterministic ordering: entries/summaries sorted; no timestamps.

## 9. Testing and coverage plan

- Unit tests: request, root resolution, containment, normalization, sorting, budgets, ignore precedence, sensitive classification, binary/language/manifest detection, serialization, error mapping, Phase 2 policy mapping.
- Filesystem integration tests: empty/mixed/nested repo, missing/permission-denied paths, deep/large/many files, symlink inside/outside/broken/cycle, junction/reparse (Windows-feasible), races, special files, hidden/ignored/sensitive/unicode/control-character names.
- CLI tests: help, text/JSON success, invalid path, partial/limit, determinism, stdout/stderr, exit codes, no ANSI in JSON, sanitized errors, Phase 1 regression.
- Security tests: traversal/root-escape/symlink-escape/prefix-collision/case/UNC/drive, malicious manifest, secret-bearing filename, oversized input, control-character injection, no Git mutation, no network, no model, no side effect.
- Coverage gates: line ≥90%, branch ≥85%, changed-lines 100% where practical, containment/link/security branches 100%, platform branches documented.

## 10. Validation

| Check | Result | Evidence |
|---|---|---|
| Required design sections | 38/38 present | heading count |
| Required architecture decisions | 24/24 answered | design + report |
| Roadmap alignment | PASS | content reading deferred to Phase 4 |
| Path containment design | PASS | component-aware, recheck, no string-prefix |
| Symlink/reparse design | PASS | classified, never followed; cross-platform matrix |
| Resource-budget design | PASS | mandatory bounded limits, hard maxima |
| Sensitive-file design | PASS | name-based redaction, no content |
| Phase 2 policy integration | PASS | REPOSITORY_METADATA_READ/READ_ONLY reused; no contract change |
| CLI compatibility | PASS | Phase 1 global options and exit codes preserved |
| Dependency scope | PASS | NO_NEW_DEPENDENCY |
| Markdown validation | PASS | section headings valid |
| Secret scan | CLEAN | pattern scan |
| Diff scope | PASS | only the two authorized untracked files |

## 11. Git state

- Current branch: feature/ah-03-repository-inspection
- HEAD: 7a46b54...
- Feature commits: 0
- Staged files: none
- Working tree: clean except the two authorized untracked files
- Authorized untracked files: `docs/PHASE_03_SAFE_REPOSITORY_INSPECTION_DESIGN.md`, `reports/AH-03-ARC-01.md`
- Unexpected files: none
- Remote operations: none
- GitHub operations: none

## 12. Warnings

- The remote Phase 2 branch `feature/ah-02-domain-contracts` still exists on origin; observed, not modified (non-blocking cleanup).

## 13. Blockers

- None.

## 14. Commands executed

- Git read-only checks (`git rev-parse`, `git branch --show-current`, `git status --short`, `git ls-remote`, `git ls-files --others`); `git switch -c feature/ah-03-repository-inspection`
- `gh pr list`
- Roadmap/design section, markdown, and secret-pattern validation
- No credentials, tokens, or sensitive file content output.

## 15. Recommended next action

PROCEED_TO_AH-03-IMP-01

The Phase 3 architecture is complete, roadmap-aligned (metadata-only inspection; content reading deferred to Phase 4), and fully specified across containment, symlink/reparse handling, mandatory budgets, sensitive-file redaction, Git metadata boundaries, Phase 2 policy integration, CLI/JSON contracts, testing, and an exact file plan. The design leaves no material implementation ambiguity, and the feature branch is ready for the implementer.

## 16. Non-modification attestation

- Only the two authorized documentation files were created.
- No existing file was modified.
- No production code or test was created.
- No dependency was added, removed, installed, or updated.
- No file was staged.
- No commit was created.
- No push or remote branch was created.
- No Pull Request or GitHub resource was modified.
- The remaining remote Phase 2 branch was not modified or deleted.
- No credential, secret, or sensitive file content was exposed.
