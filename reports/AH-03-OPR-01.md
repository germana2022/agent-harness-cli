# AH-03-OPR-01 — Safe Repository Inspection Operational Validation Report

## 1. Operational decision

- Decision: OPERATIONAL_PASS_WITH_WARNINGS
- Timestamp: 2026-08-17
- Repository: `germana2022/agent-harness-cli`
- Git root: `D:/agente-harness`
- Branch: `feature/ah-03-repository-inspection`
- Base commit: `7a46b54f47f542d1c6d37f8e38343958c917eb83`
- Execution mode: WRITE_CONTROLLED_REPORT_ONLY

All supported public workflows are operationally usable, deterministic, metadata-only, and side-effect-free. Two accepted `LOW`/`INFO` reliability observations are recorded; neither affects usability, security, or the published contract, and neither requires a correction before controlled Git publication. No `BLOCKER`, `HIGH`, or `MEDIUM` finding.

Recommended next action: **PROCEED_TO_AH-03-GIT-01**.

## 2. Preconditions

| Check | Result |
|---|---|
| Git root / branch / HEAD | `D:/agente-harness`, `feature/ah-03-repository-inspection`, `7a46b54…` |
| Commits ahead of `main` | 0 |
| Staged changes | none |
| Modified (tracked) | only `src/agent_harness/cli.py` (pre-existing Phase 3 `inspect` command) |
| Untracked | exact Phase 3 inventory: design + reports (ARC/IMP/TST/SEC/IMP-FIX/TST-FIX/SEC-FIX) + `application/`, `infrastructure/`, `inspection/` + 10 Phase 3 test files |
| Remote Phase 3 branch | absent (`git ls-remote origin feature/ah-03-repository-inspection` → empty) |
| Phase 3 PR | none |
| Dependency state | `python -m pip check` clean; `git diff -- pyproject.toml` empty |
| `git diff --check` | clean (exit 0) |
| Generated artifacts | none in repo; no coverage/`__pycache__`/`htmlcov` artifacts added (grep of `git status` clean) |
| Phase 1/2 changes | none beyond the pre-existing `cli.py` |

The repository state matched the authorized state exactly throughout.

## 3. Public package and import behavior

Fresh-process import smoke of every Phase 3 public module (`agent_harness.inspection.*`, `infrastructure.{inspector,git_metadata}`, `application.inspection_service`, `cli`, `domain`, `config`) succeeded with **zero** files created, zero threads started, zero subprocesses launched, and zero stdout/stderr. Importing all modules with an empty `PATH` (no `git`) succeeded — Git availability is not required to import or use non-Git inspection. Framework imports (typer) remain confined to the CLI module; immutable value modules (`request`, `result`, `errors`) have no framework dependency. Operational workflows used only public construction paths (`agent_harness.cli.app`, `InspectionService`, `Inspector`, `GitMetadataReader`, `InspectionRequest`) — no private imports required.

## 4. CLI discoverability

- `python -m agent_harness --help` and `python -m agent_harness inspect --help` render readable option/command listings, exit 0, no traceback.
- Global: `--output text|json`, `--verbose`, `--no-color`; `--no-color` help emitted no ANSI (verified `chr(27)` absent).
- `inspect` sub-options: `--path` (default: current directory), `--max-entries` (bounded, 1..1,000,000), `--max-depth` (bounded, 1..1024), `--git` / `--no-git`.
- Phase 1 commands (`version`, `health`, `config-check`) remain visible and unchanged; module (`python -m agent_harness`) and console (`agent-harness`) entry points both work (console `--version` is not a defined option — consistent pre-existing behavior, matches `version` command).

## 5. Default repository workflow

From `D:/agente-harness`, `inspect` with defaults: exit 0; root classified `git_worktree`; with `--git`, branch `feature/ah-03-repository-inspection`, short commit `7a46b54`, `dirty=true` exactly matching `git status`; `.git` never appears as an entry; uncommitted Phase 3 files are inventoried consistently; no absolute path in JSON; `content_bytes_read=0`; text human-readable; JSON valid schema-v1. Bounded runtime (~0.6–0.8 s per invocation).

## 6. Git and non-Git workflows

Isolated synthetic Git repos (all under a git-free fixture base on `D:\`): clean branch, dirty working tree, detached HEAD, path containing spaces, and empty repo — branch/commit/dirty state correct in every case; `--no-git` triggered **no** Git subprocess (popen-trap spy verified); inspection never mutated any repo (`git status -b` before == after). Non-Git directory with default path, relative path, and absolute path all classify `directory`, succeed with `--git` (no `git` section, no failure from absent metadata), and emit machine-path-independent JSON. A git-free base was essential: the earlier `C:\Users\agust`-based fixture inherited that path's git ancestry (known INFO), which the corrected base resolved.

## 7. Metadata-only and sensitive-name workflows

Service-path `open()` spy: **zero** opens over a fixture with source/manifest/README/`.gitignore`/`.env.example`/protected `.env`/`creds`/`server.key`/large binary/PNG files; `content_bytes_read=0`; no canary content leaked into text or JSON; manifest and language classification are name/metadata-based; `.gitignore` is inventoried as metadata only (never parsed); `.env.example` appears as allowed metadata; `.env` and `.env.local` are refused at the default hidden setting; `creds.toml`, `service-creds.yaml`, `server.key` redacted; big-file entries carry size without content reads; binary classified by name. `secrets.dev.json` remains visible (pre-existing exact-only secret matching — recorded INFO). CLI text+JSON redaction/visibility verified; no raw protected name leaks through sorting, counts, or Git output.

## 8. Ignore and nested-repository workflows

`.git` always excluded; nested repository (`inner` with its own `.git`) not traversed; `node_modules/` and `.venv/` excluded by default and included with `include_ignored` (design); boundary-aware — `node_modulesx` sibling remains visible; `.gitignore` content does not drive Phase 3 (`secret_ignored.txt` still inventoried); results deterministic.

## 9. Link and containment workflows

Real-symlink fixtures are not creatable without elevation on this host (documented platform limit); containment/link behavior was verified with the existing mocked/unit coverage (root-link → `PathEscapeError`; `follow_symlinks=False` in 6 inspector sites; cycles impossible because links are never followed). External targets never enumerated; warnings sanitized; link-policy error behavior deterministic (covered by the unit suite). No external absolute path disclosed.

## 10. Budgets and partial results

- Empty directory: `status=ok`, 0 files. Exact entry limit and one-beyond: `LIMIT_ENTRIES_EXCEEDED`, `partial=true`, exit 0, `file_count` capped. Depth limit: `LIMIT_DEPTH_EXCEEDED`. Wide/deep trees bounded.
- Invalid values — `0`, `-1`, `1_000_000_000_000` (above max), non-integer, `--max-depth 0`, `--max-depth 1e10` — all rejected before traversal (exit 2, clear message, no traceback). Mandatory limits cannot be disabled; traversal stops promptly; gathered results deterministic; partial is explicit and cannot be confused with complete.
- Operators can distinguish partial from complete via the `status`/`partial`/`limit` fields.

## 11. Git failure, truncation, and lifecycle

Via injected adapters: Git not installed, nonzero exit, timeout, stdout-over-cap, stderr-over-cap, and concurrent stdout+stderr flood all yield (exit-0) inspection with `GIT_METADATA_UNAVAILABLE`; no raw output leaks; no deadlock; no live process/thread (thread set before/after); no repository mutation; serialized output bounded; **filesystem metadata remains fully usable when Git metadata is unavailable** (the returned result still inventories files — verified `file_count==1` with `a.py` present). Normal Git metadata unchanged below the cap. All-or-nothing Git truncation is represented as git-absent with the stable unavailability warning (design-documented).

## 12. Error-consumer behavior

- Missing path → exit 2, `path not found`, no traceback. File-as-root → exit 2, `not a directory`, no traceback. NUL path → rejected in-process (exit 2, no traceback; NUL cannot cross subprocess argv). Invalid option → exit 2, no traceback. Success → stdout populated, stderr empty; no traceback ever on expected paths.
- Policy denial and raising-policy dependency → fail closed before traversal/Git.
- Accepted `kill()` mock (controlled, non-mutating): CLI reports exit **10** (`error: unexpected internal error`) with **no traceback**, **no raw Git output** (distinct stdout/stderr markers absent), and **no result falsely reported** as success. Matches the accepted fail-closed LOW documented by SEC-FIX-01.

## 13. Policy-before-operation validation

Deny-policy engine → **zero** `inspector` calls and **zero** `git` calls (order `[]`); raising policy → fails closed with no traversal; capability `REPOSITORY_METADATA_READ`; mode `READ_ONLY`; no approval required for this read-only operation; request input cannot select a policy authority (phase-2 engine owns the decision; provenance unchanged).

## 14. Determinism

Fresh-process byte-identical JSON for: `--no-git`, `--git`, partial (`--max-entries 2`), and git-unavailable roots; identical across different current working directories; creation-order-independent (two fixture trees built in opposite orders hash equal); text mode byte-identical; no timestamps/random IDs; no absolute machine path; stable ordering. All confirmed by SHA-256 equality.

## 15. Side-effect validation

Before/after a representative git fixture inspection (CLI + service): file inventory (recursive `rglob` + sizes), `git status -b`, branch, commit, running thread set, environment, and cwd all **unchanged**. No file create/modify/rename/delete/chmod/timestamp write; no Git mutation; no network/GitHub/model/telemetry/container; no env/cwd change; no background process/thread leak; no unsolicited output.

## 16. Phase 1 and Phase 2 regression

- Phase 1: `version` (`agent-harness 0.1.0`), `health`, `config-check` exit 0, JSON health; module/console entry points; help; exit-code + stdout/stderr contracts — all unchanged.
- Phase 2: default READ_ONLY, `REPOSITORY_METADATA_READ` capability, policy denial precedence, approval provenance, scope binding, atomic approval consumption, replay prevention, no Phase 2 CLI expansion — all covered by the unaffected Phase 2 suite inside the full run. Phase 3 introduced no change to Phase 1/2 behavior.

## 17. Full validation results

| Metric | Current run |
|---|---|
| Tests collected / passed / failed / skipped / xfailed / xpassed | 387 / 377 / 0 / 10 / 0 / 0 |
| Line coverage | 99% (1,585 stmts, 9 miss) |
| Branch coverage | ~97.9% (470 branches, 10 partial) |
| `git_metadata.py` | 100% line/branch |
| `inspector.py` | 99% (misses 234-235, 244, 280-281, 649→651 — pre-existing resolve/bare-repo/classify paths) |
| Security-critical uncovered branch | none |
| Operationally relevant skip justification | all 10 skips platform-only (7 symlink/FIFO/NUL on Windows, 2 unit symlink, 1 NUL); Windows exhausts the symlink cases with mocked equivalents |
| Operational probes (this run) | **66 + 28 = 94 passed, 0 failed** |
| Static scans | content-read, dynamic-exec, shell, network, model, unbounded-capture, env/cwd-mutation: none; git-mutation verbs: no reachable literal (only a dict field-name false positive); changed files import stdlib/self only |
| `pip check` / `git diff --check` | clean / clean |

## 18. Findings

### OPR-1 (LOW — accepted reliability limitation; pre-existing)
- Unguarded `proc.kill()` on the Git-timeout path (SEC-FIX established). Operationally re-verified: not triggerable through any practical fixture workflow; the controlled mock degrades to exit-10 fail-closed with no raw-output leak and no false-complete result. **Accepted** for this phase; a guard is recommended for a future implementation pass (not required before publication).

### OPR-2 (INFO — pre-existing exact-only secret-name matching)
- `secrets.dev.json` (non-exact composite) is visible as metadata because secret matching is exact-name/extension based. Name-only; no content access; consistent with prior acceptances. Safer-but-not-complete exactness; **INFO**.

### OPR-3 (INFO — default hidden-file behavior)
- At the CLI default, dotfiles including `.env.example` and `.env.local` are withheld by the hidden-file default (`include_hidden=False`), so `.env.example` is "visible" only in the metadata sense (not redacted-as-sensitive) when hidden files are included. `.env.example` is not treated as sensitive; the hidden default is a separate documented policy. **INFO**.

### OPR-4 (INFO — accepted)
- `C:\Users\agust` is itself a git repo; non-Git operational fixtures must be created on a git-free base (e.g., `D:\`) — resolved and documented. **INFO** (environmental).

## 19. Accepted residual risks

- The `proc.kill()` LOW (OPR-1): fail-closed exit-10, no disclosure/mutation/leak, not reliably triggerable.
- Exact-only secret matching for non-standard composite names (OPR-2): metadata-only, conservative visibility.
- Hidden-dotfile default (OPR-3): documented project behavior for `inspect`; operators wanting hidden metadata use `include_hidden` (design/serialization path), distinct from sensitive redaction.
- Windows cannot create symlinks without elevation: the feature still refuses-and-classifies via mocked/link-policy coverage.

None of these block controlled publication.

## 20. Warnings

- The full suite includes one ~5 s last-resort-cleanup regression test; acceptable.
- All 10 skips remain justified (platform-only).
- The console entry point does not define `--version` (no `--version` option at the group level); `version` is the supported command — pre-existing, consistent, documented.

## 21. Blockers

None.

## 22. Repository state

- HEAD `7a46b54`, branch `feature/ah-03-repository-inspection`, 0 commits ahead of `main`; nothing staged.
- Modified (tracked): `src/agent_harness/cli.py` only (pre-existing Phase 3 baseline).
- Untracked: the full authorized Phase 3 inventory plus the reports through `AH-03-SEC-FIX-01` and this report.
- No remote branch, no PR, nothing pushed or published; no fixture or temporary artifact remains on disk (verified at `D:\` root and in the repo).

## 23. Commands executed

- Scope: `git rev-parse --show-toplevel/--abbrev-ref HEAD`, `git rev-list --count main..HEAD`, `git status --short`, `git diff --cached`, `git diff --check`, `git ls-remote origin feature/ah-03-repository-inspection`, `git diff -- pyproject.toml`, `git ls-files --others --exclude-standard`.
- Dependency/import: `python -m pip check`; fresh-process import smoke with empty `PATH`; `python -m agent_harness --help / inspect --help`; `agent-harness` console parity.
- Operational harnesses (operator-authored): `opr_a.py` (66 checks: default/non-Git/Git workflows, metadata+sensitive, ignore/nested, budgets/partial, error-consumer) and `opr_b.py` (28 checks: Git failure/truncation, kill-mock exit-10, policy-before, determinism, side-effect attestation).
- Regression: `pytest -p no:cacheprovider --cov=agent_harness --cov-branch --cov-report=term-missing`; `-ra` skip audit; static scans; Phase 1 smoke.
- All fixtures/artifacts created exclusively under `C:\Users\agust\AppData\Local\Temp\opencode\ah03-opr\` and `D:\opr-fixtures-*`/`D:\opr-b-*`; all removed before finishing.

## 24. Recommended next action

`PROCEED_TO_AH-03-GIT-01`

## 25. Non-modification attestation

No production code, test, design document, or earlier report was created or modified during this validation. Only `reports/AH-03-OPR-01.md` was written. During fixture base-setup a transient mis-set directory (`Path("D:")` drive-relative) briefly created fixture folders inside `D:\agente-harness\`; these were fully removed and the repository verified to be byte/state-identical to the authorized state (git status matches exactly); no file was modified, staged, committed, or tracked-side effects. No repository, Git, remote, GitHub, model, network, or shell side effect remains; no unrelated repository was inspected; the accepted `proc.kill()` warning was not fixed; all temporary artifacts were removed.