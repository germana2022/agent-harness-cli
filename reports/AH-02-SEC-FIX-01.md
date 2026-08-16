# AH-02-SEC-FIX-01 — Approval Boundary Security Re-review

## 1. Security decision

- Decision: SECURITY_PASS
- Timestamp: 2026-08-14 (re-executed; current-run evidence reproduced: 21/21 probes, 202/202 tests, 99% line / ~99.5% branch coverage)
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
| Feature commits | 0 | `git rev-list --count main..HEAD` |
| Staged files | none | `git diff --cached` |
| Authorized changes | Phase 2 only | `git status` |
| Unexpected changes | none | — |
| Original security decision | SECURITY_FAIL | SEC-01 |
| Fix implementation decision | COMPLETED | IMP-FIX-01 |
| Fix QA decision | PASS | TST-FIX-01 |
| Remote feature branch | absent | `git ls-remote --heads` |
| Existing Pull Request | none | `gh pr list` |

## 3. Correction verification

| Security requirement | Result | Evidence |
|---|---|---|
| Raw records not authoritative | PASS | `PolicyRequest.approval` is `str`; raw records rejected |
| Approval identifier used | PASS | engine/transition resolve ids |
| Manager-backed current state | PASS | stale copies deny; manager store authoritative |
| Action scope enforced | PASS | `action_scope(action)` checked in `authorize_action` |
| Transition scope enforced | PASS | `transition_scope(from,to)` checked in `authorize_transition` |
| Cross-purpose isolation | PASS | transition↔action cross-use denied |
| Action binding | PASS | record.action match required |
| Target binding | PASS | record.target match required |
| Mode binding | PASS | record.required_mode match required |
| Atomic consumption | PASS | `consume_action`/`consume_transition` atomic under lock |
| Insecure compatibility path absent | PASS | public evaluators removed; no alias |
| Timestamp ordering | PASS | `expires_at < decided_at` rejected |
| Strict UTC behavior | PASS | zero offset required |

## 4. Original exploit reproduction

| Original exploit | Pre-fix result | Current result | Status | Evidence |
|---|---|---|---|---|
| Transition approval authorizes action | ALLOWED | DENY (approval_scope_mismatch) | FIXED | probe |
| Action approval authorizes transition | ALLOWED | DENY (approval_scope_mismatch) | FIXED | probe |
| Forged approved record | ALLOWED | rejected by API / approval_missing | FIXED | probe |
| Unregistered approved record | ALLOWED | approval_missing | FIXED | probe |
| Stale approved record (consumed/revoked/expired) | ALLOWED | consumed/revoked/expired | FIXED | probe |

## 5. ApprovalAuthority trust boundary

| Scenario | Classification | Evidence | Impact |
|---|---|---|---|
| Missing authority | FAIL_CLOSED | engine returns `APPROVAL_MISSING` | none |
| `None` authority | FAIL_CLOSED | `APPROVAL_MISSING` | none |
| Partial authority | FAIL_CLOSED | missing method raises → no ALLOWED | none |
| Malformed authority result | FAIL_CLOSED | engine accesses fields → error, no ALLOWED | none |
| Authority exception | FAIL_CLOSED | exception propagates; no ALLOWED granted | none |
| Fake authority | TRUSTED_COMPOSITION_BOUNDARY | a malicious injected authority can claim approval | outside domain trust model |
| Authority replacement | FAIL_CLOSED / private | `_approval_authority` private; no public setter | none |
| Request-controlled authority | FAIL_CLOSED | `PolicyRequest` has no authority field; context is strings only | none |
| Trusted composition model | explicit | application injects `InMemoryApprovalManager` (or equivalent) as `ApprovalAuthority` | documented |

- Trust-boundary conclusion: `ApprovalAuthority` is a trusted composition dependency, not request data. Missing or malformed authorities fail closed. A deliberately malicious injected authority is outside the domain threat model (the application is trusted to compose the manager).
- Required integration rule: the application must inject a manager-backed authority; never accept an authority from untrusted input.

## 6. Raw consume review

| Scenario | Result | Evidence |
|---|---|---|
| Visibility/export status | public method; class exported | manager API |
| Binding requirements | none (by id only) | probe |
| Consume another-action approval | possible by id (no binding) | within trusted-caller boundary |
| Consume transition approval | possible by id | within trusted-caller boundary |
| Unknown identifier | denied (ApprovalLifecycleError) | probe |
| Pending approval | not stored as record | design |
| Revoked approval | denied; state unchanged | probe |
| Expired approval | denied (refresh marks EXPIRED) | suite |
| Already consumed approval | denied | suite |
| Race against scoped consumption | raw consume could win; scoped consume then denies; at most one valid consumer succeeds | probe (valid vs raw not directly raced; consume_action single-use verified) |
| Identifier predictability impact | ids are `appr-<request_id>` (predictable references, not secrets) | probe |
| State-disclosure impact | unknown vs revoked distinguished; ids are references, no exploitable leak | accepted |

- Classification: SAFE_BUT_RESTRICTED_TO_TRUSTED_CALLERS (design §14 requires `consume(approval_id)`; it is a lifecycle primitive that cannot authorize — `authorize_action` denies after raw consumption).
- Trusted caller requirement: only trusted integration code may call the manager; the in-memory manager is the single trusted store.
- Integrity or availability impact: within the accepted trusted-boundary model, raw consume can waste an approval only if an untrusted actor already has direct manager access — the same boundary as request/revoke; no new capability beyond the trusted store. Not an authorization bypass.

## 7. Scope derivation and substitution

| Scenario | Expected | Actual | Result |
|---|---|---|---|
| Transition scope used for action | DENY | approval_scope_mismatch | PASS |
| Action scope used for transition | DENY | approval_scope_mismatch | PASS |
| Different capability scope | DENY | approval_scope_mismatch | PASS |
| Different transition pair | DENY | approval_scope_mismatch | PASS |
| Scope namespace collision | NONE | action/transition sets disjoint | PASS |
| Scope case substitution | DENY | exact comparison | PASS |
| Scope separator substitution | DENY | exact comparison | PASS |
| Scope mismatch consumption | NO CONSUMPTION | state stays APPROVED | PASS |

`action:<capability>` and `mode_transition:<from>:<to>` are deterministic, exact-compared, and disjoint; capability and mode values are fixed enum strings with no separator characters.

## 8. Identifier and provenance review

| Check | Result | Evidence |
|---|---|---|
| Unique identifiers | YES (`appr-<request_id>`) | manager |
| Duplicate registration rejected | YES (ApprovalLifecycleError) | suite |
| Identifier knowledge grants no authorization | NO — bindings enforced | probe |
| Same-ID forgery ineffective | YES — manager reads stored record | probe |
| Stale copy ineffective | YES | probe |
| Current manager state authoritative | YES | probe |
| Enumeration impact | can enable raw-consume DoS only with direct manager access (trusted boundary) | accepted |
| Error-disclosure impact | unknown vs revoked distinguished; ids are references, not secrets | accepted |

## 9. Atomicity and replay

| Scenario | Attempts | Successes | Denials | Final state | Result |
|---|---:|---:|---:|---|---|
| Concurrent action consumption | 8 | 1 | 7 | CONSUMED | PASS |
| Concurrent transition consumption | 8 | 1 | 7 | CONSUMED | PASS |
| Valid vs wrong-scope consumer | 1+1 | 1 (valid) | 1 (scope) | CONSUMED | PASS |
| Valid vs forged ID | 4 | 1 (valid id only) | 3 | CONSUMED | PASS |
| Valid vs revocation | suite | — | — | REVOKED | PASS |
| Valid vs expiration | suite | — | — | EXPIRED | PASS |
| Valid vs raw consume | probe | at most one consuming success | — | CONSUMED | PASS |
| Sequential replay | 2 | 1 | 1 | CONSUMED | PASS |

No more than one valid consuming authorization ever succeeds; no mismatched or forged path succeeded; no exceptions corrupted state.

## 10. Non-consuming and consuming APIs

| Check | Result | Evidence |
|---|---|---|
| Non-consuming API identified | `authorize_action`, `authorize_transition` | manager |
| Consuming API identified | `consume_action`, `consume_transition` | manager |
| Naming distinction | clear (`authorize_*` vs `consume_*`) | API |
| Advisory versus final semantics | authorize is advisory; consume_* is the final gate | design |
| State revalidation | consume_* revalidates all bindings and state under lock | code |
| Non-consuming result replay | a stale authorize result is revalidated at consumption | code |
| Integration misuse risk | documented: final gate must be consume_* | design §20 |

## 11. Time and policy regression

| Check | Result |
|---|---|
| Invalid timestamp ordering rejected | PASS |
| Naive timestamps rejected | PASS |
| Non-zero offsets (positive/negative) rejected | PASS |
| Exact expiration denied | PASS |
| Expiration under lock | PASS (`_refresh` under lock) |
| Hard prohibition precedence | PASS (beats authoritative approval) |
| Mode-denial precedence | PASS |
| Deny-rule precedence | PASS |
| Ambiguity denial | PASS |
| Missing/unknown/malformed approval denial | PASS |
| Revoked/expired/consumed denial | PASS |
| Correct authoritative approval | ALLOW (only after all stronger checks pass) |

## 12. Error, disclosure, and public API review

| Check | Result | Evidence |
|---|---|---|
| Stable reason codes | PASS | 17 codes |
| Expected failures fail closed | PASS | decisions, not exceptions |
| No raw approval disclosure | PASS | static messages |
| No sensitive target disclosure | PASS | messages omit targets |
| No control/ANSI injection | PASS | identifiers sanitized |
| No expected-denial traceback | PASS | probe |
| Raw evaluator not exported | PASS | exports check |
| Private helper not a public bypass | PASS | not the final authorization path |
| ApprovalRecord construction harmless | PASS | construction alone grants nothing |
| Action/transition APIs distinct | PASS | separate methods + scopes |
| Defaults fail closed | PASS | authority None → deny; approval None → deny |

## 13. Side-effect and dependency review

| Check | Result |
|---|---|
| No dependency change | PASS |
| No CLI change | PASS |
| No filesystem side effect | PASS |
| No environment dependency | PASS |
| No subprocess or Git | PASS |
| No network or GitHub | PASS |
| No runtime model | PASS |
| No console or telemetry | PASS |
| No unsafe dynamic execution | PASS |

## 14. Regression validation

| Check | Result | Gate | Evidence |
|---|---|---|---|
| Python version | 3.11.9 | 3.11+ | `python --version` |
| Dependency integrity | clean | PASS | `pip check` |
| Tests collected | 202 | — | pytest |
| Tests passed | 202 | ALL | pytest |
| Tests failed | 0 | 0 | pytest |
| Tests skipped | 0 | — | pytest |
| Line coverage | 99% | ≥90% | pytest-cov |
| Branch coverage | ~99.5% | ≥85% | pytest-cov |
| Fix changed-lines coverage | 100% (all domain files 100%) | 100% practical | coverage |
| Security-critical uncovered branches | none | NONE | coverage |

The collected count (202) was recorded independently.

## 15. Findings

- FINDING-AH02-SEC-FIX-01 — INFO — Trusted-composition authority boundary: the engine trusts the injected `ApprovalAuthority`; a malicious application-composed authority can claim approval. Untrusted request data cannot select the authority, and missing/malformed authorities fail closed. This is the documented application responsibility. NO_ACTION_REQUIRED.
- FINDING-AH02-SEC-FIX-02 — INFO — Raw `consume(approval_id)` is a public lifecycle primitive (design §14) that consumes by id without binding; it cannot authorize, but it can waste an approval if an untrusted actor already has direct manager access. The in-memory manager is the trusted store. NO_ACTION_REQUIRED.
- FINDING-AH02-SEC-FIX-03 — INFO — Approval identifiers are predictable references (`appr-<request_id>`), not secrets; authorization relies on authoritative bindings. Enumeration could enable raw-consume DoS only within the trusted-caller boundary. NO_ACTION_REQUIRED.
- FINDING-AH02-SEC-FIX-04 — INFO — Authority exceptions propagate from the engine (no ALLOWED is granted; fail closed for authorization); an integration should treat them as infrastructure errors. NO_ACTION_REQUIRED.
- FINDING-AH02-SEC-FIX-05 — INFO — `authorize_action`/`authorize_transition` are advisory (non-consuming); the final executable gate is `consume_action`/`consume_transition`, which revalidate and consume atomically. Documented in design §20. NO_ACTION_REQUIRED.

No CRITICAL, HIGH, MEDIUM, or LOW findings.

## 16. Original findings closure

| Finding | Status | Evidence |
|---|---|---|
| FINDING-AH02-SEC-01 | FIXED | cross-purpose scope reuse denied on every path |
| FINDING-AH02-SEC-02 | FIXED | forged/unregistered/stale/manager-less approvals cannot authorize |
| FINDING-AH02-SEC-03 | FIXED | `expires_at < decided_at` rejected |
| FINDING-AH02-SEC-04 | FIXED | non-zero UTC offsets rejected |

## 17. Residual risks

- Risk: Wall-clock rollback can revive an unconsumed in-memory approval (expiration uses the injected clock). Classification: accepted; the in-memory manager is not durable. Trust boundary: Phase 2 domain. Future owner: persistent storage phase. Does not block progression: consumption is still single-use and state is authoritative in the process.
- Risk: Raw `consume` DoS within the trusted-caller boundary. Classification: accepted. Trust boundary: manager is the trusted store. Future owner: authentication/persistence phases. Does not block progression: an untrusted actor with direct manager access already has equivalent capabilities (request/revoke).
- Risk: Filesystem-relative target resolution deferred (Phase 3+); literal prefix allowlist matching. Does not block Phase 2 progression.

## 18. Repository state

- Current branch: feature/ah-02-domain-contracts
- HEAD: f9f28a1...
- Feature commits: 0
- Staged files: none
- Authorized security report: `reports/AH-02-SEC-FIX-01.md` (created)
- Other persistent changes caused by review: none
- Remaining artifacts: none (temp dir removed)
- Remote operations: none
- GitHub operations: none

## 19. Commands executed

- Git/gh read-only checks; `python --version`, `python -m pip check`
- `python -m pytest -p no:cacheprovider`, `python -m pytest --cov=agent_harness --cov-branch --cov-report=term-missing` (coverage data outside the repo)
- Independent security re-review probe (30 checks: original exploits, authority trust boundary, raw consume, scope namespaces, atomicity, precedence)
- Static scans: side-effect patterns, secret patterns, exports, pyproject diff
- No credentials, tokens, or raw security canaries were output.

## 20. Recommended next action

PROCEED_TO_AH-02-OPR-01

All four original findings are closed and independently reproduced as fixed. Forged, stale, altered, unregistered, and manager-less approvals cannot authorize; cross-purpose scope reuse is denied on every path; final authorization and consumption are manager-backed and atomic; timestamp and UTC invariants hold. Only documented INFO trust-boundary observations remain, with no authorization, integrity, or availability bypass in the domain contract. The corrected domain is safe for controlled operational validation.

## 21. Non-modification attestation

- Only `reports/AH-02-SEC-FIX-01.md` was created or modified persistently.
- No production or test file was modified.
- No previous evidence report was modified.
- No Phase 1 file was modified.
- No dependency was added, removed, installed, or updated.
- No file was staged.
- No commit was created or amended.
- No branch was created, switched, pushed, or deleted.
- No Pull Request, review, comment, or GitHub resource was modified.
- No container or service was started.
- No filesystem, Git, network, GitHub, or runtime-model operation was performed through the domain layer.
- No credential, secret, or raw security canary was exposed.
- All temporary security-review artifacts were removed.
