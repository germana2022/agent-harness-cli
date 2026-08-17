# AH-03-TST-01 — Independent Safe Repository Inspection QA Report

## 1. Decision

- Decision: PASS_WITH_WARNINGS
- Timestamp: 2026-08-14
- Repository: germana2022/agent-harness-cli
- Git root: D:/agente-harness
- Branch: feature/ah-03-repository-inspection
- Base commit: 7a46b54f47f542d1c6d37f8e38343958c917eb83
- Execution mode: WRITE_CONTROLLED_REPORT_ONLY

## 2. Preconditions

| Check | Result | Evidence |
|---|---|---|
| Git root | D:/agente-harness | `git rev-parse` |
| Current branch | feature/ah-03-repository-inspection | `git branch --show-current` |
| HEAD | 7a46b54... | `git rev-parse HEAD` |
| Base commit | 7a46b54... | match |
| Feature commits | 0 | `git rev-list --count main..HEAD` |
| Staged files | none | `git diff --cached` |
| Tracked modifications | only `src/agent_harness/cli.py` | `git diff --name-only` |
| Untracked files | Phase 3 design/report + new packages + tests | `git ls-files --others` |
| Remote Phase 3 branch | absent | `git ls-remote --heads` |
| Existing Phase 3 Pull Request | none | `gh pr list` |
| Dependency state | unchanged | `pyproject.toml` untouched |
| `git diff --check` | clean | exit 0 |

## 3. Scope and diff review

- Created: 10 production modules (inspection, infrastructure, application), 9 test modules, design + ARC + IMP reports.
- Modified: `src/agent_harness/cli.py` (inspect command only).
- No Phase 1/Phase 2 file modified; no dependency change; no unexpected file.
- Justified refinements: `test_inspection_errors.py` renamed from `test_errors.py` (pytest module-name collision with Phase 2); a transient inspection `conftest.py` was removed for the same reason (helpers inlined). No Phase 2 test modified.
- Scope result: conforms to the architecture file plan.

## 4. Architecture conformance

| Decision | Result | Evidence |
|---|---|---|
| Git + non-Git roots | conform | resolver + tests |
| Current-directory default | conform | CLI default `--path .` |
| Root resolution | conform | lexical normalize, link rejection, `.git` marker |
| Metadata-only | conform | open-spy: zero calls |
| Ignore behavior | conform | hard + generated rules; `include_ignored` |
| Nested-repo exclusion | conform | integration test |
| Symlink policy | conform | classified, never followed |
| Junction/reparse policy | conform | reparse-tag classification |
| Hard-link treatment | conform | ordinary metadata entries (no content) |
| Sensitive-name handling | conform (one LOW gap, see §17) | redaction tests |
| Mandatory budgets/hard maxima | conform | request validation + walker |
| Partial results | conform | explicit `limit` + exit 0 |
| Deterministic ordering | conform | sorted BFS + summaries |
| Absolute-path disclosure | conform | JSON omits; relative paths |
| JSON schema v1 | conform | serialization |
| CLI options/exit codes | conform | 0/2/3/10 |
| Phase 2 policy mapping | conform | `REPOSITORY_METADATA_READ`/READ_ONLY |
| Dependency direction | conform | CLI→application→domain; infra→interfaces |
| Framework isolation | conform | stdlib-only value modules |

## 5. Metadata-only validation

- Independent `open` spy on the public service path: zero `open` calls during a full inspection of a fixture containing ordinary, manifest, README, and sensitive files (including `include_hidden=True`).
- `content_bytes_read == 0` in the result; sensitive synthetic content never read or emitted.
- Static scan confirms no content-reading APIs in inspection/infrastructure code (the only `.read(` match is the Git adapter's method name, which runs subprocesses, not file reads).
- Manifest and language detection are name/extension-only.

## 6. Root containment and path handling

- Prefix-collision (`repo` vs `repo-escape`) handled correctly; nothing above the root emitted; no `..` in output.
- Missing path → `PATH_NOT_FOUND`; file path → `PATH_NOT_DIRECTORY`.
- Symlink/junction in the requested path rejected (`PATH_ESCAPE`); link-component detection mocked-tested cross-platform.
- NUL-bearing requested path rejected with a defined `InspectionError`.
- Working-directory independence confirmed (fixtures at explicit `--path`).

## 7. Symlink, junction, reparse, and special-entry validation

- `_classify_kind` independently verified for symlink, junction (mount-point tag), other reparse tag, and special entries.
- Links classified with `LINK_NOT_FOLLOWED` warning; never traversed; cycles impossible (non-following).
- `link_policy="error"` raises `LINK_NOT_FOLLOWED`; special entries skip-warn or fail under `error_policy="fail"`.
- Real-symlink/FIFO fixtures are platform-skipped on this Windows host (no symlink privilege, no FIFO); equivalent behavior is covered by mocked unit tests. Skips are explicitly recorded, not silently counted.

## 8. Resource budgets and partial results

- Entry, directory, depth, and total-bytes limits independently verified to produce explicit `LIMIT_*_EXCEEDED` partial results with exit 0.
- Warnings cap produces `LIMIT_WARNINGS_EXCEEDED`; manifest cap warns.
- Requests reject zero/negative/above-hard-max limits; hard maxima cannot be exceeded.
- Partial results preserve deterministic collected data; traversal stops promptly.

## 9. Ignore and nested-repository behavior

- `.git` always excluded (including with `include_ignored=True`).
- Nested repositories excluded (`nested_repository` exclusion).
- `node_modules` excluded by default and traversed under `include_ignored=True`.
- `.gitignore` content is not parsed (no content read).
- Boundary-aware matching (no substring errors).

## 10. Sensitive-name and disclosure validation

- `.env`, `id_rsa`, `secrets.json`, `server.key` redacted to `<sensitive-N>`; raw names absent from text and JSON.
- Synthetic contents never read or emitted; no ANSI; no absolute paths in JSON.
- One LOW gap: `creds.toml` (a credential-like name) is not matched by the sensitive policy and its filename appears (see §17). No content disclosure.

## 11. Git metadata boundary

- Commands recorded: only `symbolic-ref`, `rev-parse --short`, `status --porcelain` — all read-only, with `--git-dir`/`--work-tree` pinning, argument arrays, no shell, `GIT_TERMINAL_PROMPT=0`, timeout, bounded status.
- No fetch/pull/push/add/commit/remote/config mutation commands.
- Dirty/clean, branch, detached-HEAD, and failure paths independently verified via a recorded runner.
- Non-Git directories skip the adapter; `--no-git` skips it.

## 12. Phase 2 policy integration

- Independent ordering spy: `policy → inspector → git` for an allowed decision; `policy` only for a denied decision (no traversal, no Git subprocess).
- Uses `Capability.REPOSITORY_METADATA_READ` in `READ_ONLY`; no approval required; no Phase 2 contract change.

## 13. Serialization and determinism

- Schema version exactly `1`; JSON valid; no machine-specific fields; redacted entries present; empty/partial/git-present/git-absent representations correct.
- Two fresh-process executions over the same fixture produce byte-identical JSON.
- Text and JSON represent equivalent facts; deterministic ordering.

## 14. CLI and regression validation

- `agent-harness inspect` (text/JSON), `python -m agent_harness inspect`, `--path`, `--git/--no-git`, `--max-entries`, `--max-depth`, invalid options (exit 2), missing path (exit 2), partial (exit 0), internal failure (exit 10), stdout/stderr separation, no ANSI in JSON — all verified.
- Phase 1 CLI regression: help/version/health/config-check text+JSON and module execution pass; no Phase 3 command interferes.

## 15. Test-quality review

- Tests reproduce the key security properties independently (open-spy, ordering spy, classification matrix, budget matrix, redaction, determinism, subprocess recording).
- Platform skips are explicit and justified; equivalent mocked coverage exists for symlink/reparse/special branches.
- No material test-quality gap found. The single LOW finding (sensitive-name coverage) is not covered by a test.

## 16. Full validation results

| Check | Result | Gate |
|---|---|---|
| Python | 3.11.9 | 3.11+ PASS |
| Dependency integrity | clean | PASS |
| Phase 3 focused | 141 passed, 10 skipped | — |
| Full suite | 343 passed, 10 skipped | ALL |
| Failed / xfailed | 0 / 0 | 0 |
| Line coverage | 99% | ≥90% PASS |
| Branch coverage | ~97.7% (442/10 partial) | ≥85% PASS |
| Module coverage | errors/request/result 100%; git_metadata 100%; service 100%; inspector 98%; serialization 95% | — |
| Containment/non-following/policy/budget branches | 100% (mocked + platform-gated) | 100% or justified |
| Changed-lines coverage | 100% for new modules; ~98% inspector (defensive lines) | 100% practical |
| Content/secret/static scans | CLEAN | CLEAN |

All 10 skips are platform-justified (symlink creation ×8, FIFO, NUL filename on Windows) with mocked equivalents.

## 17. Findings

- FINDING-AH03-TST-01 — LOW — `creds.toml` is not matched by the sensitive-name policy. Evidence: independent probe placed `creds.toml` with synthetic content; its raw filename appears in output (redacted to nothing). Expected: credential-like names should be redacted per the design's sensitive-file category. Actual: `creds.toml` (and other `creds*`/`.credentials` variants) is not in `SENSITIVE_EXACT`/suffix rules; only the filename is disclosed (no content). Impact: minor disclosure of a credential-file's presence; no content leak. Remediation: broaden sensitive patterns (e.g., `creds*`, `.credentials`, `*.token`) with care to avoid over-redacting ordinary source names.
- FINDING-AH03-TST-02 — INFO — Real-symlink/FIFO/NUL fixtures are platform-skipped on this Windows host; equivalent behavior is covered by mocked unit tests. NO_ACTION_REQUIRED.
- FINDING-AH03-TST-03 — INFO — `C:\Users\agust` is itself a git repository; fixtures under the user profile resolve to the home repo unless the fixture has its own `.git` or the resolver is injected. The resolver's nearest-`.git` behavior is correct and the CLI/service handle it; tests use injected resolvers or self-contained `.git` fixtures. NO_ACTION_REQUIRED.

No BLOCKER, HIGH, or MEDIUM findings.

## 18. Warnings

- None beyond the LOW finding above.

## 19. Blockers

- None.

## 20. Repository state

- Branch: feature/ah-03-repository-inspection
- HEAD: 7a46b54...
- Feature commits: 0
- Staged files: none
- Only `src/agent_harness/cli.py` modified among tracked files; Phase 3 new files untracked
- Report change: `reports/AH-03-TST-01.md` created only
- Remote operations: none; GitHub operations: none

## 21. Commands executed

- Git/gh read-only checks; `git diff --check`
- `python --version`, `python -m pip check`
- `python -m pytest -p no:cacheprovider --cov=agent_harness --cov-branch` (temp coverage data)
- Independent probe script (46 checks): open-spy metadata-only, containment/path attacks, link classification, budgets, ignore/nested-repo, sensitive disclosure, git subprocess boundary, policy ordering, fresh-process determinism
- Phase 1 CLI regression and `inspect` operational smoke
- Static content-read/framework/mutating-git/secret scans
- No credentials, tokens, or raw sensitive filenames were output.

## 22. Recommended next action

PROCEED_TO_AH-03-SEC-01

The Phase 3 implementation independently passes all security-critical checks: no inspected content is read, containment and non-following behavior hold, mandatory budgets produce explicit partial results, sensitive data and machine-specific paths are protected (with one LOW credential-name gap), the policy gate provably runs before traversal, Git metadata is local and read-only, and schema/CLI contracts hold. All 343 tests and coverage gates pass. The single LOW finding does not prevent proceeding to the independent security review.

## 23. Non-modification attestation

- Only `reports/AH-03-TST-01.md` was created or updated persistently.
- No production or test file was modified.
- No prior evidence report was modified.
- No Phase 1 or Phase 2 file was modified.
- No dependency was added, removed, installed, or updated.
- No file was staged.
- No commit was created or amended.
- No branch was created, switched, pushed, or deleted.
- No Pull Request or GitHub resource was modified.
- No container or service was started.
- No inspected-file content was read or exposed.
- No credential, secret, or raw sensitive filename was exposed.
- All temporary validation artifacts were removed.
