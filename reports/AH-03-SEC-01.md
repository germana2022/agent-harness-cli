# AH-03-SEC-01 - Independent Safe Repository Inspection Security Review

## 1. Decision

**SECURITY_PASS_WITH_WARNINGS**

The Phase 3 repository-inspection feature satisfies its security requirements. Independent adversarial probing found **no HIGH or MEDIUM findings**, **two LOW findings** (one re-confirming the prior `AH03-TST-01` LOW, one newly identified), and two INFO observations. The feature is security-safe to proceed.

Recommended next action: **PROCEED_TO_AH-03-OPR-01** once the LOW findings are dispositioned in the Phase 3 implementation gate (address `AH03-SEC-01-F1` and `AH03-SEC-01-F2`).

## 2. Preconditions

| Check | Result |
|---|---|
| Git root | `D:/agente-harness` (repo `germana2022/agent-harness-cli`) |
| Current branch | `feature/ah-03-repository-inspection` |
| HEAD | `7a46b54f47f542d1c6d37f8e38343958c917eb83` |
| Commits vs `main` | 0 (no Phase 3 commits yet) |
| Staged changes | none |
| `git diff --check` | clean (exit 0) |
| `pyproject.toml` diff | none (no new dependency added) |
| Remote Phase 3 branch | absent; no PR open (confirmed via `gh`) |
| Scope discipline | only `reports/AH-03-SEC-01.md` created/updated; no source changes |
| Environment | Windows host; Phase 1 bare `python` is 3.8, so the project venv (`Python 3.11.9`) was used |

## 3. Scope and diff review

Scope: independent adversarial security review of the Phase 3 repository-inspection feature introduced since the Phase 2 merge base:

- `src/agent_harness/inspection/` (request, result, errors, serialization)
- `src/agent_harness/infrastructure/inspector.py` and `git_metadata.py`
- `src/agent_harness/application/inspection_service.py`
- `src/agent_harness/cli.py` (added `inspect` command)
- `tests/unit/inspection/`, `tests/integration/inspection/`, `tests/integration/test_cli_inspect.py`
- `docs/PHASE_03_SAFE_REPOSITORY_INSPECTION_DESIGN.md`

Only tracked modification is `src/agent_harness/cli.py`. All other Phase 3 artifacts are untracked. Review boundary: security review only; **no code repair was performed**.

## 4. Threat model and attack surface

Attacker model: an untrusted repository tree (the inspect target) supplied by a user; the reviewer additionally assumes the tree may contain malicious files, names, symlinks/junctions, oversized content, worktree `.git` files, and crafted output-formatting characters. The review also covers the orchestrating service and Git adapter as attack surfaces.

Threats evaluated:

| # | Threat | Control under review |
|---|---|---|
| T1 | File content disclosure via inspection | Metadata-only traversal; `content_bytes_read = 0` |
| T2 | Escape via symlink/junction/reparse point | Never followed; `LINK_NOT_FOLLOWED`; link-in-root rejection |
| T3 | Path traversal (`..`, prefix collision, unicode) | Root containment + relative path computation |
| T4 | TOCTOU / race between enumeration and stat | Stat-once snapshots; failures become warnings/size-0 |
| T5 | Sensitive-name disclosure (real secrets bearing names) | Name-based redaction |
| T6 | Resource exhaustion (depth/width/bytes/warnings) | Mandatory budgets + partial results |
| T7 | Git metadata exfiltration or mutation | Read-only pinned commands, no shell/network/prompt |
| T8 | Policy bypass (inspection without Phase 2 gate) | Policy decision before traversal and Git |
| T9 | Output/terminal injection (ANSI, control chars, newlines) | Sanitization of warnings/errors and serialized output |
| T10 | Serialization integrity / partial-not-reported-complete | `status`/`partial`/`limit` consistency |
| T11 | Supply-chain / new side effects | No dependency changes; no network/model/shell |

## 5. Metadata-only (content-read) verification

Independent instrumented probe (monkeypatched `builtins.open`):
- Zero `open()` calls across the full service path (resolver -> policy gate -> inspector -> git -> serialization), including partial-limit and sensitive-redaction paths.
- `content_bytes_read` is hard-coded `0` in `inspection_service.py:72`; surfaced in JSON and text output.
- Canary contents (`CANARY_*`) written into files inside the target tree were never present in any JSON/text output.
- Static scan: no `read_text`/`read_bytes`/`open()`/`os.open` calls anywhere in `src/agent_harness`.

**Result: PASS.** The inspector is strictly metadata-only.

## 6. Root containment and path attack resistance

Adversarial path cases verified:

| Case | Result |
|---|---|
| `requested_path` with `..` components that resolve inside the repo | normalized; `..` never appears in output paths |
| Prefix-collision sibling dirs (`a` vs `ab`) | entries remain distinct; no bleed-through |
| Unicode + spaces in names (`café dir/é.py`) | handled; valid relative paths emitted |
| Requested path whose ancestor is a symlink | `PathEscapeError` raised (mocked `os.path.islink`; Windows lacks symlink privilege) |
| Output paths | always POSIX-relative under the root; no absolute, no `..` |

`resolve_inspection_root` (inspector.py:211) checks `_contains_link_component` on the full lexical path before returning a root; the walker computes `repository_relative_path` via `Path(path).relative_to(root)`.

**Result: PASS.** No path-traversal or containment escape found.

## 7. Link, junction, reparse, and special-entry resistance

- Links are classified (`EntryKind.SYMLINK/JUNCTION/REPARSE_POINT`) via `entry.is_symlink()` plus Windows `st_reparse_tag` discrimination, and are **never followed** (`follow_symlinks=False` everywhere).
- `link_policy="error"` raises `LinkEncounteredError`; default emits `LINK_NOT_FOLLOWED` and records the link's own lstat metadata only.
- A link-to-outside placed in a child dir would be reported, not traversed; the queue only ever appends directory entries classified with `follow_symlinks=False`.
- A `.git` directory (the hard exclusion) is checked with `is_dir(follow_symlinks=False)`, so a `.git` *symlink* is not silently skipped as a dir; it is classified as a link and not followed.
- Windows junction/reparse handling is exercised via mocked equivalents (no symlink privilege and no FIFO creation on this host), consistent with the test suite's documented platform skips.

**Result: PASS.** No link/junction/reparse traversal.

## 8. TOCTOU / race handling

Race: an entry's kind or metadata changes between enumeration and stat.
- `_entry_size` uses `entry.stat(follow_symlinks=False)`; an `OSError` (entry vanished) yields a `FILESYSTEM_CHANGED` warning and a size-0 snapshot entry (verified via a synthetic `DirEntry` whose `stat` raises). No content is read and no link is followed on the raced entry.
- Sizes are captured once; the design's stat-once semantics hold (size is a snapshot, and skew becomes a warning or is reconciled in `total_metadata_size`).
- Directory read failures under race become `FILESYSTEM_CHANGED` warnings or `PermissionDeniedError`/`InspectionInternalError` under `error_policy="fail"`.

**Result: PASS.** Races fail closed (no follow, no read, warning emitted).

## 9. Sensitive-name and redaction policy

Systematic matrix probe over 27 candidate names:

| Category | Result |
|---|---|
| `.env`, `.env.local`, `.env.production`, `.env` prefix family | redacted |
| `id_rsa`, `id_ed25519`, `id_ecdsa`, `id_dsa` | redacted |
| `credentials`, `credentials.json`, `credentials.toml`, `secrets.json` | redacted |
| `.npmrc`, `.pypirc`, `.netrc` | redacted |
| `*.key`, `*.pem`, `*.p12`, `*.pfx`, `*.jks`, `*.keystore`, `*.secret` | redacted |
| `id_rsa.pub` (public key), `credentials.txt`, `cred.json`, `token.py`, `password_manager.py`, `keyboard.py`, `.env.example` handling | visible unless matched below |
| Redaction mechanics | stable per-walk `<sensitive-N>` tokens; distinct for distinct files; count in `sensitive_entries`; no content read or printed |

`credentials.txt` and `id_rsa.pub` are correctly visible (not secret-bearing). No sensitive variant leaked. Two issues found (see Findings): a false negative for `creds.toml`/`creds` (F1, re-confirms TST-01) and a false positive for `.env.example` (F2).

**Result: PASS WITH WARNINGS.** See Findings F1/F2.

## 10. Resource-exhaustion resistance

| Budget | Enforcement verified |
|---|---|
| `max_entries` | `LIMIT_ENTRIES_EXCEEDED`, walk stops |
| `max_depth` | `LIMIT_DEPTH_EXCEEDED` on 40-deep synthetic tree |
| `max_directories` | `LIMIT_DIRECTORIES_EXCEEDED` on 500-dir synthetic tree |
| `max_total_bytes` / `max_individual_file_bytes` | `LIMIT_TOTAL_BYTES_EXCEEDED` / `FILE_TOO_LARGE` warning |
| `max_path_length` | `PATH_TOO_LONG` warning (300 x 250-char-name pathological tree) |
| `max_manifests` / `max_warnings` | `LIMIT_MANIFESTS_EXCEEDED` / `LIMIT_WARNINGS_EXCEEDED` |
| Invalid budgets (`max_entries=0`, negatives, `max_depth=10**9`) | rejected by `InspectionRequest` validation before traversal |

The walker is breadth-first over an explicit queue; no recursion-depth risk. Pathological tree completed without crash or unbounded growth.

**Result: PASS.**

## 11. Git adapter security boundary

`GitMetadataReader` (`git_metadata.py`):
- Commands are fixed and read-only: `symbolic-ref --quiet --short HEAD`, `rev-parse --short HEAD`, `status --porcelain --untracked-files=all`.
- `--git-dir=<root>/.git` and `--work-tree=<root>` are pinned; a path beginning with `-` was verified to be safe (single `--git-dir=...` token, no option injection).
- Executed via argument array (`subprocess.run`, no `shell=True`); `GIT_TERMINAL_PROMPT=0` and `GIT_OPTIONAL_LOCKS=0`; 5s timeout; output parsed to counts only (bounded to `max_status_lines`).
- No network, fetch, remote, credential-helper, or mutation path exists (static scan clean). No config-conditional subprocess is invoked; `GIT_CONFIG_NOSYSTEM` is not set but the invoked commands are aliases-safe fixed verbs and cannot trigger credential/network behavior.
- Worktree `.git`-file indirection (a `.git` *file* with a `gitdir:` line) can redirect git to an attacker-chosen git dir; verified graceful (invalid target -> returncode!=0 -> `None`, `GIT_METADATA_UNAVAILABLE` warning). See Findings F3/F5.

**Result: PASS WITH OBSERVATIONS.** See Findings F3/F5 (INFO).

## 12. Phase 2 policy-gate security

Orchestration (`inspection_service.py:47-50`): resolver -> `_assert_allowed` (policy gate) -> inspector traversal -> Git read. Verified with spy components that:
- A deny decision blocks before any traversal or Git call (spy order `[]`).
- A raising policy engine blocks traversal and surfaces the error.
- A malformed (non-decision) policy result blocks traversal.
- Git metadata is only attempted after a successful gate and only for `git_worktree`/`git_bare` roots with `git_metadata != "off"`.

**Result: PASS.** No policy bypass.

## 13. Output and injection resistance

- JSON: valid, `sort_keys=True`, `ensure_ascii=True`; no ANSI (`\x1b`) present; control characters/newlines in filenames cannot forge records.
- Text: no raw ANSI emitted; entries display-limited (200) with explicit truncation marker.
- Git failure diagnostics are mapped to a sanitized `GIT_METADATA_UNAVAILABLE` warning (no raw stderr propagated).
- Warnings/errors pass through `sanitize_text` (control chars stripped).
- Redacted paths replace the filename token; `requested_path` in the result is sanitized; absolute machine paths are not emitted (`resolved_root="."`).

**Result: PASS.**

## 14. Serialization and determinism integrity

- Fresh-process determinism: two independent CLI invocations of `inspect --git` produced byte-identical JSON (SHA-256 `B481763F...`).
- `partial`/`status`/`limit` are mutually consistent (verified on a 20-file/`max_entries=5` tree: `status="partial"`, `partial=true`, `limit.code="LIMIT_ENTRIES_EXCEEDED"`).
- Result dataclasses are frozen; entries are tuples; the JSON payload is a fresh dict.
- Omitted zero-valued optional fields are a schema-v1 design choice (validated against serialization unit tests and design `§ Schema v1`).

**Result: PASS.**

## 15. Partial-result integrity

Verified: a truncated walk is always reported as `partial` with a non-null `limit` carrying the specific exceeded-budget code. Warnings captured during a truncated walk are retained. No path produces `status="ok"` while a limit is set.

**Result: PASS.**

## 16. Side-effect and dependency audit

Static scans across `src/agent_harness`:
- No file content reads (see §5).
- No mutating Git verbs (`add|commit|push|fetch|pull|remote|checkout|reset|clean|restore|switch|merge|rebase|...`) — the only matches are unrelated identifiers (`commit` field names, `os.path`).
- No network clients (`urllib|requests|httpx|socket|aiohttp`), no `shell=True`, no LLM/model calls.
- `pyproject.toml` unchanged: **no new dependency** introduced.

**Result: PASS.**

## 17. Regression validation (tests, coverage, CLI)

- Full suite: **343 passed, 10 skipped** (Windows platform skips documented), run with `pytest -p no:cacheprovider --cov=agent_harness --cov-branch --cov-report=term-missing`.
- Coverage: **99% lines** (1490 stmts, 9 miss), **~97.8% branch** (442 branches, 10 partial). `inspection_service.py`, `git_metadata.py`, and `inspection/request.py|result.py` at 100%; `inspector.py` 99% (misses are `InspectionInternalError`/bare-repo/rare edge paths).
- CLI smoke: `version`, `health`, `config-check` exit 0; `inspect --path <repo> --git` exit 0 with correct text summary (86 files, 15 dirs, content bytes read 0); `inspect --git` JSON shows `git.branch=feature/ah-03-repository-inspection`, `commit=7a46b54`, `dirty=true`, `tracked_count=1`, `untracked_count=23` (matches `git status`), `content_bytes_read=0`.

## 18. Findings

### AH03-SEC-01-F1 (LOW, re-confirms `AH03-TST-01` LOW)
- **Area:** `inspector.py` `_is_sensitive_name` / `SENSITIVE_EXACT`.
- **Detail:** `creds.toml` and bare `creds` filenames are **not** redacted; they are common credential-config names and are not matched by the current exact/suffix rules (the design's `credentials*` pattern requires the full `credentials` stem). Impact is name-only disclosure (no content), but these filenames are conventional secret-bearing.
- **Recommendation (implementation gate):** extend `SENSITIVE_EXACT` with `creds`, `creds.toml` (and consider `.pgpass`). Verify no over-redaction of source names.

### AH03-SEC-01-F2 (LOW, newly identified)
- **Area:** `inspector.py` `_is_sensitive_name` `.env.*` prefix rule.
- **Detail:** `.env.example` is redacted by the `.env.*` prefix rule, but `docs/SECURITY_MODEL.md:52` designates `.env.example` as the **only** environment-template exception that must remain visible. This is a false positive: safe template files are hidden from inspection output (conservative direction, no disclosure).
- **Recommendation (implementation gate):** exempt the exact name `.env.example` from the `.env.*` prefix rule (and add a regression test).

### AH03-SEC-01-F3 (INFO)
- **Area:** `git_metadata.py` `_run`.
- **Detail:** for a worktree whose `.git` is a *file* (gitdir indirection), `--git-dir=<root>/.git` lets git follow an attacker-controlled `gitdir:` target. Verified graceful (invalid target -> `None` + `GIT_METADATA_UNAVAILABLE`). Residual risk is limited to bounded, read-only metadata reads within the 5s timeout; no content, no network, no mutation.
- **Recommendation (optional):** resolve `.git`-file gitdir targets and pin `--git-dir` to the resolved directory; or document the bounded-timeout reliance.

### AH03-SEC-01-F4 (INFO)
- **Area:** `inspector.py` `_contains_link_component`.
- **Detail:** duplicated unreachable block (lines 285-296) is dead code. Cosmetic only.
- **Recommendation (optional):** remove the dead block.

### AH03-SEC-01-F5 (INFO)
- **Area:** `git_metadata.py` output capture.
- **Detail:** `subprocess.run(capture_output=True)` buffers the full `git status` stdout before the 10k-line parse cap; a pathological tree could produce a large in-memory buffer within the 5s timeout. Bounded and counts-only, but streaming/capping would reduce peak memory.
- **Recommendation (optional):** stream/limit stdout capture, or document the accepted bound.

## 19. Warnings

- Windows platform skips: symlink/junction/FIFO paths are exercised through mocked equivalents; results are consistent with the documented test-suite platform handling.
- The `C:\Users\agust` host path is itself a git repository; all probes used injected resolvers or self-contained synthetic `.git` fixtures, matching the known Phase 2 INFO.

## 20. Blockers

None.

## 21. Repository state

- HEAD `7a46b54`, branch `feature/ah-03-repository-inspection`, 0 commits ahead of `main`.
- Modified: `src/agent_harness/cli.py` (Phase 3 `inspect` command).
- Untracked: Phase 3 docs/reports/source/tests as listed in §3.
- No files committed or staged; no remote branch or PR.

## 22. Commands executed

- `git rev-parse --show-toplevel/--abbrev-ref HEAD`, `git rev-list --count main..HEAD`, `git status --short`, `git diff --check`, `git ls-remote --heads origin feature/ah-03-repository-inspection`, `gh pr list --head feature/ah-03-repository-inspection`
- Adversarial probe script (probes for content-read, containment, race, sensitive matrix, budgets, git option-injection, policy-gate spies, output injection, partial integrity) — **29 checks, 28 pass / 1 expected finding (F2)**; sensitive substrings re-verified with regex boundary matching.
- Targeted probes: gitdir-file indirection, link-in-root rejection, pathological tree, fresh-process JSON determinism.
- `pytest -p no:cacheprovider --cov=agent_harness --cov-branch --cov-report=term-missing` (343 passed, 10 skipped)
- Static scans: content-read, mutating-Git, network, shell, LLM; `git diff -- pyproject.toml`
- CLI smoke: `version`, `health`, `config-check`, `inspect --path ... --git/--no-git`, `--output json`

## 23. Non-modification attestation

No source, test, design, or report file other than `reports/AH-03-SEC-01.md` was created or modified during this review. No code repair was performed. All probe and smoke artifacts were written to `C:\Users\agust\AppData\Local\Temp\opencode\ah03-sec\` outside the workspace. Findings F1/F2 are left for the Phase 3 implementation gate; none block proceeding to `AH-03-OPR-01`.
