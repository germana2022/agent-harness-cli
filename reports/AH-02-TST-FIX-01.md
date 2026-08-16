# AH-02-TST-FIX-01 — Independent Approval Boundary Fix Validation

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
| Git root | D:/agente-harness | `git rev-parse` |
| Current branch | feature/ah-02-domain-contracts | `git branch --show-current` |
| HEAD | f9f28a1... | `git rev-parse HEAD` |
| Feature commits | 0 | `git rev-list --count main..HEAD` |
| Staged files | none | `git diff --cached` |
| Authorized changes | Phase 2 files only | `git status` |
| Unexpected changes | none | — |
| Original QA decision | PASS (TST-01) | report |
| Security decision | SECURITY_FAIL (SEC-01) | report |
| Fix implementation decision | COMPLETED (IMP-FIX-01) | report |
| Remote feature branch | absent | `git ls-remote --heads` |
| Existing Pull Request | none | `gh pr list` |

## 3. Fix diff review

| Check | Result | Evidence |
|---|---|---|
| Production files modified | errors.py, approvals.py, policy.py, approval_manager.py, transitions.py, `__init__.py` (all within allowed list) | report + source |
| Test files modified | test_policy, test_approval_manager, test_transitions, test_approvals, test_errors | report + source |
| Report created | `reports/AH-02-IMP-FIX-01.md` | present |
| Unexpected files | none | git status |
| Phase 1 unchanged | yes | `git diff -- pyproject.toml cli.py test_cli.py` empty |
| Dependency files unchanged | yes | pyproject unchanged |
| CLI unchanged | yes | cli.py diff empty |
| Diff check | clean | `git diff --check` exit 0 |

## 4. Root-cause correction

| Security requirement | Result | Evidence |
|---|---|---|
| Raw records not authoritative | PASS | `PolicyRequest.approval` is `str | None`; raw records rejected (`ValueError`) |
| Manager-backed lookup | PASS | engine resolves via injected `ApprovalAuthority`; manager reads stored records |
| Current stored state used | PASS | stale copies deny after consumption/revocation/expiration (probes) |
| Canonical action scope | PASS | `action_scope(action)` = `action:<capability>` |
| Canonical transition scope | PASS | `transition_scope(from,to)` = `mode_transition:<from>:<to>` |
| Cross-purpose isolation | PASS | transition↔action cross-use denied (`APPROVAL_SCOPE_MISMATCH`) |
| Atomic final authorization | PASS | `consume_action`/`consume_transition` validate+consume under one lock |
| Insecure legacy path removed | PASS | `validate`/public evaluators removed; not exported |
| Timestamp ordering enforced | PASS | `expires_at < decided_at` rejected |
| UTC offset enforced | PASS | `validate_utc` requires zero offset |

## 5. Forgery and provenance regression

| Scenario | Expected | Actual | Reason code | Result |
|---|---|---|---|---|
| Directly constructed record | DENY | API rejection (`ValueError`) | — | PASS |
| Raw record passed as identifier | DENY | rejected by API | — | PASS |
| Unregistered identifier | DENY | DENY | approval_missing | PASS |
| Same-ID altered record | DENY | engine resolves stored record, not caller copy | allowed (stored is authoritative) | PASS |
| Stale copy after consumption | DENY | DENY | approval_consumed | PASS |
| Stale copy after revocation | DENY | DENY | approval_revoked | PASS |
| Stale copy after expiration | DENY | DENY | approval_expired | PASS |
| Engine without authority | DENY or unavailable | DENY (fail closed) | approval_missing | PASS |
| Lower-level evaluator bypass | DENY or unavailable | evaluators internal/not exported; engine requires authority | — | PASS |
| Valid authoritative approval | ALLOW | ALLOW | allowed | PASS |

## 6. Scope-binding regression

| Scenario | Expected | Actual | Reason code | Result |
|---|---|---|---|---|
| Transition approval for action | DENY | DENY | approval_scope_mismatch | PASS |
| Action approval for transition | DENY | DENY | approval_scope_mismatch | PASS |
| Wrong action scope | DENY | DENY | approval_scope_mismatch | PASS |
| Wrong transition pair | DENY | DENY | approval_scope_mismatch | PASS |
| Wrong target | DENY | DENY | approval_scope_mismatch | PASS |
| Wrong mode | DENY | DENY | approval_scope_mismatch | PASS |
| Wrong purpose | DENY | DENY | approval_scope_mismatch | PASS |
| Correct action authorization | ALLOW | ALLOW | allowed | PASS |
| Correct transition authorization | ALLOW | ALLOW | allowed | PASS |

## 7. Consumption and concurrency

| Scenario | Attempts | Successes | Denials | Final state | Result |
|---|---:|---:|---:|---|---|
| Concurrent action consumption | 8 | 1 | 7 | CONSUMED | PASS |
| Concurrent transition consumption | 8 | 1 | 7 | CONSUMED | PASS |
| Consumption vs revocation | suite | — | — | REVOKED/CONSUMED | PASS |
| Consumption vs expiration | suite | — | — | EXPIRED | PASS |
| Scope mismatch vs valid consumer | mixed | only valid succeeds | others deny | CONSUMED | PASS |
| Forged ID vs valid consumer | 4 (mixed) | 1 (valid id only) | 3 | CONSUMED | PASS |
| Sequential replay | 2 | 1 | 1 | CONSUMED | PASS |

- Raw `consume(approval_id)` classification: SAFE_AND_CLEAR — retained as a documented lifecycle primitive; it is not an authorization gate; after raw consumption, `authorize_action` denies with `APPROVAL_CONSUMED` (probe).
- Evidence: probe + suite concurrency tests.
- Security impact: none; all consuming authorization paths are scoped and atomic.

## 8. Timestamp validation

| Scenario | Result | Evidence |
|---|---|---|
| Expiry before decision | rejected | `InvalidDomainValue` |
| Expiry equal to decision | accepted; immediately expired (fail closed) | probe |
| Exact expiration | denied (`expires_at <= at_time`) | suite |
| Naive creation time | rejected | suite |
| Naive decision time | rejected | suite |
| Naive expiration time | rejected | suite |
| Positive non-zero offset | rejected | probe |
| Negative non-zero offset | rejected | probe |
| UTC zero offset | accepted | suite |
| Custom zero-offset timezone | accepted (utcoffset()==0) | probe |
| Fixed clock | deterministic | suite |
| Production UTC clock | UTC-aware zero-offset | suite |

## 9. Policy and transition regression

| Contract | Result | Evidence |
|---|---|---|
| Hard prohibition precedence | PASS | beats any approval (probe) |
| Mode-denial precedence | PASS | beats any approval (probe) |
| Explicit deny precedence | PASS | suite |
| Ambiguity denial | PASS | `POLICY_CONFIGURATION_ERROR` |
| Missing approval denial | PASS | `APPROVAL_REQUIRED` |
| Unknown approval denial | PASS | `APPROVAL_MISSING` |
| Expired approval denial | PASS | `APPROVAL_EXPIRED` |
| Revoked approval denial | PASS | `APPROVAL_REVOKED` |
| Consumed approval denial | PASS | `APPROVAL_CONSUMED` |
| Nine-cell transition matrix | PASS | all 9 cells verified (probe) |
| Single-use transition approval | PASS | concurrent transition consume: one success |

Approval evaluation remains after stronger denials (hard prohibition, mode, allowlist); no regression in precedence.

## 10. Public API review

| Check | Result | Evidence |
|---|---|---|
| Raw-record final authorization removed | PASS | `PolicyRequest.approval` is an id |
| Removed helpers not exported | PASS | `evaluate_approval_record`/`evaluate_transition_approval` not in exports |
| Removed helpers not bypassable | PASS | private (`_evaluate_approval_record`); engine/manager are the entry points |
| Authority dependency explicit | PASS | `DefaultPolicyEngine(approval_authority=...)` |
| Fail-closed engine construction | PASS | no authority → `APPROVAL_MISSING` |
| ApprovalRecord construction harmless | PASS | construction alone grants nothing |
| Protocol bindings complete | PASS | `ApprovalAuthority.authorize_action` includes action/target/mode/time; `authorize_transition` includes both modes |
| Action/transition API separation | PASS | distinct methods and canonical scopes |
| Compatibility shim safety | PASS | no shim recreates raw-record acceptance |

## 11. Test-quality assessment

- Tests that reproduce original findings: `test_forged_approval_record_cannot_authorize`, `test_transition_approval_cannot_authorize_action`, forged transition id, stale-copy tests — these would fail pre-fix (raw record accepted; stale copies allowed).
- Negative-path strength: exact reason-code assertions across forgery, scope, mode, target, expiry, revocation, consumption.
- Positive-path strength: correct authoritative action and transition approvals allowed.
- Concurrency quality: 4-thread (suite) and 8-thread (independent probe) `consume_action`/`consume_transition` races assert exactly one success and no exceptions.
- Timestamp quality: ordering, naive, positive/negative offsets, zero-offset, custom zero-offset, exact boundary.
- Missing or weak cases: none material.
- Implementation-coupling concerns: two tests target the private `_evaluate_approval_record` for defensive branch coverage — acceptable; all security-critical assertions use public APIs.
- Regression-protection assessment: strong — Phase 1 suite preserved; precedence and transition matrices re-verified.

## 12. Full validation results

| Check | Result | Gate | Evidence |
|---|---|---|---|
| Python version | 3.11.9 | 3.11+ | `python --version` |
| Dependency integrity | clean | PASS | `pip check` |
| Focused fix tests | pass | PASS | domain tests |
| Tests collected | 202 | — | pytest |
| Tests passed | 202 | ALL | pytest |
| Tests failed | 0 | 0 | pytest |
| Tests skipped | 0 | — | pytest |
| Line coverage | 99% | ≥90% | pytest-cov |
| Branch coverage | ~99.5% | ≥85% | pytest-cov |
| Domain coverage | 100% (line + branch, all domain files) | — | pytest-cov |
| Fix changed-lines coverage | 100% (all modified domain lines covered) | 100% practical | coverage |
| Security-critical uncovered branches | none | NONE | coverage |
| Side-effect scan | CLEAN | CLEAN | pattern scan |
| Dependency scan | CLEAN (no new dep) | CLEAN | pyproject diff |

The independently collected test count (202) matches the reported count.

## 13. Findings

- FINDING-AH02-TST-FIX-01 — INFO — `policy._evaluate_approval_record` remains a module-level private helper reachable via deliberate private access. It is not exported, is not the final authorization path, and construction alone grants nothing; all authorization resolves through the manager. Required remediation: NO_ACTION_REQUIRED.
- FINDING-AH02-TST-FIX-02 — INFO — Raw `consume(approval_id)` is retained as a documented lifecycle primitive (not an authorization gate); `authorize_action`/`consume_action` are the security-relevant entry points. Required remediation: NO_ACTION_REQUIRED.

No BLOCKER, HIGH, or MEDIUM findings.

## 14. Findings closure

| Original finding | Status | Evidence |
|---|---|---|
| FINDING-AH02-SEC-01 | FIXED | cross-purpose scope reuse denied on every path |
| FINDING-AH02-SEC-02 | FIXED | forged/unregistered/stale/manager-less approvals cannot authorize |
| FINDING-AH02-SEC-03 | FIXED | `expires_at < decided_at` rejected |
| FINDING-AH02-SEC-04 | FIXED | non-zero UTC offsets rejected; zero-offset accepted |

## 15. Repository state

- Current branch: feature/ah-02-domain-contracts
- HEAD: f9f28a1...
- Feature commits: 0
- Staged files: none
- Authorized QA report: `reports/AH-02-TST-FIX-01.md` (created)
- Other changes caused by this task: none
- Remaining artifacts: none (temp dir removed)
- Remote operations: none
- GitHub operations: none

## 16. Commands executed

- Git/gh read-only checks; `python --version`, `python -m pip check`
- `python -m pytest -p no:cacheprovider`, `python -m pytest --cov=agent_harness --cov-branch --cov-report=term-missing` (coverage data outside the repo)
- Independent adversarial probe (forgery, provenance, scope, consumption, concurrency, timestamps, precedence, 9-cell transition matrix)
- Public API export review and static scans
- No credentials, tokens, or raw security canaries were output.

## 17. Recommended next action

PROCEED_TO_AH-02-SEC-FIX-01

Both original MEDIUM findings are demonstrably fixed: approvals resolve authoritatively by identifier through the manager, canonical action and transition scopes are enforced on every authorization and consumption path, and forged/stale/altered/unregistered approvals cannot authorize. Atomic single-use consumption holds under concurrency, timestamp and UTC invariants are enforced, and all 202 tests with 100% domain coverage pass. The fix is ready for an independent security re-review.

## 18. Non-modification attestation

- Only `reports/AH-02-TST-FIX-01.md` was created or modified persistently.
- No production or test file was modified.
- No prior evidence report was modified.
- No Phase 1 file was modified.
- No dependency was added, removed, installed, or updated.
- No file was staged.
- No commit was created or amended.
- No branch was created, switched, pushed, or deleted.
- No Pull Request or GitHub resource was modified.
- No container or service was started.
- No infrastructure or runtime-model action was performed.
- No credential, secret, or raw security canary was exposed.
- All temporary validation artifacts were removed.
