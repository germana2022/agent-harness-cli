# AH-02-TST-01 — Independent Domain Contracts and Policies QA Report

## 1. Decision

- Decision: PASS
- Timestamp: 2026-08-14
- Repository: germana2022/agent-harness-cli
- Git root: D:/agente-harness
- Branch: feature/ah-02-domain-contracts
- Base commit: f9f28a1ef77e06ec3607b1bf4b7b30917aaed257
- Execution mode: WRITE_CONTROLLED_REPORT_ONLY

## 2. Preconditions

| Check | Result | Evidence |
|---|---|---|
| Git root | D:/agente-harness | `git rev-parse --show-toplevel` |
| Current branch | feature/ah-02-domain-contracts | `git branch --show-current` |
| HEAD | f9f28a1... | `git rev-parse HEAD` |
| Base commit | f9f28a1... (main == origin/main) | `git rev-parse main`, `git rev-parse origin/main` |
| Feature commits | 0 | `git rev-list --count main..HEAD` |
| Staged files | none | `git diff --cached` |
| Authorized changes | Phase 2 design/report/domain/tests only | `git status --short` |
| Unexpected changes | none | `git status` |
| Remote feature branch | none | `git ls-remote --heads` |
| Existing Pull Request | none | `gh pr list` |

## 3. Scope and diff review

| Check | Result | Evidence |
|---|---|---|
| Created files | 24 untracked: 3 Phase 2 docs/reports, 10 domain modules, 10 test files, conftest.py | `git ls-files --others --exclude-standard` |
| Modified files | none (tracked) | `git diff` empty |
| Deleted files | none | — |
| Unexpected files | none | — |
| Generated artifacts | none staged or tracked | git status; `.pytest_cache` ignored and pre-existing |
| Phase 1 files unchanged | yes | `git diff -- pyproject.toml cli.py test_cli.py ...` empty |
| Dependency files unchanged | yes | pyproject.toml unchanged |
| Diff check | clean (exit 0) | `git diff --check` |
| Scope result | within approved Phase 2 scope plus `conftest.py` (classified below) | — |

## 4. Architecture conformance

| Contract | Result | Evidence |
|---|---|---|
| Module plan | PASS — exactly 10 domain modules | files present |
| Immutable objects | PASS — frozen dataclasses, immutability tests | test_actions/test_approvals/test_transitions |
| Mode model | PASS — READ_ONLY/WORKSPACE_WRITE/DELIVERY, default READ_ONLY | modes.py; tests |
| Capability taxonomy | PASS — 14 capabilities | probe |
| Category count | PASS — 6 categories, matching the design (see §5) | probe + design §6 |
| Transition matrix | PASS — all 9 cells verified | §8 below |
| Policy precedence | PASS — documented order exercised with conflicts | §6 below |
| Default deny | PASS | §6 below |
| Allowlist semantics | PASS — exact/bounded, deny-first, ambiguous ties | §7 below |
| Approval model | PASS — immutable, validated | approvals.py; tests |
| Approval lifecycle | PASS | §9 below |
| Replay prevention | PASS — single-use, concurrent-safe | §10 below |
| Stable reason codes | PASS — 17 codes | policy.py; tests |
| Domain errors | PASS — DomainError hierarchy; denials are decisions | probe |
| Framework independence | PASS — AST import scan clean | test_framework_independence |
| No CLI impact | PASS — no new command; Phase 1 CLI unchanged | diff empty |
| No dependency impact | PASS | pyproject unchanged |

## 5. Reported discrepancy resolution

| Item | Classification | Evidence | Impact |
|---|---|---|---|
| Six implemented categories vs seven designed | COMPLIANT — the authoritative design §6 defines exactly six categories (READ, LOCAL_WRITE, EXECUTION, GIT_MUTATION, EXTERNAL, DESTRUCTIVE). The "seven" figure appears only in the architecture report, which is lower authority than the design. | design §6 lines 163-172; probe shows 6 categories | None; the implementation matches the design |
| `tests/unit/domain/conftest.py` | JUSTIFIED_REFINEMENT — pytest support file providing fixtures/factories; it defines no tests and does not expand the test scope. | file content; pytest collects only test_*.py | None |
| `ApprovalRecord.required_mode` | JUSTIFIED_REFINEMENT — required to enforce the mandated "approval mode mismatch → deny" requirement (explicit in the implementation prompt's default-deny and test lists and consistent with design §22 strict action/target/scope matching). It is derived from `ApprovalRequest.required_mode` (design §11) and cannot weaken enforcement. | approvals.py; manager record_decision; tests | None |

## 6. Policy and default-deny validation

| Scenario or contract | Result | Reason code or evidence |
|---|---|---|
| Hard-prohibition precedence | PASS | hard prohibition beats a valid approval (probe) |
| Mode precedence | PASS | mode denial beats a valid approval (probe) |
| Deny-rule precedence | PASS | explicit deny beats allow (suite + probe) |
| Ambiguous rule denial | PASS | equal-priority allow tie → `POLICY_CONFIGURATION_ERROR` (suite) |
| Unknown input denial | PASS | unknown action → `ACTION_UNKNOWN` (suite) |
| Missing input denial | PASS | missing target → `TARGET_MISSING` (suite) |
| Missing approval denial | PASS | `APPROVAL_REQUIRED` (probe) |
| Approval mismatch denial | PASS | `APPROVAL_SCOPE_MISMATCH` (action/target/scope/mode) (suite + probe) |
| Expired approval denial | PASS | `APPROVAL_EXPIRED` (probe, injected clock) |
| Consumed approval denial | PASS | `APPROVAL_CONSUMED` (probe) |
| Revoked approval denial | PASS | `APPROVAL_REVOKED` (suite) |
| Valid approval decision | PASS | `ALLOWED` when all conditions satisfied (probe) |

All denials are returned as `PolicyDecision` objects; no denial raised an exception.

## 7. Allowlist validation

| Contract | Result | Evidence |
|---|---|---|
| Exact matching | PASS | suite + probe |
| Bounded prefix | PASS | `repo:main:src/lib/` matches children, not `libx` (probe) |
| Bounded suffix | PASS | suite |
| Boundary enforcement | PASS | near-boundary exact non-match (`a.py` vs `a.pyx`) (probe) |
| No substring behavior | PASS | `xrepo:main:src/a.py` does not match (probe) |
| No implicit glob behavior | PASS | `*.py` target does not glob-match (probe) |
| Deny precedence | PASS | suite + probe |
| Specificity | PASS | priority resolves same-kind conflicts (suite) |
| Ambiguous ties | PASS | allow tie → ambiguous (deny) (suite) |
| Empty or malformed rules | PASS | empty allowlist → None; malformed rules rejected (suite) |

## 8. Transition matrix

| From | To | Expected | Actual | Approval behavior | Result |
|---|---|---|---|---|---|
| READ_ONLY | READ_ONLY | deny | deny | — | PASS |
| READ_ONLY | WORKSPACE_WRITE | allow | allow | approval required; valid approval allows | PASS |
| READ_ONLY | DELIVERY | allow | allow | approval required; valid approval allows | PASS |
| WORKSPACE_WRITE | READ_ONLY | allow | allow | none required | PASS |
| WORKSPACE_WRITE | WORKSPACE_WRITE | deny | deny | — | PASS |
| WORKSPACE_WRITE | DELIVERY | allow | allow | approval required | PASS |
| DELIVERY | READ_ONLY | allow | allow | none required | PASS |
| DELIVERY | WORKSPACE_WRITE | allow | allow | none required | PASS |
| DELIVERY | DELIVERY | deny | deny | — | PASS |

Wrong-scope transition approval denied with `APPROVAL_SCOPE_MISMATCH` (probe).

## 9. Approval lifecycle and binding

| Contract | Result | Evidence |
|---|---|---|
| Request immutability | PASS | frozen dataclass; test |
| Record immutability | PASS | frozen dataclass; test |
| Valid lifecycle | PASS | PENDING→APPROVED→CONSUMED (suite + probe) |
| Invalid transitions | PASS | duplicate decision/lifecycle misuse raises ApprovalLifecycleError |
| Terminal states | PASS | DENIED/EXPIRED/REVOKED/CONSUMED terminal; consume/revoke of non-APPROVED rejected |
| Expiration | PASS | injected clock; boundary tested |
| Revocation | PASS | prevents later consumption |
| Single consumption | PASS | second consume raises |
| Action binding | PASS | mismatch → APPROVAL_SCOPE_MISMATCH |
| Target binding | PASS | mismatch → APPROVAL_SCOPE_MISMATCH |
| Scope binding | PASS | transition scope mismatch → APPROVAL_SCOPE_MISMATCH |
| Mode binding | PASS | `required_mode` enforced (JUSTIFIED_REFINEMENT) |
| Identity trust boundary | PASS | `approver` is a plain reference; no authentication claims |

## 10. Replay and concurrency

| Check | Result | Evidence |
|---|---|---|
| Concurrent consumers attempted | 8 threads (probe) / 4 threads (suite) | probe + test |
| Successful consumers | exactly 1 | probe |
| Rejected consumers | 7 (probe) / 3 (suite) | probe + test |
| Final approval state | CONSUMED | probe |
| Deterministic denial | yes | repeated runs stable |
| Validation/consumption atomicity | lock covers validate/consume/revoke | manager `threading.Lock`; observable behavior |
| Expiration/revocation race handling | state refreshed under lock before operations | `_refresh` under lock |

## 11. Clock, errors, and side effects

| Check | Result | Evidence |
|---|---|---|
| UTC-aware production clock | PASS | `UtcClock.now()` aware UTC |
| Deterministic fixed clock | PASS | `FixedClock` advance |
| Exact expiration boundary | PASS | `expires_at <= now` expires; boundary tested |
| Stable reason codes | PASS | 17 stable string values |
| Domain error hierarchy | PASS | DomainError + 5 subclasses |
| Expected denials are decisions | PASS | probe |
| Framework import scan | PASS | AST scan; no typer/click/pydantic/pytest/CLI imports in domain |
| Filesystem side effects | PASS | no fs calls; import/use creates nothing |
| Git side effects | PASS | none in domain |
| Network side effects | PASS | no socket/requests/HTTP in domain |
| Model side effects | PASS | no LLM/OpenCode imports |
| Console or telemetry side effects | PASS | no logging/print in domain |

## 12. Test-quality review

- Strengths: exact reason-code assertions; full transition matrix; precedence-conflict tests; adversarial allowlist near-match cases; expiration boundaries; terminal states; replay and concurrent consumption; immutability checks; framework-independence AST scan; Phase 1 suite preserved.
- Missing or weak coverage: none material; all domain lines and branches reach 100% in-process.
- Nondeterminism risks: none — injected clocks and a lock make time/race behavior deterministic.
- Overfitted or implementation-mirroring tests: `test_framework_independence.py` reads source ASTs (acceptable static guarantee); conftest factories are reasonable test helpers, not assertion mirroring.
- Regression protection assessment: strong — Phase 1 tests unchanged and passing; immutability and import-freedom tests guard the key invariants.

## 13. Full validation results

| Check | Result | Gate | Evidence |
|---|---|---|---|
| Python version | 3.11.9 | 3.11+ | `python --version` |
| Dependency integrity | PASS | PASS | `pip check` |
| Tests collected | 184 | — | pytest |
| Tests passed | 184 | ALL | pytest |
| Tests failed | 0 | 0 | pytest |
| Tests skipped | 0 | — | pytest |
| Line coverage | 99% | ≥90% | pytest-cov |
| Branch coverage | ~99.5% | ≥85% | pytest-cov (204 branches, 1 partial) |
| Changed-lines coverage | 100% for all new domain production lines | 100% practical | all domain files 100% line/branch |
| Security-critical uncovered branches | none | NONE | all policy/approval/replay branches covered |

The only uncovered lines are the pre-existing Phase 1 entry-point guards (`__main__.py:6-9`, `cli.py:133`), behaviorally verified via module execution and unrelated to Phase 2.

## 14. Findings

- FINDING-AH02-01 — INFO — Architecture report states "fourteen capabilities across seven categories"; the authoritative design defines six categories. The implementation implements the design's six. Impact: none (report accuracy only). Required remediation: NO_ACTION_REQUIRED (historical report preserved).
- FINDING-AH02-02 — INFO — `tests/unit/domain/conftest.py` added beyond the ten listed test files; pytest support file, no tests. Impact: none. Required remediation: NO_ACTION_REQUIRED.
- FINDING-AH02-03 — INFO — `ApprovalRecord.required_mode` is an additional immutable field beyond design §12, required to enforce the mandated approval-mode-mismatch denial; derived from `ApprovalRequest.required_mode`. Impact: enforcement is strictly strengthened. Required remediation: NO_ACTION_REQUIRED (documented refinement).
- FINDING-AH02-04 — INFO — `FixedClock` lives in the production `domain/clock.py`; the design explicitly names it as the deterministic test clock. Impact: none. Required remediation: NO_ACTION_REQUIRED.

No BLOCKER, HIGH, or MEDIUM findings.

## 15. Repository state

- Current branch: feature/ah-02-domain-contracts
- HEAD: f9f28a1...
- Feature commits: 0
- Staged files: none
- Authorized report change: `reports/AH-02-TST-01.md` (created)
- Other source or test changes caused by QA: none
- Remaining test artifacts: none (temp dir removed; `.pytest_cache/` pre-existing and gitignored, not created by this QA task which used `-p no:cacheprovider` + `PYTHONDONTWRITEBYTECODE`)
- Remote operations: none
- GitHub operations: none

## 16. Commands executed

- `git rev-parse`, `git branch --show-current`, `git status --short`, `git rev-list --count main..HEAD`, `git ls-files --others --exclude-standard`, `git diff --check`, `git diff -- <phase1 files>`
- `git ls-remote --heads`, `gh pr list`
- `python --version`, `python -m pip check`
- `python -m pytest -p no:cacheprovider`, `python -m pytest --cov=agent_harness --cov-branch --cov-report=term-missing` (coverage data and temp artifacts outside the repo)
- Independent behavioral probe (transitions, policy precedence, allowlist adversarial, approvals, concurrency)
- AST import scan (via test suite) and secret-pattern scan
- No credentials, tokens, or sensitive values were output.

## 17. Recommended next action

PROCEED_TO_AH-02-SEC-01

All tests (184/184) and coverage gates pass, all 31 independent behavioral probes pass, and the three reported discrepancies are resolved as compliant or justified against the authoritative design. The domain is framework-independent, default-deny, deterministic, and replay-safe, with no hidden infrastructure side effects. It is ready for the independent security review.

## 18. Non-modification attestation

- Only `reports/AH-02-TST-01.md` was created or modified persistently.
- No production or test file was modified.
- No architecture or implementation evidence was modified.
- No dependency was installed or changed.
- No file was staged.
- No commit was created or amended.
- No branch was created, switched, pushed, or deleted.
- No Pull Request or GitHub resource was modified.
- No container or service was started.
- No runtime LLM request was performed.
- No credential or sensitive value was exposed.
- All temporary testing artifacts were removed.
