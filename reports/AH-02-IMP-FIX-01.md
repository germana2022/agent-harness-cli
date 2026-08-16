# AH-02-IMP-FIX-01 — Approval Boundary Security Fix Report

## 1. Result

- Status: COMPLETED
- Timestamp: 2026-08-14
- Repository: germana2022/agent-harness-cli
- Git root: D:/agente-harness
- Branch: feature/ah-02-domain-contracts
- Base commit: f9f28a1ef77e06ec3607b1bf4b7b30917aaed257
- Execution mode: WRITE_CONTROLLED_LOCAL

## 2. Preconditions

| Check | Result | Evidence |
|---|---|---|
| Git root | D:/agente-harness | `git rev-parse` |
| Current branch | feature/ah-02-domain-contracts | `git branch --show-current` |
| HEAD | f9f28a1... | `git rev-parse HEAD` |
| Feature commits | 0 | `git rev-list --count main..HEAD` |
| Staged files | none | `git diff --cached` |
| Authorized existing changes | Phase 2 files only | `git status` |
| Unexpected changes | none | — |
| QA decision | PASS (TST-01) | report |
| Security decision | SECURITY_FAIL (SEC-01) | report |
| MEDIUM findings reproduced | YES | probe: forged record → ALLOWED; transition approval reused as action approval → ALLOWED |

## 3. Root-cause analysis

### FINDING-AH02-SEC-01 — Scope confusion

- Root cause: `evaluate_approval_record` compared only action and target; `scope` was validated only on the transition path (`evaluate_transition_approval`). A transition approval (scope `mode_transition:...`) with coinciding action/target was accepted by the engine's action path.
- Affected path: `policy.py` approval validity step and `approval_manager.py` validation.
- Why existing tests missed it: tests exercised the action path with records whose scope matched the default; no cross-purpose (transition-scope vs action-scope) test existed.

### FINDING-AH02-SEC-02 — Forged approval

- Root cause: `PolicyRequest.approval` accepted a raw, caller-constructed `ApprovalRecord`; the engine validated the record's fields but never verified it was issued by the manager.
- Affected path: `DefaultPolicyEngine.decide` step 5 and `evaluate_transition`.
- Why existing tests missed it: all tests used manager-issued records; no manager-bypass or forgery test existed.

### LOW findings

- Timestamp-order root cause: `ApprovalRecord.__post_init__` did not compare `expires_at` against `decided_at`.
- UTC-validation root cause: `validate_utc` accepted any aware timestamp rather than requiring a zero UTC offset.

## 4. Files changed

### Modified

- `src/agent_harness/domain/errors.py` (strict UTC)
- `src/agent_harness/domain/approvals.py` (expiry ordering)
- `src/agent_harness/domain/policy.py` (approval id + `ApprovalAuthority`, `action_scope`, internal evaluators)
- `src/agent_harness/domain/approval_manager.py` (authoritative scoped authorization)
- `src/agent_harness/domain/transitions.py` (authority-based escalation)
- `src/agent_harness/domain/__init__.py` (exports)
- `tests/unit/domain/test_policy.py`
- `tests/unit/domain/test_approval_manager.py`
- `tests/unit/domain/test_transitions.py`
- `tests/unit/domain/test_approvals.py`
- `tests/unit/domain/test_errors.py`

### Created

- `reports/AH-02-IMP-FIX-01.md`

### Unexpected

- None.

## 5. Security correction

| Requirement | Implementation | Evidence |
|---|---|---|
| Authoritative approval lookup | `InMemoryApprovalManager` resolves approval identifiers against stored records under lock; the engine injects it via `ApprovalAuthority` | probe |
| Raw-record distrust | `PolicyRequest.approval` is an identifier; raw `ApprovalRecord` values are rejected with `ValueError` | probe |
| Canonical action scope | `action_scope(action)` = `action:<capability>` derived by the engine/authority | tests |
| Canonical transition scope | `transition_scope(from,to)` = `mode_transition:<from>:<to>` (unchanged) | tests |
| Scope binding | `authorize_action` and `authorize_transition` compare the record's stored scope against the canonical scope | tests + probe |
| Action binding | record.action must equal the requested action | tests |
| Target binding | record.target must equal the requested target | tests |
| Mode binding | record.required_mode must equal the requested mode | tests |
| Atomic validation/consumption | `consume_action`/`consume_transition` validate and consume under one lock; scope mismatch does not consume | tests |
| Safe public API | removed public `evaluate_approval_record`/`evaluate_transition_approval`; final authorization is manager-backed; raw records are not authoritative | exports + tests |
| Timestamp ordering | `ApprovalRecord` rejects `expires_at < decided_at` | tests |
| Strict UTC validation | `validate_utc` requires a zero UTC offset | tests |

## 6. Forgery regression

| Scenario | Expected | Actual | Result |
|---|---|---|---|
| Directly constructed approved record | DENY | rejected by API (`ValueError`); id absent → `APPROVAL_MISSING` | PASS |
| Unregistered approval identifier | DENY | `APPROVAL_MISSING` | PASS |
| Stale approved copy after consumption | DENY | `APPROVAL_CONSUMED` | PASS |
| Stale approved copy after revocation | DENY | `APPROVAL_REVOKED` | PASS |
| Stale approved copy after expiration | DENY | `APPROVAL_EXPIRED` | PASS |
| Same-ID altered record | DENY | manager reads stored record only | PASS |
| Manager-bypass attempt | DENY or unavailable | `evaluate_approval_record` is internal; engine requires authority | PASS |
| Valid authoritative approval | ALLOW | `ALLOWED` | PASS |

## 7. Scope-binding regression

| Scenario | Expected | Actual | Result |
|---|---|---|---|
| Transition approval used for action | DENY | `APPROVAL_SCOPE_MISMATCH` | PASS |
| Action approval used for transition | DENY | `APPROVAL_SCOPE_MISMATCH` | PASS |
| Wrong action scope | DENY | `APPROVAL_SCOPE_MISMATCH` | PASS |
| Wrong transition pair | DENY | `APPROVAL_SCOPE_MISMATCH` | PASS |
| Wrong target | DENY | `APPROVAL_SCOPE_MISMATCH` | PASS |
| Wrong mode | DENY | `APPROVAL_SCOPE_MISMATCH` | PASS |
| Correct authoritative bindings | ALLOW | `ALLOWED` | PASS |

## 8. Lifecycle, time, and concurrency

| Check | Result | Evidence |
|---|---|---|
| Expiry before decision rejected | PASS | `InvalidDomainValue` |
| Exact expiration denied | PASS | `expires_at <= at_time` |
| Naive datetime rejected | PASS | `InvalidDomainValue` |
| Non-zero UTC offset rejected | PASS | `InvalidDomainValue` |
| Zero UTC offset accepted | PASS | valid records |
| Concurrent single-use | PASS | 8-thread `consume_action`: exactly one success |
| Forged concurrent consumer | PASS | absent/consumed ids deny |
| Scope mismatch does not authorize | PASS | `consume_action` scope mismatch does not consume |
| Revocation race | PASS | revoked records deny |
| Expiration race | PASS | expired records deny |

## 9. Public API review

- Final authorization entry point: `InMemoryApprovalManager.authorize_action` / `authorize_transition` (non-consuming) and `consume_action` / `consume_transition` (atomic consuming); the engine resolves through the injected `ApprovalAuthority`.
- Authoritative validator dependency: `DefaultPolicyEngine(approval_authority=...)`; without an authority approval-required actions fail closed with `APPROVAL_MISSING`.
- Removed or narrowed insecure API: public `evaluate_approval_record` and `evaluate_transition_approval` removed from exports; `PolicyRequest.approval` no longer accepts a record; manager `validate` replaced by scoped `authorize_action`/`authorize_transition`.
- Raw record construction impact: `ApprovalRecord` remains constructible as immutable domain data, but construction alone grants nothing (all authorization resolves through the manager by identifier).
- Export changes: added `ApprovalAuthority`, `action_scope`; removed the two raw-record evaluators.
- Compatibility impact: phase-internal API changed (documented as a justified security evolution of the design protocol); CLI and dependency surface unchanged.

## 10. Validation results

| Check | Result | Gate | Evidence |
|---|---|---|---|
| Python version | 3.11.9 | 3.11+ | `python --version` |
| Dependency integrity | clean | PASS | `pip check` |
| Focused security tests | 143 domain tests pass | PASS | pytest |
| Tests collected | 202 | — | pytest |
| Tests passed | 202 | ALL | pytest |
| Tests failed | 0 | 0 | pytest |
| Tests skipped | 0 | — | pytest |
| Line coverage | 99% | ≥90% | pytest-cov |
| Branch coverage | ~99.5% | ≥85% | pytest-cov |
| Fix changed-lines coverage | 100% (all domain files 100% line/branch) | 100% practical | coverage |
| Security-critical uncovered branches | none | NONE | coverage |
| Framework import scan | CLEAN | CLEAN | AST scan |
| Dangerous-operation scan | CLEAN | CLEAN | pattern scan |
| Secret scan | CLEAN | CLEAN | pattern scan |
| Diff check | CLEAN | CLEAN | `git diff --check` |

## 11. Findings closure

| Finding | Status | Evidence |
|---|---|---|
| FINDING-AH02-SEC-01 | FIXED | scope enforced on every final authorization path; transition/action cross-use denied |
| FINDING-AH02-SEC-02 | FIXED | approvals resolve by identifier through the manager; raw records not authoritative |
| FINDING-AH02-SEC-03 | FIXED | `expires_at < decided_at` rejected |
| FINDING-AH02-SEC-04 | FIXED | `validate_utc` requires UTC offset zero |

## 12. Warnings

- The manager protocol evolved: `validate(approval_id, action, target, at_time)` was replaced by scoped `authorize_action`/`authorize_transition` and atomic `consume_action`/`consume_transition`; the raw `consume(approval_id)` lifecycle primitive is retained and documented as not an authorization gate.

## 13. Blockers

- None.

## 14. Git state

- Current branch: feature/ah-02-domain-contracts
- HEAD: f9f28a1...
- Feature commits: 0
- Staged files: none
- Authorized modified files: the seven production/test files listed in §4
- Authorized untracked files: Phase 2 design, reports, domain, tests
- Unexpected files: none
- Remote operations: none
- GitHub operations: none

## 15. Commands executed

- Git/gh read-only checks; `python --version`, `python -m pip check`
- `python -m pytest -p no:cacheprovider`, `python -m pytest --cov=agent_harness --cov-branch --cov-report=term-missing` (coverage data outside the repo)
- Security fix-verification probe (forgery, scope, stale-copy, transition/action cross-use)
- Static scans: dangerous-import, secret, pyproject/CLI diff
- No credentials, tokens, or raw sensitive canaries were output.

## 16. Recommended next action

PROCEED_TO_AH-02-TST-FIX-01

Both MEDIUM findings are demonstrably closed: approvals now resolve authoritatively through the manager by identifier, canonical action and transition scopes are enforced on every final authorization path, and forged or unregistered approvals cannot authorize. All 202 tests and coverage gates pass with the domain at 100% coverage. An independent tester should re-validate the fix before the phase proceeds.

## 17. Non-modification attestation

- Only authorized Phase 2 production and test files were modified.
- Only `reports/AH-02-IMP-FIX-01.md` was created as new evidence.
- Earlier architecture, implementation, QA, and security reports were not modified.
- Phase 1 source and tests were not modified.
- No dependency was added, removed, installed, or updated.
- No file was staged.
- No commit was created or amended.
- No branch was created, switched, pushed, or deleted.
- No Pull Request or GitHub resource was modified.
- No container or service was started.
- No infrastructure or runtime-model integration was introduced.
- No credential, secret, or raw sensitive canary was exposed.
- All temporary validation artifacts were removed.
