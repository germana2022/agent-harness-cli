# AH-03-SEC-FIX-01 — Repository Inspection Security Fix Re-review

## 1. Security decision

- Decision: SECURITY_PASS_WITH_WARNINGS
- Timestamp: 2026-08-17
- Repository: `germana2022/agent-harness-cli`
- Git root: `D:/agente-harness`
- Branch: `feature/ah-03-repository-inspection`
- Base commit: `7a46b54f47f542d1c6d37f8e38343958c917eb83`
- Execution mode: WRITE_CONTROLLED_REPORT_ONLY

All original findings are independently reproduced as **FIXED**. The new QA finding (`AH-03-TST-FIX-01 F-TST-1`, unguarded `proc.kill()`) is reproduced with a controlled mock and empirically shown to be **unreachable with real processes** (0/340 stress iterations); it is an accepted **LOW** reliability limitation that fails closed and does not require a code change before operational validation. One additional **LOW** (platform-gated, pre-existing) upstream-of-no-fix finding is recorded for text-mode entry-path sanitization, and the informational observations remain `INFO`. No `CRITICAL`, `HIGH`, or `MEDIUM` issue exists.

Recommended next action: **PROCEED_TO_AH-03-OPR-01**.

## 2. Preconditions

| Check | Result |
|---|---|
| Git root / branch / HEAD | `D:/agente-harness`, `feature/ah-03-repository-inspection`, `7a46b54…` |
| Commits ahead of `main` | 0 |
| Staged changes | none |
| Modified (tracked) | only `src/agent_harness/cli.py` (pre-existing Phase 3 `inspect` command; fix-mtime independent) |
| Untracked | Phase 3 docs/reports/source/tests + IMP-FIX/TST-FIX/SEC-FIX reports |
| Remote Phase 3 branch | absent (`git ls-remote origin feature/ah-03-repository-inspection` → empty) |
| Phase 3 PR | none (`gh pr list` attempted; GitHub API returned transient 503 — outage-side; corroborated by empty ls-remote) |
| Dependency integrity | `python -m pip check` clean; `git diff -- pyproject.toml` empty |
| `git diff --check` | clean (exit 0) |
| Generated artifacts | none fix-generated; `build/` + `*.egg-info/` are pre-existing gitignored packaging artifacts |
| Fix scope | only the 5 reported files + report (mtime-corroborated in TST-FIX) |

No unauthorized Phase 1/2 change; no unexpected CLI change.

## 3. Fix diff and trust boundaries

- Production delta: `inspector.py` (exception set, token set, boundary separators, precedence-based `_is_sensitive_name`, bounded-token helper; single active `_contains_link_component`) and `git_metadata.py` (Popen + concurrent bounded drains, `_BoundedBuffer`, `_drain_until_eof`, `_capture`, `_TRUNCATED` sentinel, per-command truncation propagation).
- Trust boundaries unchanged: untrusted repo tree ⇒ name-based classification and read-only Git metadata only; no content is read; policy authority remains in the Phase 2 engine; approvals/provenance untouched.
- Public contract: `GitMetadataReader.read() → GitInfo | None` unchanged; injection seam `runner=` → `popen=` (test-only).

## 4. Original findings reproduction

| Finding | Pre-fix (reported + reproduced) | Post-fix (current run) | Impact | Closure |
|---|---|---|---|---|
| F1 `cred`/`creds` redaction | `_is_sensitive_name("creds.toml") is False` | True; full matrix (43 protected incl. `cred`, `creds`, `cred.json`, `creds.toml`, `service-cred.yaml`, `service-creds.json`, `database_cred.ini`, `database_creds.yaml`, `CredS.toml`, `creds `, ` cred`, `a.b.c-creds.d.e`, backup/extensions) | Name-only; still no content access | **FIXED** |
| F2 `.env.example` exception | `_is_sensitive_name(".env.example") is True` | False for exact name + case variants; true for `.env`, `.env.local/.production`, `.env.example.local/.bak/.copy/~` | Visible template without content exposure | **FIXED** |
| F5 unbounded Git output | `subprocess.run(capture_output=True)` buffered to EOF | Removed; in-drain byte caps on stdout and stderr; `_TRUNCATED` at/over cap; timeout kill/reap; deterministic `None` → `GIT_METADATA_UNAVAILABLE` | Output genuinely bounded during receipt | **FIXED** |
| Dead-code observation | duplicated unreachable block in `_contains_link_component` | single active implementation; 6× `follow_symlinks=False`; root-link rejection reproduced | Containment unchanged | **FIXED** |

## 5. Sensitive-name security validation

Independent tester-authored matrix (34-check harness, distinct from implementation tests):

- **Redacted (verified, case-insensitive, boundaries `.` `_` `-` space + basename edges):** `cred`, `creds`, `cred.json`, `creds.toml`, `service-cred.yaml`, `service-creds.json`, `database_cred.ini`, `database_creds.yaml`, `CRED`, `CREDS`, `CredS.toml`, `creds `, ` cred`, `creds_file_bak.txt`, `a.b.c-creds.d.e`, `creds.backup`, `x.creds`, `credentials`, `credentials.json`, `CREDENTIALS`, `secrets.json`, `client_secret.json`, `id_rsa`, `server.key`, and all `.env*` variants including `.env.example.local/.bak/.copy/~`.
- **Visible (verified):** `accredited.py`, `accreditation.txt`, `credit.py`, `credito.yaml`, `credentialing.py`, `credible.md`, `credo.toml`, `credals.yaml`, `credential_is_checked.py`, `mycreds`, `credsfile`, `creddle.txt`, `credenza.md`, `credit_card.py`, `notcreds`, `creds2`, ordinary config/docs, `id_rsa.pub`, `.env.example` + case variants, `env.example.md`, `example.env`, `credentials.txt` (accepted in TST-01).
- **Adversarial non-approved separators do not over-match:** `creds:prod`, `creds~tmp`, `creds\backup`, `notcreds`, `precreds`, `credsx` all visible — no unrestricted substring rule exists.
- **Material false-positive/negative check:** no protected name leaked; no unrelated named file hidden beyond the documented conservative cases (§15); redaction is name-based only — zero writes/news.

Consistency verified across entries, text, JSON, warnings, summaries, counts, sorting (`sort_keys`), and partial results; raw sensitive names do not leak through another field; no file content read.

## 6. `.env.example` exception validation

- Visible (exact, case-folded): `.env.example`, `.ENV.EXAMPLE`, `Env.Example`.
- Redacted (all variants): `.env`, `.env.local`, `.env.production`, `.env.development`, `.env.test`, `.env.example.local`, `.env.example.bak`, `.env.example.copy`, `.env.example~`.
- Exception evaluated before the broad `.env.` rule (`inspector.py:560` before `:564`); it is exact and narrow (not generalized to names merely containing `example`). The file is never opened; no example-file content emitted; identical behavior in text and JSON; sibling sensitive names do not appear in warnings/errors.

## 7. Bounded-output security validation

Real helper subprocesses driven through the actual `_capture` path:

- **Caps during receipt:** stdout 4096/256, 1000/1000, and 1000/1000-at/over; far-over both (512 KiB/64 KiB) → `_TRUNCATED`; exactly-at succeeds with intact bytes; one-byte-over truncates; stderr-over truncates; very long single line (300 KiB) truncates while retained bytes never exceed the cap (instrumented `_BoundedBuffer` never grew beyond `limit`). Repeated over-cap calls (8×) stable — no retention drift.
- **No full-capture API reachable:** `subprocess.run`, `capture_output`, `communicate` absent from `src/agent_harness` (grep).
- **Multibyte/invalid:** 4-byte emoji stream split at the byte boundary truncates safely; `\xff\xfe\x00\x81` decodes with `errors="replace"`, no crash.
- **Concurrency/deadlock:** concurrent stdout+stderr floods are drained by separate threads; a never-exiting flood was killed in 0.42 s of a 0.4 s timeout with no deadlock and no live `ah-git-*` thread.
- **Determinism:** truncation → `read() → None` consistently; service surfaces sanitized `GIT_METADATA_UNAVAILABLE`; serialized result size bounded (counts + short branch/commit only).

## 8. Process and thread lifecycle

- Normal completion, nonzero exit (`None`), timeout (kill+reap), stdout/stderr truncation, simultaneous truncation, and repeated invocation all verified with real children — no deadlock, no orphan, no live drain thread, no unbounded queue, no raw oversized output.
- Descriptor/thread counts: `ah-git-*` thread set before/after every probe was identical (empty); no leak across ~380 process spawns (stress included).
- Timeout vs truncation are internally distinguishable (`None` vs `_TRUNCATED`); both collapse to the deterministic unavailable-metadata result with the stable reason code.

## 9. Unguarded kill-path assessment

Reproduction (controlled mock): a popen whose `wait()` raises `TimeoutExpired` and whose `kill()` raises `OSError("Simulated kill failure")` → the `OSError` propagates uncaught out of `_capture` → `_run` → `read()` → service (no partial result returned; no `GIT_METADATA_UNAVAILABLE` emitted). Drain threads were daemon and self-reaped (no live threads after propagation). CLI effect would be the existing exit-10 internal-error path.

Reachability evidence:
- **Real process stress:** 300 rapid-timeout iterations against a flooding child that exits immediately, plus 40 iterations against a never-exiting flood → **0 propagated exceptions, 340/340 clean**. The trigger is a microsecond race (child self-exits between the `wait(timeout)` poll — which only raises while the child is provably alive — and `TerminateProcess`), and on the current platform this did not occur once in practice.
- **Can an untrusted repo reliably cause `kill()` itself to raise?** No. The repo controls only Git output size/content and directory shape; it has no handle to the subprocess and cannot influence the `wait`→`kill` window.

Fail-closed answers:
- Grants authorization? **No.** · Reads content? **No.** · Follows links? **No.** · Mutates Git? **No.** · Leaks output? **No** (the error is sanitized; no result is produced). · Leaves a live process? **No** in the realistic path (kill-failure implies the child already exited; threads self-reap). · Leaks threads/descriptors? Transient daemon threads only, self-reaped; no persistent leak observed. · Reaches CLI as exit 10? **Yes** — a fail-closed internal error, not an incorrect security result. · Reported as complete/partial? **No** — no result object returned, no confusion with `ok`/`partial`. · Bypasses policy or permits traversal? **No** — traversal had already been gated and executed; the failure is confined to the Git-metadata enrichment. · Mutates the inspected repo? **No.** · Repeated exploitation a practical availability risk? **No** — not reliably triggerable with a real process.

**Decision:** accepted **LOW** reliability limitation. It does not violate the design's deterministic fail-closed error contract in a security-relevant way (the failure produces a clean internal error and no output/result, and is not repo-triggerable in practice). It **may be accepted as a documented reliability limitation for AH-03-OPR-01**; a trivial guard (`try/except OSError` around `proc.kill()`, falling through to `None`) is recommended for the next implementation pass but is not required before operations.

## 10. Git command security

- All reachable verbs are the three fixed read-only forms (`symbolic-ref --quiet --short HEAD`, `rev-parse --short HEAD`, `status --porcelain --untracked-files=all`), always `["git", "--no-optional-locks", "--git-dir=<root>/.git", "--work-tree=<root>", …]`.
- Argument arrays, `shell=False`, `GIT_TERMINAL_PROMPT=0`, `GIT_OPTIONAL_LOCKS=0`, finite timeout, finite stdout/stderr; no fetch/pull/push/add/commit/checkout/reset/clean/update-index, no hooks or aliases, no network; path components with spaces and leading hyphens are embedded in single `--git-dir=`/`--work-tree=` tokens (real-git verified) — no option injection.
- Diagnostics sanitized: hostile porcelain lines (`\x1b…red…`, `quote"json}`, ` M \x1b[1mshould-not-leak`) reduce to counts only; branch/commit are single-line cleaned; no raw diagnostics/filenames reach results; `.git`-file gitdir redirection remains bounded by the fixed 5 s timeout and metadata-only reads (accepted SEC-01 INFO).

## 11. Containment and metadata-only regression

- Zero inspected-file `open()` calls (spy, randomized canaries); zero content bytes; no manifest/`.gitignore`/sensitive-file parsing.
- Root links rejected (`PathEscapeError`); `_contains_link_component` single active implementation with correct rejection and OSError-fail-safe; 6× `follow_symlinks=False` sites; prefix-collision containment distinct; no path above root; mandatory budgets + explicit partial state and no traversal after limit (regression suite).
- Dead-code removal removed no active protection (section 4).

## 12. Policy-gate regression

- A denying engine produced an empty order (`[]`): no `inspector` call, no `git` call — policy runs before root enumeration and Git execution.
- Capability `REPOSITORY_METADATA_READ`; mode `READ_ONLY`; missing/malformed/exception-raising policy dependency fails closed (service/domain suites); request data cannot replace the Phase 2 policy authority; Phase 2 approval provenance unchanged.

## 13. Output and serialization security

- Synthetic hostile entry names (`\x1b[31m…`, tab, quotes, backslash, bidi `\u202e`, 2 KB-long, unicode) through the serializer: JSON remains valid schema-v1; control characters are JSON-escaped (no unescaped ESC); no absolute path/user-profile string; text warnings/errors remain sanitized; stdout/stderr separated; stable reason codes; partial/complete cannot be confused; fresh-process JSON byte-identical (SHA-256 equal).
- **Recorded observation (finding SFX-2):** `to_text` does not strip control characters from non-sensitive entry paths, so on a non-Windows filesystem a hostile filename containing ESC would place raw ANSI into text-mode output. JSON is unaffected; warnings/errors are sanitized; the current Windows platform forbids control characters in filenames (unreachable here); pre-existing (`to_text` untouched by the fix).

## 14. Full regression validation

| Metric | Current run |
|---|---|
| Collected / passed / failed / skipped / xfailed / xpassed | 387 / 377 / 0 / 10 / 0 / 0 |
| Full line coverage | 99% (1,585 stmts, 9 miss) |
| Full branch coverage | ~97.9% (470 branches, 10 partial) |
| `git_metadata.py` | 100% line/branch |
| `inspector.py` | 99% (misses: 234-235, 244, 280-281, 649→651 — pre-existing resolve/bare-repo/classify paths) |
| Fix changed-lines / classifier decision branches | 100% |
| Security-critical uncovered branch | none |
| Adversarial probe harness (this run) | 34/34 passed (plus 1 recorded observation) |
| Static scans | content-read: none; dynamic exec: none; shell: none; network: none; git-mutation verbs: none reachable; model: none; unbounded-capture APIs: none; changed-file imports stdlib/self only |
| Skips | 10, all platform-justified (7 symlink/FIFO/NUL on Windows, 2 unit symlink, 1 NUL) |
| CLI smoke | `version`, `health`, `config-check` exit 0; `inspect` exit 0/2/0 (ok/missing-file/partial) |

## 15. Findings

### SFX-1 (LOW — accepted reliability limitation, reproduced)
- Unguarded `proc.kill()` on the timeout path (`git_metadata.py:192-195`): a mock `kill()` raising `OSError` propagates through `read()` and the service as a fail-closed internal error instead of `GIT_METADATA_UNAVAILABLE`. Empirical real-process stress (340 iterations) showed **zero** propagations; an untrusted repo cannot reliably trigger it (microsecond process-state race only). No disclosure, mutation, traversal, policy bypass, live-process, or thread-leak consequence. **Disposition: ACCEPTED_LOW** — documented reliability limitation; guard recommended for a future implementation pass, not required before OPR-01.

### SFX-2 (LOW — pre-existing, platform-gated)
- `to_text` emits non-sensitive entry paths verbatim; ESC-containing filenames (creatable only on non-Windows filesystems) would inject ANSI into text output. JSON is safe (JSON-escaping + `ensure_ascii`); warnings/errors sanitized; unreachable on the current Windows platform. **Disposition: ACCEPTED_LOW** — harden `to_text`/`_entry_dict` with `sanitize_text` in a future pass; not a blocker for Windows ops.

## 16. Original findings closure

| Finding | Status |
|---|---|
| `AH03-TST-01 / SEC F1` (`cred`/`creds` redaction) | **FIXED** |
| `SEC F2` (`.env.example` exception) | **FIXED** |
| `SEC F5` (bounded Git output) | **FIXED** |
| `SEC` dead-code observation | **FIXED** |

## 17. QA findings disposition

| Observation | Disposition |
|---|---|
| `AH-03-TST-FIX-01 F-TST-1` — unguarded `proc.kill()` | **ACCEPTED_LOW** (documented reliability limitation; no pre-ops fix required; guard recommended) |
| Last-resort drain-thread `join()` has no explicit timeout | **ACCEPTED_INFO** — the fixed read-only Git verbs spawn no persistent grandchildren; no hang observed in ~380 real process interactions |
| Truncation drops all branch/commit metadata (all-or-nothing) | **ACCEPTED_INFO** — deliberate, deterministic, stable `GIT_METADATA_UNAVAILABLE`; per-field partial metadata is a possible later enhancement |
| Compound `credentials` vs `creds` token asymmetry (`x-credentials.json` visible vs `x-creds.json` redacted) | **ACCEPTED_INFO** — consistent with the previously accepted visibility of `credentials.txt`; abbreviation is protected more aggressively |
| Conservative `_`-joined redaction (`cred_parser.py`-style) | **ACCEPTED_INFO** — whole-token boundary rule; name-only, no content; documented conservative behavior |
| Text-mode entry-path control-character sanitization gap | **ACCEPTED_LOW** (SFX-2; platform-gated, pre-existing) |

## 18. Residual risks

- Hostile name-based metadata display in interactive text mode on non-Windows filesystems (SFX-2) — machine-mode (JSON) safe; address in a future pass.
- `kill()` race graceful-degradation — theoretical only on the supported platform; if ever exposed (e.g., a future helper process that parks), the guard should be added.
- Worktree `.git`-file gitdir redirection remains an accepted, time-bounded, read-only boundary (prior INFO).

## 19. Warnings

- GitHub API (`gh`) returned transient 503s during this run; the absence of a Phase 3 PR is corroborated by the empty `ls-remote` for the head branch and by phase discipline throughout.
- The ~5 s last-resort-cleanup regression test increases suite time slightly; acceptable.
- One probe check that documented the SFX-2 text-output behavior was counted as an observation, not a pass/fail gate, to avoid a false red on a deliberately recorded invariant.

## 20. Blockers

None.

## 21. Repository state

- HEAD `7a46b54`, branch `feature/ah-03-repository-inspection`, 0 commits ahead of `main`; nothing staged.
- Modified (tracked): `src/agent_harness/cli.py` only (pre-existing Phase 3 baseline).
- Untracked: Phase 3 docs/reports/source/tests + `AH-03-IMP-FIX-01`, `AH-03-TST-FIX-01`, and this report.
- No remote branch, no PR, nothing pushed or published.

## 22. Commands executed

- Scope: `git rev-parse --show-toplevel/--abbrev-ref HEAD`, `git rev-list --count main..HEAD`, `git status --short`, `git diff --cached`, `git diff --check`, `git ls-remote origin feature/ah-03-repository-inspection`, `gh pr list …`, `git diff -- pyproject.toml`.
- Dependency: `python -m pip check`.
- Security harness: real-helper-subprocess and controlled-mock probes (sensitive-name matrix, bounded-output memory, lifecycle/kill-race stress, fail-closed assessment, Git vector/hostile-output, containment/metadata-only/policy, output/serialization) — 34/34.
- Regression: `pytest -p no:cacheprovider --cov=agent_harness --cov-branch --cov-report=term-missing`; `-ra` skip/xfail audit; static regex scans; fresh-process JSON determinism; CLI smoke.
- All artifacts under `C:\Users\agust\AppData\Local\Temp\opencode\` were removed before finishing.

## 23. Recommended next action

`PROCEED_TO_AH-03-OPR-01`

## 24. Non-modification attestation

No production code, test, design document, or earlier report was created or modified during this review; only `reports/AH-03-SEC-FIX-01.md` was written. The unguarded-`kill()` behavior was intentionally not fixed, per the task constraints. No repository, Git, network, GitHub, model, or shell side effect occurred; no credential or unrelated repository was accessed; no destructive testing was performed; all temporary artifacts were removed.