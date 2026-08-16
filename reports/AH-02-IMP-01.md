# AH-02-IMP-01 — Domain Contracts and Policies Implementation Report

## Status

COMPLETED

## Timestamp

2026-08-14

## Git root and branch

- Repository: `D:/agente-harness`
- Branch: `feature/ah-02-domain-contracts`
- Base commit: `f9f28a1ef77e06ec3607b1bf4b7b30917aaed257`

## Architecture source

- `docs/PHASE_02_DOMAIN_CONTRACTS_AND_POLICIES_DESIGN.md` (authoritative)
- `reports/AH-02-ARC-01.md`

## Files created

- `src/agent_harness/domain/__init__.py`
- `src/agent_harness/domain/modes.py`
- `src/agent_harness/domain/actions.py`
- `src/agent_harness/domain/policy.py`
- `src/agent_harness/domain/allowlist.py`
- `src/agent_harness/domain/approvals.py`
- `src/agent_harness/domain/approval_manager.py`
- `src/agent_harness/domain/clock.py`
- `src/agent_harness/domain/transitions.py`
- `src/agent_harness/domain/errors.py`
- `tests/unit/domain/conftest.py` (pytest support file, no tests)
- `tests/unit/domain/test_modes.py`
- `tests/unit/domain/test_actions.py`
- `tests/unit/domain/test_policy.py`
- `tests/unit/domain/test_allowlist.py`
- `tests/unit/domain/test_approvals.py`
- `tests/unit/domain/test_approval_manager.py`
- `tests/unit/domain/test_transitions.py`
- `tests/unit/domain/test_errors.py`
- `tests/unit/domain/test_clock.py`
- `tests/unit/domain/test_framework_independence.py`
- `reports/AH-02-IMP-01.md`

## Existing files modified

- None.

## Unexpected files

- None (only design-authorized domain/test files plus the report and `conftest.py`).

## Domain models implemented

- `OperatingMode` (`READ_ONLY`, `WORKSPACE_WRITE`, `DELIVERY`) with `DEFAULT_MODE = READ_ONLY`.
- `Capability` (14 members) mapped to `ActionCategory` (6 members) via `CAPABILITY_CATEGORY`.
- `ActionName` and `TargetResource` immutable value objects; category consistency enforced.
- `AllowlistRule`, `AllowlistMatch`, `RuleKind`, `MatchMode`, `AllowlistEngine`.
- `ApprovalRequest`, `ApprovalRecord`, `ApprovalDecision`, `ApprovalState`, `TERMINAL_STATES`.
- `ApprovalManager` protocol and `InMemoryApprovalManager`.
- `Clock` protocol, `UtcClock`, `FixedClock`.
- `ModeTransitionRequest`, `TransitionDecision`, `evaluate_transition`, `transition_scope`.
- `DomainError` hierarchy and identifier/UTC validators.

## Operating modes

Implemented exactly `READ_ONLY`, `WORKSPACE_WRITE`, `DELIVERY`; default `READ_ONLY`. Mode capability mapping enforces: reads allowed in all modes; local mutations only in `WORKSPACE_WRITE`/`DELIVERY`; external/destructive actions only in `DELIVERY`.

## Transition matrix implementation

All six registered transitions implemented; escalations require approval; returns do not; identity and unregistered transitions deny with `UNSUPPORTED_TRANSITION`.

## Capability taxonomy

14 capabilities across 6 categories; category is derived from capability and enforced at construction.

## Policy evaluation order

Implemented exactly: hard prohibition → mode capability → allowlist → approval requirement → approval validity → final decision.

## Default-deny behavior

Unknown action, missing target, missing allowlist match, explicit deny rule, ambiguous allowlist, prohibited mode, hard prohibition, missing/pending/denied/expired/revoked/consumed/mismatched approval, and unsupported transitions all deny with stable reason codes.

## Allowlist semantics

Exact plus bounded prefix/suffix matching; deny rules win; priority resolves same-kind conflicts; allow ties are ambiguous (deny); default deny; malformed rules rejected at construction with `PolicyConfigurationError`.

## Approval request and record models

Implemented the exact design fields; the record additionally carries `required_mode` (derived from the request) to support the mandated approval-mode-mismatch denial. Records contain metadata only — no credentials or sensitive values.

## Approval lifecycle

`PENDING → APPROVED → CONSUMED`; `PENDING → DENIED`; `APPROVED → EXPIRED/REVOKED`; terminal states enforced; single-use consumption; expiration via injected UTC clock.

## Approval manager behavior

Protocol operations (request, record_decision, get, validate, consume, revoke) plus lazy expiration detection; locked single-process implementation; deterministic.

## Replay-prevention mechanism

Single-use approvals: a consumed approval is permanently `CONSUMED`; repeated or concurrent consumption is denied (thread-safe via `threading.Lock`).

## Clock behavior

`Clock` protocol; `UtcClock` (real UTC); `FixedClock` (deterministic, advanceable) for tests; naive timestamps rejected.

## Reason codes

All 17 `PolicyReasonCode` values implemented with stable sanitized messages.

## Error taxonomy

`DomainError` with `InvalidDomainValue`, `InvalidTransition`, `ApprovalLifecycleError`, `PolicyConfigurationError`, `InternalDomainError`. Ordinary denials are decisions, not exceptions.

## Dependency impact

No new runtime dependency; domain imports only the Python standard library and other domain modules.

## CLI impact

No new CLI command; Phase 1 CLI and its tests unchanged.

## Tests and coverage

- Existing Phase 1 tests: 57 passed (unchanged).
- New Phase 2 tests: 127 passed (126 domain tests + framework-independence assertions).
- Total collected: 184; passed: 184; failed: 0.
- Line coverage: 99% (715 statements, 4 missed — only the pre-existing entry-point guards `__main__.py` and `cli.py:133`).
- Branch coverage: ~99.5% (204 branches, 1 partial).
- Changed-lines coverage: all new Phase 2 domain files at 100% line/branch coverage in-process; the only uncovered lines are the Phase 1 entry-only guards (pre-existing, behaviorally verified).
- Coverage gates: line ≥ 90% PASS; branch ≥ 85% PASS.

## Security validation

| Check | Result |
|---|---|
| Default deny | verified (unknown/missing/ambiguous all deny) |
| Hard-prohibition precedence | verified (tested with configured sets) |
| Deny-rule precedence | verified |
| Mode escalation approval | verified (all escalations require valid approval) |
| External-action approval | verified (every external action requires separate approval) |
| Approval expiration | verified (injected clock) |
| Approval revocation | verified |
| Replay prevention | verified (single-use, concurrent-safe) |
| Scope and target binding | verified (action/target/mode match enforced) |
| Identity trust boundary | `approver` is an untrusted reference, not authenticated identity |
| Sensitive-data handling | no secret fields; identifiers normalized; messages sanitized |
| Framework independence | AST import scan passes; no filesystem/Git/network/model calls |

## Git status

- Current branch: `feature/ah-02-domain-contracts`
- HEAD: `f9f28a1ef77e06ec3607b1bf4b7b30917aaed257`
- Feature commits: 0
- Staged files: none
- Working tree: clean except authorized untracked files
- Remote operations: none

## Warnings

- `conftest.py` added as a pytest support file (not a test module) alongside the ten planned test files.
- `ApprovalRecord` carries one justified refinement (`required_mode`) to enforce the mandated approval-mode-mismatch denial.

## Blockers

- None.

## Recommended next action

PROCEED_TO_AH-02-TST-01

The domain package is complete, framework-independent, default-deny, and fully unit-tested (184/184 passing, coverage gates far exceeded). An independent tester should validate the implementation before publication.

## Non-modification attestation

- The two Phase 2 architecture files were not modified.
- Only design-authorized domain and test files were created (plus `conftest.py` and the report).
- No Phase 1 source or test was modified.
- No dependency file was modified.
- No dependency was installed.
- No CLI command was added.
- No file was staged.
- No commit was created.
- No push or remote resource was created or modified.
- No credential or secret was exposed.
