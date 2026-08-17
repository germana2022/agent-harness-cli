# AH-03-IMP-FIX-01 — Repository Inspection Security Fix Report

## 1. Result

- Status: COMPLETED
- Timestamp: 2026-08-17
- Repository: `germana2022/agent-harness-cli`
- Git root: `D:/agente-harness`
- Branch: `feature/ah-03-repository-inspection`
- Base commit: `7a46b54f47f542d1c6d37f8e38343958c917eb83`
- Execution mode: WRITE_CONTROLLED_LOCAL

## 2. Preconditions

Verified against the authorized expected state:

| Check | Result |
|---|---|
| Git root | `D:/agente-harness` |
| Branch | `feature/ah-03-repository-inspection` |
| HEAD | `7a46b54f47f542d1c6d37f8e38343958c917eb83` |
| Commits ahead of `main` | 0 |
| Staged changes | none |
| Remote Phase 3 branch | absent |
| Phase 3 PR | none |
| `python --version` | 3.11.9 (project venv; Phase 1 bare interpreter is 3.8) |
| `python -m pip check` | clean |
| Dependency changes | none (no `pyproject.toml` diff) |
| Existing reports | AH-03-ARC-01 / IMP-01 / TST-01 / SEC-01 present |

Authoritative inputs read before changes: `docs/PHASE_03_SAFE_REPOSITORY_INSPECTION_DESIGN.md`, `docs/SECURITY_MODEL.md`, and the four `AH-03-*` reports. The design and security model were honored; no design conflict was encountered.

## 3. Findings reproduced

Failing-before evidence (baseline, prior to edits):

- **F1 (`AH03-TST-01` / Security F1):** `Inspector._is_sensitive_name` returned `False` for `creds`, `creds.toml`, `cred`, `service-creds.json`, `database_creds.yaml`, `CREDENTIALS` case variants. `creds.toml` was emitted literally in CLI/JSON output.
- **F2 (Security F2):** `Inspector._is_sensitive_name(".env.example")` returned `True` (redacted), contradicting `docs/SECURITY_MODEL.md` "`.env.example` is the only environment-template exception allowed."
- **F5 (Security F5):** `GitMetadataReader._run` used `subprocess.run(capture_output=True, text=True)` — all stdout was buffered in memory before the `splitlines()[:max_status_lines]` cap; no byte bound during collection.

All three reproduced from base state before any source edit.

## 4. Root-cause analysis

- **F1:** The sensitive classifier used exact-name and extension-suffix membership plus a broad `.env.` prefix, but had no bounded-token matching, so credential abbreviations (`cred`, `creds`) short of the full `credentials` stem were visible.
- **F2:** The `.env.` prefix rule (`startswith(".env.")`) matched `.env.example` with no exception step, so the documented safe template was suppressed.
- **F5:** Capture was delegated to `subprocess.run`, which collects stdout/stderr to EOF before returning; the logical line cap applied only after an unbounded in-memory copy.

## 5. Files changed

Authorized Phase 3 files only; no Phase 1/2 production/test files, no `cli.py`, no design/earlier-report files touched.

| File | Change |
|---|---|
| `src/agent_harness/infrastructure/inspector.py` | Precedence-based sensitive classifier, `.env.example` exception, bounded-token helper; removed unreachable duplicate block in `_contains_link_component` |
| `src/agent_harness/infrastructure/git_metadata.py` | Bounded stdout/stderr capture (explicit byte caps, concurrent draining, deterministic termination/cleanup, truncation sentinel) |
| `tests/unit/inspection/test_git_metadata.py` | Rewritten for fake-`popen` injection; expanded 10 → 24 tests incl. output bounds, timeout termination, concurrent streams, thread-leak, truncation determinism, drain/cleanup error tolerance, `_BoundedBuffer` units |
| `tests/unit/inspection/test_sensitive_policy.py` | New: 11 test functions (18 pytest items) for sensitive positives/negatives, `.env.example` exception + variants, cross-output redaction, deterministic ordering, zero-content-read |
| `tests/integration/test_cli_inspect.py` | +2 CLI regression tests: `cred`-name redaction and near-match visibility through the CLI |
| `reports/AH-03-IMP-FIX-01.md` | This report |

## 6. Sensitive-name policy correction

`Inspector._is_sensitive_name` (inspector.py) now implements documented precedence:

1. Exact approved exception — `.env.example` (case-insensitive) → visible.
2. Exact protected names — existing `SENSITIVE_EXACT` → sensitive.
3. Protected bounded tokens/extensions — `.env.` prefix, `SENSITIVE_SUFFIXES`, and `cred`/`creds` tokens matched only on approved boundaries (`.`, `_`, `-`, whitespace, basename edges) → sensitive.
4. Non-sensitive default → visible.

Token matching uses `_has_sensitive_bounded_token`, which normalizes the lowered basename onto boundaries and compares whole tokens — no substring matching. Verified:

- New positives: `cred`, `creds`, `creds.toml`, `service-creds.json`, `database_creds.yaml`, `CREDENTIALS`, `Creds`, `Cred.toml`, `DB-CREDS.yml`, `prod_creds.ini`.
- Near matches stay visible: `accredited.py`, `accreditation.txt`, `credit.py`, `credito.yaml`, `credentialing.py`, `discredited.log`, `mycreds`, `credsfile`, `token.py`, `password_manager.py`, `id_rsa.pub`.
- Existing protected names unchanged: `.env`, `.env.local`, `id_rsa`, `*.key`, `*.pem`, `*.p12`, `*.pfx`, `*.jks`, `*.keystore`, `credentials`, `credentials.json`, `credentials.toml`, `client_secret.json`, `service_account.json`, `secrets.json`, `.npmrc`, `.pypirc`, `.netrc`.
- Redaction representation unchanged (`<sensitive-N>`), stored via the existing `_visit_file` sensitive branch; `sensitive_entries` count and deterministic ordering preserved.

No file content is ever read (verified below).

## 7. `.env.example` exception correction

The exception is exact and narrow:

- Visible: `.env.example` and case variants (`.ENV.EXAMPLE`, `Env.Example`, `.env.exaMple`).
- Still protected (real environment variants): `.env`, `.env.local`, `.env.production`, `.env.development`, `.env.test`, `.env.example.local`, `.env.example.bak`, `.env.example.copy`, `.env.example.2024`.
- Not generalized: `example.env`, `examples.md`, `example.py`, `env.example.md` remain governed by the normal rules and are visible (they were never matched by `.env.` anyway) — the exception is not extended to arbitrary names containing `example`.

## 8. Bounded Git-output correction

`GitMetadataReader` (git_metadata.py) now enforces bounds during collection:

- `max_stdout_bytes` (default 1 MiB) and `max_stderr_bytes` (default 64 KiB) explicit caps.
- `_capture` uses `subprocess.Popen` with concurrent daemon-thread draining of `stdout` and `stderr` (`_drain_until_eof` + `_BoundedBuffer`). Both pipes are drained simultaneously, so the child can never block on a full pipe (no deadlock); bytes beyond the caps are read and discarded, so memory stays bounded while the writer is drained.
- Timeout retained (`timeout=5.0`); on `TimeoutExpired` the child is `kill()`ed and `wait()`ed (deterministic reap), then threads are joined; a last-resort cleanup closes the pipes and reunites any still-alive drain threads. Verified no leaked `ah-git-*` threads after real and faked runs.
- Output at/above the byte cap is treated as truncated via an explicit `_TRUNCATED` sentinel; `read()` returns `None` for a truncated command, and the service surfaces the stable, sanitized `GIT_METADATA_UNAVAILABLE` warning (no raw filenames, control characters, absolute paths, or raw Git diagnostics are emitted; serialized result size stays bounded).
- Preserved: fixed read-only verbs (`symbolic-ref`, `rev-parse`, `status --porcelain`), `--git-dir`/`--work-tree` pinning, argument-array execution (`shell=False`), `GIT_TERMINAL_PROMPT=0`/`GIT_OPTIONAL_LOCKS=0`, no hooks/aliases, no network or mutation, no new executable, no new dependency (standard library `threading`, `subprocess` only).
- Normal behavior unchanged: `test_oversized_status_line_cap` (500-line status, byte-capped by line cap only), clean repos, detached head, and ordinary failures behave exactly as before.

## 9. Regression tests added

- `tests/unit/inspection/test_sensitive_policy.py` — sensitive positives, near-match negatives, `.env.example` exception + protected variants, bounded-token unit checks, entry-level redaction/visibility, cross-output text/JSON consistency, deterministic ordering, and a `builtins.open` spy asserting zero content reads across the sensitive path.
- `tests/unit/inspection/test_git_metadata.py` — read success, argument arrays/no-shell, prompt disabled, detached head, missing git, nonzero exit, line cap, clean repo, status-failure partial, stdout at/exceeding the byte cap, stderr exceeding the cap, concurrent stdout+stderr (no deadlock), timeout kill+reap, no leaked threads, truncation determinism, large-but-below-bound, `_BoundedBuffer` units, drain read/close error tolerance, forced pipe-close cleanup and join.
- `tests/integration/test_cli_inspect.py` — CLI JSON redaction of `creds.toml`/`service-creds.json`, and CLI visibility of `accredited.py`/`credit.py` (pipeline-level cross-output).

## 10. Security and operational probes

Standalone probe (outside the repo) — **15/15 passed**:

1. Zero `open()` calls across the sensitive service path (spy).
2. No canary content leaked; `content_bytes_read == 0`.
3. Sensitive positives all redacted; near-match negatives visible; real `.env` variants protected; `.env.example` exception exact and case-insensitive.
4. Truncation → `read()` returns `None`; through `InspectionService` → stable `GIT_METADATA_UNAVAILABLE` warning.
5. Real Git repository (`git init`+commit) → bounded metadata obtained through the new capture; no leaked `ah-git-*` threads.
6. Fresh-process CLI determinism (byte-identical JSON) and `creds.toml`/canary absence from CLI output.

Static scans (Python-regex over `src/agent_harness`): no inspected-file content reads, no `eval`/`exec`/`pickle`, no `shell=True`/`os.system`/`os.popen`, no network clients, no model/LLM calls, no secrets in code, no `runner=` leftovers, no native/ctypes imports, changed-file imports are stdlib/self only. The only `.read()` hits are the Git pipe drain and a method-name false positive — both benign.

## 11. Validation results

| Gate | Result |
|---|---|
| Focused fix tests | all pass |
| Complete Phase 3 tests | 172 passed, 10 skipped |
| Full test suite | **377 passed, 10 skipped** (baseline 343 → +34) |
| Line coverage | **99%** (1,585 stmts, 9 miss) — gate ≥90% ✓ |
| Branch coverage | **~97.9%** (470 branches, 10 partial) — gate ≥85% ✓ |
| Fix changed-lines coverage | `git_metadata.py` **100%** line + branch; sensitive-policy classifier **100%** (no misses in any changed/new line) |
| Sensitive-policy correction branches | 100% |
| Git output-bound and cleanup branches | 100% (incl. `_BoundedBuffer`, drain error tolerance, timeout kill/reap, forced cleanup) |
| Uncovered remainders | pre-existing unrelated paths only (inspector resolve briefs/bare-repo detection, serialization optional-field branches, `cli.py:222`, `__main__.py`) — no security-critical branch |
| `git diff --check` | clean (exit 0) |
| `py_compile` of changed files | clean |
| CLI regression | `version`, `health`, `config-check` exit 0; `inspect --path <repo> --git` exit 0 with branch/commit/counts; `inspect --output json --git` populated git field |
| Phase 1/2 suites | unchanged and passing within the full suite |
| No content read | confirmed (spy probe + static scan) |
| No repo/Git/network/model/shell side effect | confirmed (static scan + read-only probe) |
| No new dependency | confirmed (`pip check` clean; no `pyproject.toml` diff) |

## 12. Findings closure

| Finding | Status | Evidence |
|---|---|---|
| `AH03-TST-01` / Security F1 — `creds`/`cred` not redacted | **FIXED** | Failing-before: `_is_sensitive_name("creds.toml") is False`. Passing-after: all `cred`/`creds` bounded-token positives redacted (unit + CLI tests; probe items 3). |
| Security F2 — `.env.example` over-redaction | **FIXED** | Failing-before: `_is_sensitive_name(".env.example") is True`. Passing-after: `.env.example` and case variants visible; `.env.example.local/.bak/.copy` still protected (unit + probe item 3). |
| Security F5 — unbounded Git stdout capture | **FIXED** | Failing-before: `subprocess.run(capture_output=True)` buffered to EOF. Passing-after: byte caps enforced during collection; over-cap → `None` → `GIT_METADATA_UNAVAILABLE` (unit + probe item 4). |
| Security F4/dead-code observation — duplicate block in `_contains_link_component` | **FIXED** | The duplicate was provably unreachable (it followed an unconditional `return False`). Removal retained the active implementation; all `test_contains_link_component_*` tests still pass; link-component validation unchanged. |

## 13. Warnings

- The `test_cleanup_forces_pipe_close_and_joins` regression test exercises the last-resort cleanup path and adds ~5s to the suite (acceptable).
- 10 pre-existing platform skips (symlink/junction/FIFO on Windows) remain, all with equivalent mocked coverage.
- The accepted worktree `.git`-file gitdir indirection and the 5s timeout behavior are unchanged (documented as `ACCEPTED_INFO`; not re-litigated in this fix).

## 14. Blockers

None.

## 15. Repository state

- HEAD `7a46b54`, branch `feature/ah-03-repository-inspection`, 0 commits ahead of `main`.
- Modified (tracked): `src/agent_harness/cli.py` (pre-existing Phase 3 baseline change — not modified by this fix).
- Untracked Phase 3 dirs/files, including the two modified infrastructure modules, updated/new tests, and this report.
- No files staged, committed, pushed, or published; no remote branch or PR created.

## 16. Commands executed

- Precondition/scope: `git rev-parse --show-toplevel/--abbrev-ref HEAD`, `git rev-list --count main..HEAD`, `git status --short`, `git diff --cached --name-only`, `git ls-remote --heads origin …`, `gh pr list …`, `python --version`, `python -m pip check`.
- Failing-before reproduction: direct `_is_sensitive_name` matrix over the finding names.
- Fix tests: `pytest tests/unit/inspection/test_sensitive_policy.py tests/unit/inspection/test_git_metadata.py tests/integration/test_cli_inspect.py`.
- Full suite: `python -m pytest -p no:cacheprovider --cov=agent_harness --cov-branch --cov-report=term-missing`.
- Module coverage: `pytest tests/unit/inspection/test_git_metadata.py --cov=agent_harness.infrastructure.git_metadata --cov-branch --cov-report=term-missing`.
- Validation probe: `python fix_probe.py` (temp dir outside the repo) — 15/15.
- Static scans: regex-based scan over `src/agent_harness` (temp script).
- `python -m py_compile <changed files>`; `git diff --check`.
- CLI smoke: `version`, `health`, `config-check`, `inspect --path … --git`, `--output json inspect … --git`.

## 17. Recommended next action

`PROCEED_TO_AH-03-TST-FIX-01`

## 18. Non-modification attestation

No Phase 1/2 production or test file, no `src/agent_harness/cli.py`, no Phase 3 design document, no earlier architecture/implementation/QA/security report, and no dependency file was created or modified by this fix. Only the authorized Phase 3 implementation modules, the relevant existing/new Phase 3 test modules, and `reports/AH-03-IMP-FIX-01.md` were created or changed. No repository, Git, network, GitHub, model, or shell side effect occurred, and no content file was read. Nothing was staged, committed, pushed, or published.