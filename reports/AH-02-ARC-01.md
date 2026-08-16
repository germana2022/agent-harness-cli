# AH-02-ARC-01 — Domain Contracts and Policies Design Report

## Status

COMPLETED

## Timestamp

2026-08-14

## Git root and branch

- Repository: `D:/agente-harness`
- Branch: `feature/ah-02-domain-contracts`
- Base commit: `f9f28a1ef77e06ec3607b1bf4b7b30917aaed257`

## Files created

- `docs/PHASE_02_DOMAIN_CONTRACTS_AND_POLICIES_DESIGN.md`
- `reports/AH-02-ARC-01.md`

## Existing files modified

- None.

## Scope compliance

- Design follows the approved Phase 2 roadmap entry (domain contracts, operating-mode model, policy engine, approval manager; mode transitions and approvals modeled and unit-tested).
- No repository inspection, command execution, model calls, or external actions included.
- No production code, tests, dependencies, or GitHub resources created.

## Key architecture decisions

- Package structure: `src/agent_harness/domain/` with 10 modules (modes, actions, policy, allowlist, approvals, approval_manager, clock, transitions, errors, `__init__`).
- Domain object style: immutable frozen dataclasses, enums, and `Protocol` interfaces; standard library only.
- Immutability: all value objects immutable.
- Operating modes: `READ_ONLY`, `WORKSPACE_WRITE`, `DELIVERY`; default `READ_ONLY`.
- Capability taxonomy: 14 stable `Capability` values across 7 `ActionCategory` classes; `ActionName` value objects, no free-form strings.
- Transition model: complete matrix; escalations require approval; returns to restrictive modes do not.
- Policy evaluation order: hard prohibition → mode capability → allowlist → approval requirement → approval validity → decision.
- Default-deny: unknown action/mode/target, missing/expired/consumed/mismatched approval all deny.
- Allowlist semantics: exact plus bounded prefix/suffix; deny rules take precedence; no globs or substring matching.
- Approval scope: narrowly scoped, single-use.
- Approval lifecycle: PENDING → APPROVED → CONSUMED; DENIED/EXPIRED/REVOKED terminal.
- Replay prevention: single-use consumption recorded before/atomically with the action.
- Approval manager: protocol + `InMemoryApprovalManager` (locked, single-process) for tests.
- Clock abstraction: `Clock` protocol with injected UTC timestamps; `UtcClock` and test `FixedClock`.
- Reason codes: 17 stable `PolicyReasonCode` values.
- Error taxonomy: `DomainError` hierarchy; ordinary denials are decisions, not exceptions.
- CLI impact: no new Phase 2 CLI command; Phase 1 CLI unchanged.
- Dependency decision: no new runtime dependency.
- Implementation file plan: 10 domain files + 10 unit test files; no integration tests required.

## Operating-mode matrix

| Mode | Read | Local write | External action |
|---|---|---|---|
| READ_ONLY | Yes | No | No |
| WORKSPACE_WRITE | Yes | Limited, allowlisted | No |
| DELIVERY | Yes | Approved | Each external action separately approved |

## Policy evaluation order

Hard prohibition → mode capability → resource allowlist → approval requirement → approval validity → final decision.

## Approval lifecycle

PENDING → APPROVED → CONSUMED (terminal); PENDING → DENIED (terminal); APPROVED → EXPIRED (terminal); APPROVED → REVOKED (terminal).

## Dependency decision

No new runtime dependency. Domain uses Python standard library only.

## Validation performed

- Preconditions verified: `main` at `f9f28a1`, local == origin == remote, clean tree, no staged/untracked files, feature branch absent locally and remotely, no PR for the branch.
- Branch `feature/ah-02-domain-contracts` created from `f9f28a1`; HEAD unchanged; no commit created.
- All 30 required design sections present.
- All 22 required architecture decisions answered.
- Mode names and default verified in the design.
- Default-deny and external-approval separation documented.
- Domain framework independence specified (stdlib-only).
- No secret or credential present.
- Git diff contains only the two authorized files.

## Warnings

- None.

## Blockers

- None.

## Git status

- Current branch: `feature/ah-02-domain-contracts`
- HEAD: `f9f28a1ef77e06ec3607b1bf4b7b30917aaed257`
- Feature commits: 0
- Staged files: none
- Working tree: clean except the two authorized untracked files
- Remote operations: none

## Recommended next action

PROCEED_TO_AH-02-IMP-01

The design is complete, unambiguous, and framework-independent; all mode, policy, approval, and transition semantics are specified. The next step is implementing the domain package and its unit tests per the design and file plan.

## Non-modification attestation

- Only the two authorized documentation files were created.
- No existing file was modified.
- No production code or test was created.
- No dependency was added, removed, or installed.
- No file was staged.
- No commit was created.
- No push or remote branch was created.
- No Pull Request or GitHub resource was modified.
- No credential or secret was exposed.
