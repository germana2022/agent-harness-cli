# Phase 2 — Domain Contracts and Policies Design

## 1. Phase objective

Phase 2 defines the domain contracts, operating-mode model, policy engine, allowlist model, approval lifecycle, transition rules, error taxonomy, package structure, and testing strategy required before any repository, command, model, or external capability is introduced.

Exit gate: mode transitions and approvals are modeled and unit-tested.

Phase 2 introduces domain modeling and enforcement logic only. It does not inspect repositories, execute commands, call models, or perform external actions.

## 2. Scope

Included capabilities:

- Operating-mode model (`READ_ONLY`, `WORKSPACE_WRITE`, `DELIVERY`).
- Action and capability taxonomy.
- Mode-transition state machine with default-deny behavior.
- Policy-engine interface and deterministic evaluation.
- Allowlist model (scaffolding, no filesystem traversal).
- Approval request and approval record models.
- Approval lifecycle (pending, approved, denied, expired, revoked, consumed).
- In-memory approval manager interface and implementation for unit tests.
- Domain error taxonomy.
- Domain clock abstraction for deterministic expiration.
- Domain interfaces (protocols) for later infrastructure.

Excluded capabilities:

- Repository inspection.
- Filesystem traversal and file reading.
- Exact search.
- Command execution.
- Git operations, worktrees, sandbox.
- Model invocation.
- Persistent approval storage.
- GitHub or any external integration.

Deferred capabilities:

- All concrete repository and model infrastructure.
- Persistent storage, authentication providers, trajectory recording.

Dependencies on Phase 1:

- Phase 1 provides the CLI boundary, configuration, exit codes, and the `agent_harness` package layout. Phase 2 domain code will be imported by future application layers, not by the Phase 1 CLI directly unless a new command is added (decision: no new CLI command).

Dependencies introduced for later phases:

- Phase 3 (safe repository inspection), Phase 4 (search and reading), Phase 6 (trajectories), Phase 7 (model provider) will consume the Phase 2 contracts.

## 3. Architectural placement

Dependency direction:

```text
CLI
→ Application
→ Domain

Infrastructure
→ Domain interfaces
```

- Domain: mode model, action taxonomy, policy engine contract, allowlist model, approval models, approval manager contract, clock protocol, domain errors, reason codes. Standard-library only.
- Application: use cases that construct policy requests, call the policy engine, request and consume approvals. Not implemented in Phase 2 beyond interface contracts.
- CLI: Typer commands (Phase 1). No new commands in Phase 2.
- Infrastructure: concrete adapters (in-memory approval store for tests is treated as test infrastructure; persistent stores are deferred).

The domain must not import Typer, Click, Pydantic, OpenCode, DeepSeek, GitHub, Docker, LangGraph, Qdrant, or any concrete provider/persistence implementation.

## 4. Proposed package structure

```text
src/agent_harness/domain/
├── __init__.py
├── modes.py          OperatingMode enum, default mode, capability mapping
├── actions.py        ActionCategory, ActionName, Capability, TargetResource
├── policy.py         PolicyRequest, PolicyDecision, PolicyReasonCode, PolicyEngine (protocol)
├── allowlist.py      AllowlistRule, AllowlistMatch, RuleKind, AllowlistEngine
├── approvals.py      ApprovalRequest, ApprovalRecord, ApprovalState, ApprovalDecision
├── approval_manager.py  ApprovalManager (protocol) and InMemoryApprovalManager
├── clock.py          Clock (protocol), UtcClock
├── transitions.py    ModeTransitionRequest, TransitionDecision, transition table
├── errors.py         DomainError hierarchy
└── __pycache__/      (generated, ignored)
```

File responsibilities:

| File | Responsibility |
|---|---|
| `modes.py` | `OperatingMode` enum, default mode constant, per-mode capability and mutation/external flags. |
| `actions.py` | `ActionCategory` enum, `ActionName` value object, `Capability` enum, `TargetResource` value object. |
| `policy.py` | Immutable `PolicyRequest`, `PolicyDecision`, `PolicyReasonCode`, and the `PolicyEngine` protocol. |
| `allowlist.py` | `AllowlistRule`, `RuleKind` (allow/deny), `AllowlistMatch`, and the `AllowlistEngine` with exact and bounded-pattern matching. |
| `approvals.py` | `ApprovalRequest`, `ApprovalRecord`, `ApprovalState`, `ApprovalDecision` value objects. |
| `approval_manager.py` | `ApprovalManager` protocol and `InMemoryApprovalManager` (single-process, for unit tests). |
| `clock.py` | `Clock` protocol and `UtcClock` implementation using injected UTC timestamps. |
| `transitions.py` | `ModeTransitionRequest`, `TransitionDecision`, and the transition matrix. |
| `errors.py` | `DomainError` hierarchy for exceptional failures only. |
| `__init__.py` | Re-exports the stable public domain surface. |

Tests:

```text
tests/unit/domain/test_modes.py
tests/unit/domain/test_actions.py
tests/unit/domain/test_policy.py
tests/unit/domain/test_allowlist.py
tests/unit/domain/test_approvals.py
tests/unit/domain/test_approval_manager.py
tests/unit/domain/test_transitions.py
tests/unit/domain/test_errors.py
tests/unit/domain/test_clock.py
tests/unit/domain/test_framework_independence.py
```

No integration tests against filesystem, Git, network, or models in Phase 2.

## 5. Operating-mode model

```text
READ_ONLY
WORKSPACE_WRITE
DELIVERY
```

Default mode: `READ_ONLY`.

| Mode | Read | Local write | External action | Approval requirements |
|---|---|---|---|---|
| READ_ONLY | Yes | No | No | None |
| WORKSPACE_WRITE | Yes | Limited and allowlisted | No | Approval required to enter and for each allowlisted local mutation when configured |
| DELIVERY | Yes | Approved | Each external action separately approved | Separate approval for every external action |

Semantics per mode:

- `READ_ONLY`: local mutation impossible, external action impossible. All action categories resolve to deny except pure read categories.
- `WORKSPACE_WRITE`: local mutation possible only for allowlisted local-write categories; external action impossible.
- `DELIVERY`: local mutation allowed under approval; external action allowed only with a separate valid approval for that specific external action. Entering `DELIVERY` grants no blanket external permission.

## 6. Action and capability taxonomy

`Capability` enum (stable identifiers):

```text
REPOSITORY_METADATA_READ
ALLOWED_FILE_READ
EXACT_SEARCH
LOCAL_WORKSPACE_WRITE
COMMAND_EXECUTION
GIT_STATE_MUTATION
LOCAL_COMMIT
EXTERNAL_PUSH
PULL_REQUEST_CREATE_MODIFY
ISSUE_TICKET_MODIFY
COMMENT_PUBLICATION
MIGRATION
DEPLOYMENT
DESTRUCTIVE_DELETE_REVERT
```

`ActionCategory` enum (classification axis):

```text
READ
LOCAL_WRITE
EXECUTION
GIT_MUTATION
EXTERNAL
DESTRUCTIVE
```

Every action is represented as an immutable `ActionName(capability, category, target)` value object. No free-form action strings.

`TargetResource` value object: nonempty normalized identifier plus an optional resource type discriminator; it carries no filesystem path coupling in Phase 2 (a plain `ref` string field).

## 7. Mode-transition state machine

Initial state: `READ_ONLY`.

Transitions:

| From | To | Allowed | Approval required |
|---|---|---|---|
| READ_ONLY | WORKSPACE_WRITE | Yes | Yes |
| READ_ONLY | DELIVERY | Yes (requires prior WORKSPACE_WRITE authorization semantics; direct transition allowed only with separate approval) | Yes |
| WORKSPACE_WRITE | DELIVERY | Yes | Yes |
| WORKSPACE_WRITE | READ_ONLY | Yes | No |
| DELIVERY | WORKSPACE_WRITE | Yes | No |
| DELIVERY | READ_ONLY | Yes | No |
| READ_ONLY | READ_ONLY | No (identity) | — |
| WORKSPACE_WRITE | WORKSPACE_WRITE | No (identity) | — |
| DELIVERY | DELIVERY | No (identity) | — |
| Any → unknown/unregistered mode | No | — | — |

Rules:

- Escalation transitions (toward WORKSPACE_WRITE or DELIVERY) require explicit human approval.
- Return to a more restrictive mode never requires approval.
- Approvals for escalation are single-use and expire; each new escalation requires a fresh approval.
- Transition evidence: `TransitionDecision` records the from/to modes, reason code, approval reference (if any), and UTC timestamp.

Transition decisions are produced by the policy engine through the same default-deny path; an unregistered transition is denied with `UNSUPPORTED_TRANSITION`.

## 8. Policy engine contract

`PolicyEngine` protocol:

```text
decide(request: PolicyRequest) -> PolicyDecision
```

`PolicyRequest` carries:

- current mode
- requested action (ActionName)
- target (TargetResource)
- allowlist result (AllowlistMatch or none)
- approval record (when supplied)
- classification flags (external, destructive)
- safe context map (bounded, typed; no raw environment values)

Evaluation precedence (authoritative order):

```text
1. Hard prohibition (category or capability is always denied)
2. Mode capability (is the category permitted in current mode)
3. Resource allowlist (target matches an allowlist rule)
4. Approval requirement (is approval required and present)
5. Approval validity (scope, target, expiration, consumption, revocation)
6. Final policy decision
```

Every `PolicyDecision` contains:

- `allowed: bool`
- `reason_code: PolicyReasonCode` (stable)
- `message: str` (sanitized, deterministic)
- `approval_required: bool`
- `evidence: tuple[str, ...]` (stable evidence references, no sensitive values)

Ordinary denials are returned as decisions; exceptions are never used for denials.

## 9. Default-deny semantics

| Condition | Result |
|---|---|
| Unknown action | deny (`ACTION_UNKNOWN`) |
| Unknown mode | deny (`MODE_UNKNOWN` / invalid request) |
| Missing target when required | deny (`TARGET_MISSING`) |
| Missing allowlist match | deny (`TARGET_NOT_ALLOWLISTED`) |
| Missing approval when required | deny (`APPROVAL_MISSING`) |
| Expired approval | deny (`APPROVAL_EXPIRED`) |
| Consumed approval | deny (`APPROVAL_CONSUMED`) |
| Approval scope mismatch | deny (`APPROVAL_SCOPE_MISMATCH`) |
| Ambiguous policy configuration | deny (`POLICY_CONFIGURATION_ERROR` as decision for ambiguous runtime match) |
| Unsupported transition | deny (`UNSUPPORTED_TRANSITION`) |

Domain errors vs decisions: conditions that are normal, expected outcomes of a request (missing/expired/consumed approval, non-matching allowlist) are denial decisions. Conditions that indicate the caller constructed an invalid request (unknown mode enum impossible by construction, malformed target) are domain errors.

## 10. Allowlist model

`AllowlistRule`:

- `rule_id: str` (nonempty normalized)
- `kind: RuleKind` (`ALLOW`, `DENY`)
- `capability: Capability`
- `target_pattern: str` (exact match or bounded prefix/suffix pattern with an explicit `match_mode`)
- `match_mode: MatchMode` (`EXACT`, `PREFIX`, `SUFFIX`)
- `priority: int`
- optional `constraint: str | None`

Matching semantics:

- Exact match is the default and safest.
- Prefix/suffix patterns are bounded: a pattern matches only the literal prefix or suffix with an explicit length limit; no glob traversal, no recursive expansion.
- `DENY` rules take precedence over `ALLOW` rules at the same capability; for conflicts within the same kind, the higher `priority` wins; ties resolve to deny.
- Default outcome when no rule matches: deny.
- Malformed rules (empty id, empty pattern, unknown capability) are rejected at construction (domain error) or skipped with a deny result when parsed from untrusted input.
- An `AllowlistMatch` records the matched rule id, kind, and a sanitized evidence string.
- No filesystem access, glob traversal, or command execution is implemented.

## 11. Approval request model

`ApprovalRequest` (immutable):

- `request_id: str`
- `action: ActionName`
- `target: TargetResource`
- `required_mode: OperatingMode`
- `current_mode: OperatingMode`
- `scope: str` (canonical description)
- `requesting_component: str`
- `rationale: str`
- `evidence_refs: tuple[str, ...]`
- `created_at: datetime` (UTC)
- `expires_at: datetime | None` (UTC)
- `is_external: bool`
- `is_destructive: bool`

Approval requests never store secrets or raw sensitive values.

## 12. Approval record model

`ApprovalRecord` (immutable):

- `approval_id: str`
- `request_id: str`
- `decision: ApprovalDecision` (`APPROVED`, `DENIED`)
- `scope: str`
- `action: ActionName`
- `target: TargetResource`
- `approver: str` (actor reference, untrusted for authentication)
- `decided_at: datetime` (UTC)
- `expires_at: datetime | None` (UTC)
- `state: ApprovalState` (PENDING/APPROVED/DENIED/EXPIRED/REVOKED/CONSUMED)
- `consumed_at: datetime | None`
- `revoked_at: datetime | None`
- `reason: str`
- `evidence_ref: str`
- `correlation_id: str | None`

Approval metadata is explicitly distinct from credentials or authorization tokens.

## 13. Approval lifecycle

States:

```text
PENDING → APPROVED → CONSUMED (terminal)
PENDING → DENIED (terminal)
APPROVED → EXPIRED (terminal)
APPROVED → REVOKED (terminal)
```

- `PENDING`: decision not yet recorded.
- `APPROVED`: valid until expiration or consumption.
- `DENIED`: terminal, decided negative.
- `EXPIRED`: `expires_at` passed.
- `REVOKED`: explicitly invalidated by an approver.
- `CONSUMED`: used once for an authorized action.

Rules:

- Terminal states: DENIED, EXPIRED, REVOKED, CONSUMED.
- Default approval-use policy: narrowly scoped, single-use.
- Consumption: the approval is marked `CONSUMED` before or atomically with the authorized action; a consumed approval can never be reused.
- Revocation: only an explicit approver action moves APPROVED → REVOKED.
- Duplicate decision: recording a decision on a non-PENDING request is an error (`APPROVAL_LIFECYCLE_ERROR`).
- Concurrent/repeated use: single-use semantics deny any second use; the in-memory manager serializes via a process lock.
- Scope mismatch: validating an approval against a different action/target denies.
- Clock handling: all comparisons use injected UTC timestamps from the `Clock` protocol; no wall-clock dependence.
- Expiration check: performed at every validation using the injected clock.

## 14. Approval manager contract

`ApprovalManager` protocol:

```text
request(request: ApprovalRequest) -> ApprovalRequest
record_decision(request_id, decision, approver, reason) -> ApprovalRecord
get(approval_id) -> ApprovalRecord
validate(approval_id, action, target, at_time) -> PolicyDecision
consume(approval_id) -> ApprovalRecord
revoke(approval_id) -> ApprovalRecord
```

Phase 2 provides `InMemoryApprovalManager` (single-process, thread-safe via a lock) to satisfy unit tests. Persistent storage, databases, files, network services, and GitHub integration are deferred.

## 15. Identity and trust boundaries

- Phase 2 models identity references only; it does not authenticate humans.
- `approver` is an actor reference string, not verified identity.
- Caller-supplied identity is untrusted unless provided by a future trusted boundary.
- Authentication and external identity providers are deferred.

## 16. Time abstraction

- `Clock` protocol: `now() -> datetime` returning a UTC-aware timestamp.
- `UtcClock`: returns `datetime.now(timezone.utc)`.
- Tests inject a `FixedClock` to control time without sleeping or wall-clock dependence.
- All expiration and lifecycle comparisons use the injected clock.

## 17. Policy-decision reason codes

Stable codes:

```text
ALLOWED
MODE_PROHIBITS_ACTION
ACTION_UNKNOWN
TARGET_MISSING
TARGET_NOT_ALLOWLISTED
HARD_PROHIBITION
APPROVAL_REQUIRED
APPROVAL_MISSING
APPROVAL_PENDING
APPROVAL_DENIED
APPROVAL_EXPIRED
APPROVAL_REVOKED
APPROVAL_CONSUMED
APPROVAL_SCOPE_MISMATCH
UNSUPPORTED_TRANSITION
INVALID_POLICY_REQUEST
POLICY_CONFIGURATION_ERROR
```

Human-readable messages are sanitized and deterministic (no raw inputs, no environment values).

## 18. Domain error taxonomy

```text
DomainError
├── InvalidDomainValue       (invalid model construction)
├── InvalidTransition        (state-machine misuse)
├── ApprovalLifecycleError   (approval lifecycle misuse)
├── PolicyConfigurationError (policy configuration failure)
└── InternalDomainError      (unexpected internal domain failure)
```

- Ordinary policy denials are returned as `PolicyDecision(allowed=False, ...)`, never raised.
- `InternalDomainError` wraps unexpected conditions only.
- Phase 1 CLI exit codes are not changed in this architecture task; future application layers will map `ConfigurationError`/`DomainError` to the existing exit-code contract (`3` configuration, `10` internal) without altering Phase 1 codes.

## 19. Immutability and validation rules

- All domain value objects are immutable (frozen dataclasses or equivalent).
- Identifiers (`request_id`, `approval_id`, `rule_id`, scope, target ref) must be nonempty and normalized (strip, no control characters).
- `TargetResource` uses a plain normalized `ref` string; no filesystem coupling.
- Timestamps are UTC-aware `datetime`; naive datetimes are rejected at construction.
- Enum exhaustiveness: policy and transition logic uses explicit handling with a final deny/error fallback so new enums fail safe.
- Arbitrary dictionaries are avoided; context is a bounded typed mapping.
- Sensitive strings are excluded from messages and `__repr__` by not storing them and by using sanitized rendering.

## 20. Application integration

Future application use cases will:

1. Construct a `PolicyRequest`.
2. Call `PolicyEngine.decide`.
3. If `approval_required` and not present, create an `ApprovalRequest` and surface it for human decision.
4. On `APPROVED`, `validate` the approval against the exact action and target.
5. `consume` the approval before or atomically with the authorized action.
6. Record the decision evidence (audit-ready record; trajectory recorder is Phase 6).
7. Return a structured result to the CLI.

No actual repository, command, Git, GitHub, or model action is implemented in Phase 2.

## 21. CLI integration boundary

- No new public CLI command in Phase 2.
- The existing Phase 1 CLI (`version`, `health`, `config-check`) remains unchanged and stable.
- No fake approval UI that appears to authenticate or authorize real external actions is designed.

## 22. Security analysis

| Threat | Mitigation | Deferred control |
|---|---|---|
| Default-deny | Unknown/ambiguous inputs deny | — |
| Privilege escalation | Escalation transitions require fresh single-use approval | — |
| Approval replay | Single-use, consumed approval denied on reuse | — |
| Approval scope confusion | Strict action+target+scope match on every validation | — |
| Time-of-check/time-of-use | Approval validated and consumed atomically in the manager | Worktree/sandbox enforcement (later phases) |
| Identity spoofing | `approver` treated as untrusted reference | Real authentication (deferred) |
| Target ambiguity | Normalized `TargetResource`; exact/bounded patterns | Filesystem-relative targeting (Phase 3+) |
| Unknown-action bypass | Enum taxonomy; unknown → deny | — |
| Unsafe string matching | Exact/bounded prefix/suffix; no globs or substring matching | — |
| Error-message disclosure | Sanitized messages; no raw values | — |
| Repository prompt injection | No repository content read in Phase 2 | Phase 3+ reading with injection policy |
| External-action confusion | Each external action requires separate approval | GitHub adapter (Phase 16) |
| Destructive-action handling | `DESTRUCTIVE` category always requires separate approval and higher scrutiny | Confirmation gates (later) |

## 23. Determinism and audit evidence

Evidence produced (audit-ready, not the Phase 6 trajectory recorder):

- Mode transition: `TransitionDecision` (from/to, reason, approval ref, timestamp).
- Policy decision: `PolicyDecision` (allowed, reason code, approval info, evidence tuple).
- Allowlist match: `AllowlistMatch` (rule id, kind, evidence).
- Approval decision: `ApprovalRecord` (decision, approver, reason, timestamp).
- Approval consumption: `consumed_at` recorded on the record.
- Approval revocation: `revoked_at` recorded on the record.

All timestamps are injected UTC; all outputs are deterministic.

## 24. Unit-testing strategy

Test categories for `AH-02-IMP-01`:

- Default mode is `READ_ONLY`.
- Every allowed transition.
- Every denied transition.
- Transition approval requirements (escalations require approval; returns do not).
- Capability matrix per mode.
- Unknown action denial.
- Missing target denial.
- Allowlist exact match.
- Allowlist non-match.
- Deny-rule precedence.
- Conflicting-rule behavior (ties deny).
- Approval lifecycle (pending → approved → consumed).
- Approval expiration (injected clock).
- Approval revocation.
- Approval consumption.
- Replay prevention (second use denied).
- Scope mismatch.
- Target mismatch.
- Deterministic reason codes.
- Sanitized messages (no raw values).
- Domain immutability (attempted mutation fails).
- Domain-framework independence (imports scan: no Typer/Click/Pydantic/providers in domain).
- No filesystem, Git, network, or model calls (no such imports; no side-effect calls).

Coverage gates:

```text
Line coverage: >= 90%
Branch coverage: >= 85%
Changed-lines coverage: 100% where practical
```

## 25. Implementation file plan

Domain production files (create):

```text
src/agent_harness/domain/__init__.py
src/agent_harness/domain/modes.py
src/agent_harness/domain/actions.py
src/agent_harness/domain/policy.py
src/agent_harness/domain/allowlist.py
src/agent_harness/domain/approvals.py
src/agent_harness/domain/approval_manager.py
src/agent_harness/domain/clock.py
src/agent_harness/domain/transitions.py
src/agent_harness/domain/errors.py
```

Application-facing interfaces: the `PolicyEngine`, `ApprovalManager`, and `Clock` protocols (in the domain package; consumed by future application layers).

Unit tests (create):

```text
tests/unit/domain/test_modes.py
tests/unit/domain/test_actions.py
tests/unit/domain/test_policy.py
tests/unit/domain/test_allowlist.py
tests/unit/domain/test_approvals.py
tests/unit/domain/test_approval_manager.py
tests/unit/domain/test_transitions.py
tests/unit/domain/test_errors.py
tests/unit/domain/test_clock.py
tests/unit/domain/test_framework_independence.py
```

Integration tests: none required for Phase 2.

Documentation updates (create):

```text
docs/PHASE_02_DOMAIN_CONTRACTS_AND_POLICIES_DESIGN.md
```

Reports (create):

```text
reports/AH-02-ARC-01.md
reports/AH-02-IMP-01.md
reports/AH-02-TST-01.md
reports/AH-02-OPR-01.md
reports/AH-02-GIT-01.md
```

No existing file is modified.

## 26. Dependency decision

- No new runtime dependency.
- Python standard library only for the domain (`dataclasses`, `enum`, `datetime`, `typing`/`Protocol`).
- If any future phase requires a dependency, it must be justified separately and installed only in the implementation phase that needs it.

## 27. Definition of Done mapping

| DoD check | Phase 2 status |
|---|---|
| Scope compliance | applicable — design follows the approved roadmap |
| Design review | applicable — this design is the review record |
| Implementation | applicable — AH-02-IMP-01 |
| Unit tests | applicable — domain unit tests |
| Integration tests (when applicable) | N/A — no cross-component integration in Phase 2 |
| Static validation | applicable — ruff/format if configured; import-freedom scan |
| Build | applicable — package imports cleanly |
| Coverage | applicable — line ≥ 90% |
| Changed-lines coverage | applicable — ≥ 100% where practical |
| Security considerations | applicable — default-deny, replay prevention, sanitization |
| Evidence | applicable — decisions carry reason codes and evidence |
| Documentation | applicable — design doc updated |
| Reproducibility | applicable — injected clock, deterministic decisions |
| No invented files or symbols | applicable — every referenced symbol is planned |
| Human approval | applicable — approvals modeled and tested |
| Git status | applicable — clean, only intended files |
| Required reports | applicable — implementation and QA reports |

## 28. Acceptance criteria for implementation

`AH-02-IMP-01` is accepted only when:

- All 10 domain production files exist with the planned modules.
- Domain imports only the standard library.
- Default mode is `READ_ONLY`.
- The transition matrix is complete and default-deny.
- Escalation transitions require approval; returns do not.
- Policy evaluation follows the documented precedence.
- Unknown action/mode/target and missing approval deny.
- Allowlists use exact/bounded matching; deny rules take precedence.
- Approvals are single-use, expire, can be revoked, and deny replay.
- Scope and target mismatches deny.
- All reason codes are stable and deterministic.
- All messages are sanitized.
- All value objects are immutable.
- No filesystem, Git, network, or model calls occur.
- Unit-test coverage: line ≥ 90%, branch ≥ 85%.
- No new dependency is added.
- Existing Phase 1 tests continue to pass unchanged.
- No file is staged or committed.

## 29. Deferred functionality

Explicitly deferred:

- Repository inspection.
- Filesystem traversal.
- Exact search.
- File reading.
- Repository map.
- Symbol analysis.
- Git history.
- Command execution.
- Worktree creation.
- Sandbox execution.
- Model invocation.
- OpenCode integration.
- DeepSeek calls.
- Ticket workflows.
- Persistent approval storage.
- Authentication providers.
- GitHub operations.
- Push, merge, deployment, or migration.
- Trajectory recording.
- Semantic retrieval.

## 30. Open questions and decisions

| Decision required | Recommended choice | Security/implementation impact | Blocks IMP-01 |
|---|---|---|---|
| Domain object style | frozen dataclasses + enums + `Protocol` | immutability and framework independence | No |
| Target representation | normalized `ref` string, no filesystem coupling | avoids path confusion | No |
| Escalation approval lifetime | 15 minutes default, injected clock | limits stale approvals | No |
| Direct READ_ONLY→DELIVERY | allowed only with separate approval | explicit escalation | No |
| Reason-code granularity | one enum with 17 stable codes | deterministic output | No |
| Manager concurrency | in-memory + lock, single-process | safe unit tests | No |
| Allowlist pattern set | exact, prefix, suffix only | no unsafe matching | No |
| New CLI command | none | Phase 1 CLI unchanged | No |
| New dependency | none | stdlib only | No |

No material implementation ambiguity remains for `AH-02-IMP-01`.
