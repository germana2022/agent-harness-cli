# AH-03-TST-FIX-01 — Independent Repository Inspection Fix Validation

## 1. Decision

- Decision: PASS_WITH_WARNINGS
- Timestamp: 2026-08-17
- Repository: `germana2022/agent-harness-cli`
- Git root: `D:/agente-harness`
- Branch: `feature/ah-03-repository-inspection`
- Base commit: `7a46b54f47f542d1c6d37f8e38343958c917eb83`
- Execution mode: WRITE_CONTROLLED_REPORT_ONLY

No `BLOCKER`, `HIGH`, or `MEDIUM` finding. The corrections are independently validated as fixed. One `LOW` robustness finding (`proc.kill()` not guarded on the timeout path) and several `INFO` observations are recorded; none void the decision.

## 2. Preconditions

| Check | Result |
|---|---|
| Git root / branch / HEAD | `D:/agente-harness`, `feature/ah-03-repository-inspection`, `7a46b54…` |
| Commits ahead of `main` | 0 |
| Staged changes | none |
| Modified (tracked) | only `src/agent_harness/cli.py` (89-insertion pre-existing Phase 3 `inspect` command change; fix mtime-independent — verified mtime 8/16 baseline) |
| Untracked | Phase 3 docs/reports/source/tests only |
| Remote Phase 3 branch / PR | absent / none |
| Dependency integrity | `python -m pip check` clean; no `pyproject.toml` diff |
| `git diff --check` | clean (exit 0) |
| Generated artifacts | none introduced by the fix; `build/` and `*.egg-info/` are pre-existing gitignored artifacts from earlier phase packaging (`.gitignore:28,30`) |
| Fix file-set (mtimes) | only `inspector.py`, `git_metadata.py`, `test_sensitive_policy.py`, `test_git_metadata.py`, `test_cli_inspect.py`, `reports/AH-03-IMP-FIX-01.md` modified at fix time; everything else at day-old baseline |

No unauthorized Phase 1 or Phase 2 change; no unexpected CLI change beyond the pre-existing Phase 3 `inspect` command; no generated artifact added by the fix.

## 3. Fix diff review

The fix is confined to the authorized Phase 3 modules and tests:

- `src/agent_harness/infrastructure/inspector.py` — added `SENSITIVE_ENV_EXAMPLE_EXCEPTION`, `SENSITIVE_TOKENS`, `_SENSITIVE_TOKEN_SEPARATORS`, `_has_sensitive_bounded_token`, and a precedence-based `_is_sensitive_name`; removed the unreachable duplicated block in `_contains_link_component`.
- `src/agent_harness/infrastructure/git_metadata.py` — replaced `subprocess.run(capture_output=True, text=True)` with `Popen` + concurrent bounded drains (`_BoundedBuffer`, `_drain_until_eof`, `_capture`), a `_TRUNCATED` sentinel, and per-command truncation propagation into `read()`.
- Tests: `test_git_metadata.py` (rewritten with fake `popen` injection, 10→24), `test_sensitive_policy.py` (new), `test_cli_inspect.py` (+2).
- Public contract: `GitMetadataReader.read()` signature and return type unchanged (`GitInfo | None`); the test-injection seam was renamed `runner=` → `popen=`. No product consumer change required (`cli.py`/service use default construction).

## 4. Root-cause correction

| Finding | Original failing behavior | Root cause | Correction | Residual |
|---|---|---|---|---|
| AH03-TST-01 / SEC F1 | `creds.toml`, `cred`, `creds`, `service-creds.json`, `database_creds.yaml` emitted unredacted | classifier used exact-name/suffix sets with no bounded-token matching for the `cred`/`creds` abbreviation | `SENSITIVE_TOKENS` on approved boundaries (`.` `_` `-` space, basename edges), case-insensitive, whole-token only | none reachable; token split is closed and substring-free |
| SEC F2 | `.env.example` redacted by the broad `.env.` prefix rule | no exception step before the broad rule | exact, case-insensitive `SENSITIVE_ENV_EXAMPLE_EXCEPTION` evaluated first | none; exception is exact and narrow |
| SEC F5 | `subprocess.run(capture_output=True)` buffered all stdout to EOF before the logical line cap | capture delegated to a fully-buffering runner | in-drain byte caps (`max_stdout_bytes`/`max_stderr_bytes`), concurrent draining, termination/reap, `_TRUNCATED` sentinel | see Findings F-TST-1 (LOW kill guard) and INFO notes |
| SEC dead-code | duplicate unreachable block behind an unconditional `return False` in `_contains_link_component` | copy/paste duplication | duplicate removed; active implementation retained unchanged | none — single active implementation remains; link tests pass |

No insecure compatibility path remains: the only capture path is the bounded one; `subprocess.run`/`capture_output`/`communicate()` are absent from `src/agent_harness` (verified by grep).

## 5. Sensitive-name regression

Independent tester-authored matrix (39/39 probe pass; distinct names, not copied from implementation tests):

- Redacted (verified): `cred, creds, cred.json, creds.toml, service-cred.yaml, service-creds.json, database_cred.ini, database_creds.yaml, cred backup.toml, cred (leading/trailing space), CRED/CREDS/CredS.toml, CREDENTIALS, credentials, credentials.json, id_rsa, server.key, app.pem, client.pfx, keystore.jks, secrets.json, .npmrc, .pypirc, .netrc, client_secret.json, service_account.json, .env, .env.local/production/development/test, .env.example.local/.bak/.copy/~`.
- Visible (verified): `accredited.py, accreditation.txt, discredited.log, credit.py, credito.yaml, credentialing.py, credible.md, credo.toml, cremate.log, credals.yaml, credential_is_checked.py, README.md, config.yaml, settings.ini, app.json, example.py, examples.md, env.example.md, example.env, keymap.py, tokenizer.py, .env.example (+ case variants)`.
- Boundary matrix (`creds`@edges, `a_creds`, `a-creds`, `a creds`, `creds_file`, `x.creds`, `creds.backup`, `a.b.c-creds.d.e`, `creds_file_bak.txt` = redacted; `mycreds`, `credsfile` = visible): all correct.
- Separator/extension/unicode matrix (`.env..local`, `.env.-.prod`, `creds..toml`, `creds.tar.gz`, `creds.example`, `café-creds.toml`, `creds-é`, `cred..`, `..creds..`, `creds\t.toml`): all correct.
- No uncontrolled substring rule exists — only whole-token equality against `{cred, creds}` after boundary normalization.

## 6. `.env.example` exception regression

- Visible: `.env.example` and case variants (`.ENV.EXAMPLE`, `Env.Example`).
- Protected (all redacted): `.env`, `.env.local`, `.env.production`, `.env.development`, `.env.test`, `.env.example.local`, `.env.example.bak`, `.env.example.copy`, `.env.example~` (verified in §5 matrices + `2d`).
- The exception is evaluated before the broad `.env.*` rule (code order at `inspector.py:560` → `564`), is exact, and is case-folded. The file is never opened (zero `open()` calls), no example-file content is emitted, and the exception behaves identically in text and JSON outputs.
- No raw sensitive sibling name appears in warnings or errors: the only warnings emitted on these paths are absence of Git metadata with sanitized text.

## 7. Cross-output disclosure regression

Verified consistently across entry lists, text, JSON, warnings, summaries, counts, deterministic ordering, and partial results:

- `creds.toml`, `x_creds.yaml`, `.env` are absent from entry paths, text, and JSON; redacted entries carry stable `<sensitive-N>` tokens; `sensitive_entries` count equals the number of redacted entries.
- `.env.example` remains visible in entries/text/JSON without exposing content.
- No absolute path, ANSI, or control character introduced; JSON is `sort_keys=True`, `ensure_ascii=True`.
- Randomized canary contents never appear; `content_bytes_read == 0`.

## 8. Bounded Git-output validation

Independent proof using real helper subprocesses driven through the real `_capture` path (not fakes):

- The fully-buffering path is unreachable: no `subprocess.run`, `capture_output`, or `communicate()` in `src/agent_harness`.
- A real child writing 256 KiB stdout + 32 KiB stderr with caps 4096/256 → `_TRUNCATED`; instrumented `_BoundedBuffer` retained exactly the cap (4096 bytes), never more; truncated flag set.
- Exactly-at-limit (1000/1000 bytes) → success with intact bytes; one-byte-over → `_TRUNCATED`.
- Multibyte UTF-8 split at the byte boundary (1200 B `€` stream at 1000 cap) → `_TRUNCATED`, no crash; invalid byte sequences (`\xff\xfe\x00\x81…`) decode safely with `errors="replace"`.
- No-newline large single line → captured correctly; nonzero-exit child → `None`; all bounded and deterministic across 5 repeated invocations.
- Serialized result size bounded: only counts + short branch/commit strings reach the result; no raw oversized output, hostile filenames, or control sequences in result, exception, stdout, or stderr.

## 9. Subprocess concurrency and lifecycle

- Concurrent stdout+stderr flood that never exits → timeout path exercised with real pipes: killed, reaped, bounded to 0.6 s of a 0.6 s timeout, `None` returned; no drain thread left (`ah-git-*` set empty before and after).
- Exactly-at / one-above / stderr-at-cap behaviors confirmed; truncation before process exit handled by drain-to-EOF (writer never blocks on a full pipe → no deadlock).
- Timeout and truncation are distinguishable internally (`None` vs `_TRUNCATED`) and both collapse deterministically to `read() → None` → sanitized `GIT_METADATA_UNAVAILABLE` warning (verified once for timeout and once for truncation).
- Normal Git metadata below the cap is unchanged: real `git init`+commit repos (including a directory with spaces and a directory with a leading hyphen) return branch/commit/dirty/counts; clean and detached-head behavior match pre-fix tests.
- See Findings `F-TST-1` (unguarded `kill()` on timeout) and `INFO-2` (bounded final join).

## 10. Git boundary regression

Recorder-injected command-vector audit:

- Exact vector tails are the three fixed read-only verbs: `symbolic-ref --quiet --short HEAD`, `rev-parse --short HEAD`, `status --porcelain --untracked-files=all`, always `["git", "--no-optional-locks", "--git-dir=<root>/.git", "--work-tree=<root>", ...]`.
- Argument-array (no shell), `GIT_TERMINAL_PROMPT=0`, `GIT_OPTIONAL_LOCKS=0`, timeout-bounded, output-bounded; no fetch/pull/push/add/commit/checkout/reset/clean/update-index/hooks/aliases/network behavior reachable.
- Paths with spaces and leading-hyphen components are safely embedded in `--git-dir=`/`--work-tree=` single tokens (real-git verified); no option injection.
- Raw Git diagnostics are never surfaced (nonzero exit/timeout/truncation → `None`/warning); hostile porcelain filenames are never emitted (status is reduced to counts).

## 11. Containment, metadata-only, and policy regression

- Dead-code removal: `_contains_link_component` (inspector.py:284-296) retains the single active implementation; all four link-component tests pass; root-link rejection reproduced (`PathEscapeError`); the walker still uses `follow_symlinks=False` in 6 places (dir/file/stat classification), so internal/external links and junctions/reparse points are never followed (mocked on Windows).
- Prefix-collision containment intact (`a.py` vs `ab.py` distinct; `accredited.py` visible; `creds.toml` redacted).
- Metadata-only: zero `open()` calls across the service path; `content_bytes_read == 0`; no manifest/`.gitignore`/sensitive-file content parsing (name-based only).
- Policy-before-traversal: a denying engine produced an empty order (no `inspector`, no `git`) — gate precedes traversal and Git.
- Capability/mode unchanged (`REPOSITORY_METADATA_READ`, `READ_ONLY`); missing/malformed policy dependency fails closed (pre-existing service tests).

## 12. CLI, serialization, and determinism

- `agent-harness` and `python -m agent_harness inspect` both exit 0 on valid trees; text and JSON modes work; `--git`/`--no-git` behave; budget (`--max-entries 2`) yields exit 0 with `status=partial`; missing path and file path yield exit 2 with no traceback; stdout/stderr separated.
- `schema_version=1`; no ANSI; no absolute paths; `content_bytes_read=0`; git section populated.
- Fresh-process byte-identical output (SHA-256 match across two invocations); deterministic after redaction-policy change; `creds.toml` absent from the self-repo JSON.
- Git-truncation warning is deterministic and sanitized (service + adapter verified).
- Phase 1 CLI (`version`, `health`, `config-check`) and Phase 2 domain/security suites pass inside the full run.

## 13. Test-quality assessment

- New/expanded tests are behavior-focused: independent fake-`popen` double with controlled streams, wait/kill timing, and blocking-stream scenarios; `_BoundedBuffer` unit tests; security-policy matrix tests; CLI cross-output tests. They are not tautologies and exercise the real `_capture` path where it matters.
- The suite contains no xfail/xpass; all 10 skips are platform-justified (7× symlink privilege/NUL-char/FIFO on Windows, 2× unit symlink, 1× NUL byte) with mocked equivalents.
- The independent tester's own 39-probe harness (real helper subprocesses + injected doubles) reproduced the claimed behavior without consulting the implementation tests.

## 14. Full validation results

| Metric | Result |
|---|---|
| Collected / passed / failed / skipped / xfailed / xpassed | 387 / 377 / 0 / 10 / 0 / 0 |
| Full line coverage | 99% (1,585 stmts, 9 miss) — gate ≥90% ✓ |
| Full branch coverage | ~97.9% (470 branches, 10 partial) — gate ≥85% ✓ |
| `inspector.py` | 99% (346/5 miss, 1 brpart) |
| `git_metadata.py` | 100% (133/0; 30/0 branches) |
| Sensitive-classifier decision branches | 100% (no miss in any changed/new line in scoped run) |
| Fix changed-lines coverage | effectively 100% — no uncovered line in fix-touched regions |
| `pip check` / `git diff --check` / `py_compile` | clean / clean / clean |
| Security-critical uncovered branch | none (residual misses are pre-existing unrelated paths: inspector resolve-error/bare-repo lines 234-235, 244, 280-281, 649→651; serialization optional-field branches; `cli.py:222`; `__main__.py`) |
| Independent probe harness | 39/39 passed |

## 15. Findings

### F-TST-1 (LOW) — `proc.kill()` unguarded on the timeout path
- **Location:** `git_metadata.py:192-195`.
- **Detail:** if `subprocess.TimeoutExpired` fires and the subsequent `proc.kill()` raises `OSError` (narrow race on Windows where the child exits between the timeout detection and the `TerminateProcess` call — `Popen.kill()` is not wrapped), the exception propagates uncaught out of `_capture` → `_run` → `read()` → service, surfacing as a CLI internal error (exit 10) instead of degrading to the sanitized `GIT_METADATA_UNAVAILABLE` result. Reproduced with a mocked popen whose `kill()` raises: `OSError: kill failed` propagated and `read()` did not return `None`.
- **Impact:** robustness only; no content disclosure, no mutation, no orphan (threads still joined). Likelihood is low (child must exit in the exact window) and Windows-specific.
- **Recommendation (for the SEC-FIX gate or a follow-up IMP):** wrap `proc.kill()` (and reaping) in `try/except OSError` so the timeout path always returns `None`.

### F-TST-2 (INFO) — last-resort join has no explicit timeout
- **Location:** `git_metadata.py:207-208`.
- **Detail:** if a drain thread remained blocked on a pipe still held open after the forced close (only conceivable for a persistent grandchild process, which the fixed read-only verbs do not spawn), the final `join()` could block indefinitely. Not observed in any real- or fake-backed probe.
- **Recommendation:** bound the final join or document the accepted assumption that the read-only Git verbs spawn no persistent children.

### F-TST-3 (INFO) — all-or-nothing truncation
A single command at/over its byte cap causes `read()` to return `None`, discarding otherwise-valid branch/commit. Deliberate and deterministic (stable `GIT_METADATA_UNAVAILABLE` code) and compliant with the contract, but for genuinely huge repos a large `status` output drops all metadata. Per-command partial metadata with a distinct reason code would be a future enhancement.

### F-TST-4 (INFO) — token-boundary asymmetry for `credential(s)` compounds
`my-creds.json`/`service-creds.json` are redacted (token `creds`), while `my-credentials.json`/`credentials.txt` remain visible (token `credentials` is not in `SENSITIVE_TOKENS`). This is consistent with the previously accepted visibility of `credentials.txt`; the abbreviation is protected more aggressively than the full word in compounds. No fix gap; monitor during SEC-FIX.

### F-TST-5 (INFO) — `_`-joined source names now redacted
Names such as `cred_parser.py`/`cred_registry.py` (whole token `cred`) are redacted name-only. Conservative and consistent with the approved-boundary rule; no content is read. Documented so it is not mistaken for a leak.

## 16. Findings closure

| Finding | Status | Independent evidence |
|---|---|---|
| `AH03-TST-01` / SEC F1 (`cred`/`creds` redaction) | **FIXED** | Failing-before: `_is_sensitive_name("creds.toml") is False` (SEC-01 matrix). Passing-after: full §5 matrix, entry/text/JSON output, CLI — all redacted. |
| SEC F2 (`.env.example` exception) | **FIXED** | Failing-before: `_is_sensitive_name(".env.example") is True`. Passing-after: exception + case variants visible; `.env.*` and `.env.example.*` variants still redacted; exactness verified. |
| SEC F5 (bounded Git output) | **FIXED** | Failing-before: `subprocess.run(capture_output=True)` buffered to EOF. Passing-after: real-subprocess proof of in-drain caps, `_TRUNCATED` at/over cap, bounded memory, deterministic timeout kill/reap, no thread/process leaks, stable `GIT_METADATA_UNAVAILABLE`. |
| SEC dead-code observation | **FIXED** | Duplicate unreachable block removed; single active `_contains_link_component` retained; link tests + root-link rejection pass; containment unaffected. |

## 17. Warnings

- The suite contains one ~5 s regression test (`test_cleanup_forces_pipe_close_and_joins`) exercising the last-resort cleanup; acceptable.
- 10 platform skips remain justified (Windows cannot create symlinks/FIFOs without privileges; NUL bytes invalid in filenames) with mocked equivalents.
- Pre-existing gitignored `build/` and `*.egg-info/` directories exist from earlier-phase packaging (not fix-generated).

## 18. Blockers

None.

## 19. Repository state

- HEAD `7a46b54`, branch `feature/ah-03-repository-inspection`, 0 commits ahead of `main`.
- Modified (tracked): `src/agent_harness/cli.py` only (pre-existing Phase 3 change; untouched by this task).
- Untracked: Phase 3 docs/reports/source/tests plus `reports/AH-03-IMP-FIX-01.md` and this report.
- Nothing staged, committed, pushed, or published; no remote branch or PR.

## 20. Commands executed

- Scope: `git rev-parse --show-toplevel/--abbrev-ref HEAD`, `git rev-list --count main..HEAD`, `git status --short`, `git diff --cached`, `git diff --check`, `git ls-remote --heads origin …`, `gh pr list …`, `git check-ignore -v build src/agent_harness_cli.egg-info`, mtime audit.
- Dependency: `python -m pip check`.
- Validation: independent probe harness (39 checks) with real helper subprocesses; `pytest -p no:cacheprovider --cov=agent_harness --cov-branch --cov-report=term-missing`; `-ra` summary for skips/xfail; scoped inspector coverage; CLI smoke + fresh-process determinism; static regex scans; `py_compile`.
- All probes/artifacts were created under `C:\Users\agust\AppData\Local\Temp\opencode\` and removed before finishing.

## 21. Recommended next action

`PROCEED_TO_AH-03-SEC-FIX-01`

## 22. Non-modification attestation

No production code, test, design document, or earlier report was modified or created during this validation. Only `reports/AH-03-TST-FIX-01.md` was written. No repository, Git, network, GitHub, model, or shell side effect occurred; no credential or unrelated repository was accessed; all temporary artifacts were removed.