# AH-02-SEC-01 — Domain Policies Independent Security Review

## 1. Security decision

- Decision: SECURITY_FAIL
- Timestamp: 2026-08-14
- Repository: germana2022/agent-harness-cli
- Git root: D:/agente-harness
- Branch: feature/ah-02-domain-contracts
- Base commit: f9f28a1ef77e06ec3607b1bf4b7b30917aaed257
- Execution mode: WRITE_CONTROLLED_REPORT_ONLY

## 2. Preconditions

| Check | Result | Evidence |
|---|---|---|
| Git root | D:/agente-harness | `git rev-parse` |
| Current branch | feature/ah-02-domain-contracts | `git branch --show-current` |
| HEAD | f9f28a1... | `git rev-parse HEAD` |
| Base identity | main == origin/main == f9f28a1 | `git rev-parse main/origin/main` |
| Feature commits | 0 | `git rev-list --count main..HEAD` |
| Staged files | none | `git diff --cached` |
| Authorized changes | Phase 2 files only | `git status` |
| Unexpected changes | none | — |
| Remote feature branch | absent | `git ls-remote --heads` |
| Existing Pull Request | none | `gh pr list` |
| QA decision | PASS (TST-01) | report |

## 3. Threat model

### Protected assets

- Operating-mode restrictions (READ_ONLY / WORKSPACE_WRITE / DELIVERY).
- Hard-prohibition configuration.
- Allowlist authorization.
- Approval-required authorization for external and destructive actions.
- Approval lifecycle integrity (single-use, expiry, revocation).
- Mode-escalation gating.
- Deterministic, machine-readable denials.

### Trust boundaries

- The domain package is a modeling/enforcement layer invoked by a future application layer.
- `InMemoryApprovalManager` is the authoritative approval store; its `validate`/`consume`/`revoke` are the safe entry points.
- `DefaultPolicyEngine.decide` trusts the `PolicyRequest` inputs, including a caller-supplied `ApprovalRecord`.
- Approver identity is an untrusted reference (no authentication in Phase 2).

### Threat actors

- Untrusted CLI or application caller.
- Caller supplying malformed action/target data.
- Caller holding an approval for a different action/target/mode/scope.
- Caller replaying a consumed approval.
- Concurrent callers consuming one approval.
- Caller constructing an `ApprovalRecord` directly (forgery).
- Caller invoking low-level evaluators directly to bypass the manager.

### Untrusted inputs

- Action names, targets, scopes, allowlist patterns, approval records, timestamps, mode strings.

### Security invariants

- Hard prohibitions cannot be overridden.
- Mode restrictions cannot be overridden by allowlist or approval.
- Deny rules beat allow rules.
- Missing/unknown/ambiguous information denies.
- Approval binds to action, target, scope, and mode.
- Approval must be approved, unexpired, unrevoked, unconsumed, single-use.
- Escalation requires approval; unsupported transitions deny.
- Decisions deterministic and machine-readable.

### Deferred integration responsibilities

- Real filesystem targeting and path resolution (Phase 3+).
- Persistent approval storage and authentication (later phases).
- Worktree/sandbox enforcement (Phase 11+).
- GitHub integration (Phase 16).

## 4. Security invariant results

| Invariant | Result | Evidence |
|---|---|---|
| Hard prohibitions cannot be overridden | PASS | hard prohibition beats allowlist + valid approval (probe) |
| Mode restrictions cannot be overridden | PASS | mode denial beats valid approval (probe) |
| Deny rules beat allow rules | PASS | deny beats highest-priority allow (probe) |
| Missing information denies | PASS | missing target/approval deny (probe + suite) |
| Unknown information denies | PASS | unknown action → ACTION_UNKNOWN (suite) |
| Ambiguous information denies | PASS | allow tie → POLICY_CONFIGURATION_ERROR (suite) |
| Action binding enforced | PASS | mismatch → APPROVAL_SCOPE_MISMATCH (probe) |
| Target binding enforced | PASS | mismatch → APPROVAL_SCOPE_MISMATCH (probe) |
| Scope binding enforced | FAIL | scope not checked on action-validation path (MEDIUM-01) |
| Mode binding enforced | PASS | `required_mode` checked (JUSTIFIED_REFINEMENT) |
| Expiration enforced | PASS | exact-instant and post-expiry deny (probe) |
| Revocation enforced | PASS | revoked approval denies (suite) |
| Single-use enforced | PASS | 16-thread race: exactly one success (probe) |
| Escalation approval enforced | PASS | all escalations require valid approval (probe) |
| Unsupported transitions denied | PASS | identity transitions → UNSUPPORTED_TRANSITION (probe) |
| Decisions deterministic | PASS | repeated runs stable |

## 5. Policy-precedence attacks

| Attack scenario | Expected | Actual | Reason code | Result |
|---|---|---|---|---|
| Hard prohibition + allowlist | DENY | DENY | hard_prohibition | PASS |
| Hard prohibition + valid approval | DENY | DENY | hard_prohibition | PASS |
| Mode denial + allowlist | DENY | DENY | mode_prohibits_action | PASS |
| Mode denial + valid approval | DENY | DENY | mode_prohibits_action | PASS |
| Explicit deny + exact allow | DENY | DENY | target_not_allowlisted | PASS |
| Ambiguous rules | DENY | DENY | policy_configuration_error | PASS |
| Missing approval | DENY | DENY | approval_required | PASS |
| Malformed approval | DENY | DENY | approval_scope_mismatch (binding) | PASS |
| Valid approval with no prior denial | ALLOW | ALLOW | allowed | PASS |

Higher-priority denials always win; input ordering does not influence the reason code.

## 6. Approval forgery and confused-deputy review

| Attack path | Classification | Evidence | Security impact |
|---|---|---|---|
| Direct record construction | VULNERABLE (MEDIUM-02) | forged `ApprovalRecord` accepted by `engine.decide` → ALLOWED | approval control bypassable via engine API |
| Altered copied record | PREVENTED | frozen dataclass; `replace` creates a new object, but a forged copy is still accepted (MEDIUM-02) | covered by MEDIUM-02 |
| Unregistered approval | VULNERABLE (MEDIUM-02) | never stored in a manager, still ALLOWED via engine | covered by MEDIUM-02 |
| Known ID with altered data | PREVENTED | manager `validate`/`get` read stored records only | none |
| Stale record replay | PREVENTED | consumed state checked in `evaluate_approval_record` | none |
| Arbitrary approved state | PREVENTED via manager; VULNERABLE via engine (MEDIUM-02) | forged state=APPROVED accepted by engine | covered by MEDIUM-02 |
| Arbitrary approver identity | CONSTRAINED_BY_API | `approver` is an untrusted reference by design | none |
| Manager bypass | VULNERABLE (MEDIUM-02) | direct `evaluate_approval_record`/`engine.decide` calls skip manager | covered by MEDIUM-02 |
| Caller-controlled validity assertion | PREVENTED | engine re-validates the record (state/expiry/binding); no boolean accepted | none |

## 7. Binding and substitution attacks

| Substitution | Result | Evidence |
|---|---|---|
| Different action | DENIED | APPROVAL_SCOPE_MISMATCH |
| Different target | DENIED | APPROVAL_SCOPE_MISMATCH |
| Different action and target | DENIED | APPROVAL_SCOPE_MISMATCH |
| Different mode | DENIED | required_mode mismatch (engine path via record; manager path via request) |
| Different scope | NOT ENFORCED on action path (MEDIUM-01); enforced on transition path | scope checked only by `evaluate_transition_approval` |
| Parent/child target substitution | DENIED | exact equality only |
| Near-match target | DENIED | exact equality only |
| Case substitution | DENIED | exact equality only |
| Separator substitution | DENIED | exact equality only |
| Empty or missing target | DENIED | TARGET_MISSING / invalid |
| Control-character target | DENIED on binding | identifiers normalized; equality exact |
| Unicode lookalike target | DENIED | no normalization (fail closed) |

## 8. Allowlist bypass review

| Technique | Result | Evidence |
|---|---|---|
| Prefix collision | DENIED (literal prefix; sibling `srcX` rejected) | probe |
| Suffix collision | DENIED (exact equality only) | probe |
| Substring match | DENIED | probe |
| Wildcard characters | DENIED (treated literally) | probe (isolated engine) |
| Regex metacharacters | DENIED (treated literally) | probe (isolated engine) |
| Traversal-like segments | LITERAL PREFIX MATCH (no fs resolution in Phase 2) | probe — deferred to Phase 3+ |
| Whitespace | DENIED (no forgiveness) | probe |
| Case changes | DENIED | probe |
| Control characters | DENIED in identifiers; literal in match targets | probe |
| Unicode confusables | DENIED (no normalization) | probe |
| Duplicate rules | DETERMINISTIC | suite |
| Conflicting equal-priority rules | DENIED (ambiguous) | suite |
| Rule ordering | NO EFFECT (deny-first, max priority) | probe |
| Long bounded identifier | PATTERN capped at 4096; bounded | static |

## 9. Mode-transition security

| Scenario | Result | Evidence |
|---|---|---|
| Direct READ_ONLY → DELIVERY | APPROVAL REQUIRED | probe |
| Chained escalation | each escalation needs fresh approval | suite |
| Reused escalation approval | DENIED (wrong destination scope) | probe |
| Wrong destination approval | DENIED (scope mismatch) | probe |
| Action approval used for transition | DENIED (scope mismatch) | probe |
| Transition approval used for action | ALLOWED (scope not enforced on action path) — MEDIUM-01 | probe |
| Identity transition abuse | DENIED (UNSUPPORTED_TRANSITION) | probe |
| De-escalation then replay | consumed/expired approvals deny | suite |
| Malformed mode input | DENIED/invalid (typed enums) | suite |

## 10. Approval lifecycle security

| Attack | Result | Evidence |
|---|---|---|
| Approve terminal record | DENIED (duplicate decision raises ApprovalLifecycleError) | probe |
| Consume pending record | NOT STORED as record until decision; decision required | manager design |
| Consume denied record | DENIED | suite |
| Consume expired record | DENIED (refresh marks EXPIRED) | suite |
| Consume revoked record | DENIED | suite |
| Reconsume record | DENIED | probe |
| Revive terminal state | IMPOSSIBLE (frozen record; only manager transitions) | design |
| Skip registration | not possible via manager; possible via engine forgery (MEDIUM-02) | probe |
| Duplicate registration | DENIED (ApprovalLifecycleError) | suite |
| Replace stored record | PREVENTED (frozen; manager stores its own) | design |
| Mutate returned record | PREVENTED (frozen dataclass) | suite |

## 11. Replay, race, and atomicity

| Scenario | Attempts | Successes | Denials | Final state | Result |
|---|---:|---:|---:|---|---|
| Concurrent consumption | 16 | 1 | 15 | CONSUMED | PASS |
| Consumption vs expiration | suite | — | — | EXPIRED | PASS |
| Consumption vs revocation | suite | — | — | REVOKED/CONSUMED | PASS |
| Concurrent revocation | suite | — | — | REVOKED | PASS |
| Duplicate registration | suite | — | — | unchanged | PASS |
| Sequential replay | suite | 1 | then deny | CONSUMED | PASS |

Validation and consumption are one atomic locked operation in the manager (`threading.Lock`); observable behavior confirms single success.

## 12. Time-boundary security

| Scenario | Result | Evidence |
|---|---|---|
| Before validity | N/A (no valid_from in Phase 2) | design |
| Exact validity start | N/A | — |
| Before expiration | ALLOWED | probe |
| Exact expiration | DENIED (`expires_at <= at_time`) | probe |
| After expiration | DENIED | probe |
| Naive datetime | REJECTED (InvalidDomainValue) | probe |
| Non-UTC aware datetime | comparisons correct (Python normalizes); validator accepts any offset | probe — INFO |
| Reversed range | REJECTED on request (expires <= created); record construction allows expires < decided (LOW) | suite + LOW finding |
| Clock rollback | FixedClock can move backward; residual risk for in-memory manager | INFO (deferred) |
| Clock forward jump | expiration enforced at validation | probe |
| Expiry between validation and consumption | consumption refreshes state under lock; expired → denied | manager `_refresh` |

## 13. Public API boundary

| Check | Result | Classification | Evidence |
|---|---|---|---|
| Security-sensitive constructors | `ApprovalRecord`, `DefaultPolicyEngine`, `evaluate_approval_record` publicly exported | exposed (MEDIUM-02) | `domain/__init__.py` |
| Internal state exposure | `_records`/`_requests` private; `get` returns frozen record | safe | design |
| Mutable stored references | none (frozen) | safe | suite |
| Manager bypass possibility | direct engine/evaluator calls skip manager | VULNERABLE (MEDIUM-02) | probe |
| Caller-controlled approval validity | none (engine re-validates record fields) | safe | probe |
| Required context enforcement | `target=None` denies; typed enums | safe | probe |
| Safe entry point clarity | manager `validate` is authoritative but the engine does not use it for approval validity | unclear (MEDIUM-02) | probe |
| Protocol responsibility clarity | `ApprovalManager`/`PolicyEngine` protocols exist | adequate | design |
| Default argument safety | `target=None`, `approval=None` fail closed | safe | probe |
| Public export minimization | broad re-export in `__init__` incl. evaluators | expandable (MEDIUM-02) | `__init__.py` |

## 14. Input robustness and disclosure

| Check | Result | Evidence |
|---|---|---|
| Wrong types fail closed | PASS (ValueError/InvalidDomainValue, no grants) | probe |
| Empty inputs fail closed | PASS | suite |
| Large bounded inputs | PASS (pattern cap 4096; bounded matching) | static |
| Hostile equality/hash behavior | types validated; frozen dataclasses | suite |
| No state corruption | PASS | suite |
| No raw sensitive disclosure | PASS (static messages; no canary echoed) | probe |
| No control-character injection | PASS (identifiers sanitized) | probe |
| No ANSI injection | PASS | probe |
| No traceback on expected denial | PASS | probe |

## 15. Framework, side-effect, and dependency boundary

| Check | Result | Evidence |
|---|---|---|
| Standard-library-only domain | PASS | imports |
| No framework import | PASS | AST scan |
| No test import in production | PASS | AST scan |
| No dynamic unsafe import | PASS | no eval/exec/__import__ |
| No filesystem side effect | PASS | no os/open/Path usage |
| No subprocess or Git side effect | PASS | none |
| No network or GitHub side effect | PASS | none |
| No model side effect | PASS | none |
| No console or telemetry side effect | PASS | no logging/print in domain |
| No global-state modification | PASS | per-instance state only |
| No new dependency | PASS | pyproject unchanged |
| No unsafe eval/exec/deserialization | PASS | none |

## 16. Regression validation

| Check | Result | Gate | Evidence |
|---|---|---|---|
| Python version | 3.11.9 | 3.11+ | `python --version` |
| Dependency integrity | PASS | PASS | `pip check` |
| Tests collected | 184 | — | pytest |
| Tests passed | 184 | ALL | pytest |
| Tests failed | 0 | 0 | pytest |
| Tests skipped | 0 | — | pytest |
| Line coverage | 99% | ≥90% | pytest-cov |
| Branch coverage | ~99.5% | ≥85% | pytest-cov |
| Security-critical uncovered branches | none in policy/approval/replay | NONE | coverage |

## 17. Findings

### FINDING-AH02-SEC-01 — MEDIUM — Approval scope binding is not enforced on the action-validation path

- Affected contract or file: `src/agent_harness/domain/policy.py` (`evaluate_approval_record`, `DefaultPolicyEngine.decide`), `src/agent_harness/domain/approval_manager.py` (`InMemoryApprovalManager.validate`).
- Threat scenario: An approval issued for one purpose is reused for a different purpose with the same action and target. Demonstrated: an approval requested with scope `mode_transition:read_only:workspace_write` (action `EXTERNAL_PUSH`) is accepted by `engine.decide` as authorization for `EXTERNAL_PUSH` in `DELIVERY`, returning `ALLOWED`.
- Evidence: adversarial probe — `transition approval reused as action approval → rc=allowed`.
- Expected: `evaluate_approval_record` should match action, target, AND scope on every validation (design §9 "Approval scope mismatch → deny"; §22 "Strict action+target+scope match on every validation").
- Actual: only action and target are compared; `scope` is checked only by the transition path (`evaluate_transition_approval`). The `APPROVAL_SCOPE_MISMATCH` reason code is unreachable via scope on the action path.
- Exploitability: Requires possession of a manager-issued approval whose action/target coincide with the target action; enables confused-deputy reuse (e.g., a transition approval doubling as an action approval).
- Impact: Approval scope binding is materially incomplete; an approval granted for one scope can authorize the same action+target under another scope.
- Required remediation: Add scope matching to `evaluate_approval_record` (e.g., an expected-scope parameter threaded from `PolicyRequest`/`validate`), so action+target+scope are matched on every validation.

### FINDING-AH02-SEC-02 — MEDIUM — Approval authenticity is not verified by the policy engine (forgery / manager bypass)

- Affected contract or file: `src/agent_harness/domain/policy.py` (`evaluate_approval_record`, `DefaultPolicyEngine.decide`, `evaluate_transition_approval`), public export of `ApprovalRecord`.
- Threat scenario: A caller constructs an `ApprovalRecord` directly (state=APPROVED, correct action/target, far-future expiry) without any manager, then calls `engine.decide` or `evaluate_approval_record` directly and obtains `ALLOWED` for a protected external/destructive action or a mode escalation. The manager's `validate` (by id against the store) is authoritative, but the engine's decide path never consults it.
- Evidence: adversarial probe — `forged ApprovalRecord accepted by engine.decide → rc=allowed`; `forged transition approval accepted → rc=allowed`.
- Expected: The approval-required control should be backed by an authoritative store or a manager-issued validity attestation; the public API should make it unmistakable that only manager-validated approvals authorize actions.
- Actual: Any well-formed `APPROVED` record is accepted by the engine and by `evaluate_approval_record`; there is no issuer check or manager binding.
- Exploitability: Requires the ability to invoke the domain directly (the integration/application layer). The documented manager-centric flow (design §20) is secure; the engine API is the weak boundary.
- Impact: The "approval required" security boundary can be bypassed through the engine's public API if an integration uses `engine.decide` as the final authorization decision rather than `manager.validate`/`consume`.
- Required remediation: Bind the engine's approval validation to the manager (e.g., inject an approval-validator/lookup and resolve by approval id, or require a manager-issued attestation), and/or narrow the public exports so security-sensitive evaluators are not trivially reachable without the manager.

### FINDING-AH02-SEC-03 — LOW — `ApprovalRecord` does not validate `expires_at` against `decided_at`

- Affected contract or file: `src/agent_harness/domain/approvals.py`.
- Evidence: direct construction with `expires_at < decided_at` is accepted (request construction rejects expiry before creation, but record construction has no such check).
- Expected: record timestamps should be consistent (expiry after decision) or at least validated.
- Actual: accepted; however the record then fails closed as EXPIRED at validation, so no authorization gain.
- Impact: validation gap only; fail-closed.
- Required remediation: add `expires_at > decided_at` validation to `ApprovalRecord.__post_init__`.

### FINDING-AH02-SEC-04 — LOW — `validate_utc` accepts any aware timezone, not strictly UTC

- Affected contract or file: `src/agent_harness/domain/errors.py`.
- Evidence: aware datetimes with non-UTC offsets pass validation; comparisons remain correct because Python normalizes aware datetimes.
- Expected: UTC-only per the design wording ("UTC-aware"); behavior is safe but the validator name/check is looser than the description.
- Impact: no correctness issue (comparisons correct); documentation/validation strictness only.
- Required remediation: optionally require `utcoffset() == timedelta(0)`.

## 18. Residual risks

- Approval authenticity and scope binding gaps (MEDIUM-01, MEDIUM-02) must be closed before Phase 7 model integration or any real enforcement.
- Wall-clock rollback: `FixedClock` may move backward; the in-memory manager cannot detect system-clock rollback. Accepted for the in-memory implementation; revisit with persistent storage.
- Literal prefix allowlist matching authorizes targets containing traversal-like segments inside an allowed prefix; no filesystem resolution exists in Phase 2 — the responsibility moves to Phase 3+ filesystem-relative targeting.
- Hard prohibitions are empty by default in `DefaultPolicyEngine`; the configuration of concrete hard prohibitions is an application/integration responsibility (mechanism exists and is tested).
- `external`/`destructive` fields on `PolicyRequest` are not consulted by the engine (the action category is authoritative); they are effectively decorative and could mislead integrations.
- `PolicyRequest.target` vs `ActionName.target` redundancy: allowlist and approval checks use `request.target`; approval binding fails closed when they differ, but the API invites confusion.

## 19. Repository state

- Current branch: feature/ah-02-domain-contracts
- HEAD: f9f28a1...
- Feature commits: 0
- Staged files: none
- Authorized security report change: `reports/AH-02-SEC-01.md` (created)
- Other persistent changes caused by review: none
- Remaining temporary artifacts: none (temp dir removed)
- Remote operations: none
- GitHub operations: none

## 20. Commands executed

- Git/gh read-only checks; `python --version`, `python -m pip check`
- `python -m pytest -p no:cacheprovider`, `python -m pytest --cov=agent_harness --cov-branch` (coverage data outside the repo)
- Adversarial security probe (forgery, bindings, allowlist, transitions, lifecycle, time, inputs, concurrency)
- Static scans: dangerous-import patterns, dynamic imports, secret patterns, pyproject diff
- No credentials, tokens, or raw sensitive canaries were output.

## 21. Recommended next action

RETURN_TO_AH-02-IMP-FIX-01

Two MEDIUM findings must be addressed before operational validation: (1) approval scope is not enforced on the action-validation path, enabling confused-deputy reuse of approvals (e.g., a transition approval authorizing the same action); and (2) the policy engine accepts forged, manager-less `ApprovalRecord` objects, so the approval-required boundary is bypassable through the engine API. Both are localized to the approval-validation path and can be closed by binding scope and authenticity to the authoritative manager within the Phase 2 domain.

## 22. Non-modification attestation

- Only `reports/AH-02-SEC-01.md` was created or modified persistently.
- No production or test file was modified.
- No architecture, implementation, or QA evidence was modified.
- No dependency was installed or changed.
- No file was staged.
- No commit was created or amended.
- No branch was created, switched, pushed, or deleted.
- No Pull Request, review, comment, or GitHub resource was modified.
- No container or service was started.
- No filesystem, Git, network, GitHub, or runtime-model action was performed through the domain layer.
- No credential, secret, or raw sensitive canary was exposed.
- All temporary security-testing artifacts were removed.
