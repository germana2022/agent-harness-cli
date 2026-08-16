# AH-02-OPR-01 — Domain Policies Operational Validation Report

## 1. Operational decision

- Decision: OPERATIONAL_PASS
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
| Authorized changes | Phase 2 only | `git status` |
| Unexpected changes | none | — |
| Fix QA decision | PASS | TST-FIX-01 |
| Fix security decision | SECURITY_PASS | SEC-FIX-01 |
| Remote feature branch | absent | `git ls-remote --heads` |
| Existing Pull Request | none | `gh pr list` |

## 3. Package and public API

| Check | Result | Evidence |
|---|---|---|
| Fresh-process import | PASS | import from empty temp dir; 51 public names; no threads spawned (active_count=1) |
| Isolated temporary import/install | NOT_EXECUTED (no isolated build performed; fresh process used the supported import config) | — |
| Public exports sufficient | PASS | all workflows built only from package-root exports |
| Private imports required | NONE | all workflow construction used public API |
| Import stdout | empty | pure import: 0 bytes stdout |
| Import stderr | empty | pure import: 0 bytes stderr |
| Import side effects | none | no files created; no subprocess/network/thread |
| Authority dependency clarity | PASS | `DefaultPolicyEngine(approval_authority=manager)` explicit |
| Default safety | PASS | no authority / missing approval / missing target all fail closed |

## 4. Default and allowlist workflows

| Workflow | Expected | Actual | Reason code | Result |
|---|---|---|---|---|
| Default READ_ONLY | READ_ONLY | READ_ONLY | — | PASS |
| Permitted read action | ALLOW | ALLOW | allowed | PASS |
| Prohibited write action | DENY | DENY | mode_prohibits_action | PASS |
| Prohibited external action | DENY | DENY | mode_prohibits_action | PASS |
| Exact allowlist match | ALLOW | ALLOW | — | PASS |
| Prefix/suffix bounded match | ALLOW | ALLOW | — | PASS |
| Near match | DENY | DENY | — | PASS |
| Explicit deny precedence | DENY | DENY | — | PASS |
| Ambiguous rules | DENY | DENY (suite) | — | PASS |
| Empty rules | DENY | DENY | — | PASS |

Decisions were deterministic and caused no manager mutation.

## 5. Action approval workflow

| Step | Result | State or reason | Evidence |
|---|---|---|---|
| Request created | PASS | scope=action_scope(action) | probe |
| Registered | PASS | manager stores request | probe |
| Pending authorization | PASS | pending requests never authorize; missing approval → approval_required | probe |
| Approved | PASS | record APPROVED | probe |
| Advisory authorization | PASS | allows without consuming (state stays APPROVED) | probe |
| Final consumption | PASS | consume_action allows | probe |
| Stored final state | CONSUMED | probe |
| Replay | PASS | approval_consumed | probe |
| Missing identifier | PASS | approval_required | probe |
| Unknown identifier | PASS | approval_missing | probe |
| Revoked approval | PASS | approval_revoked | probe |
| Expired approval | PASS | approval_expired | probe |
| Wrong action | PASS | approval_scope_mismatch | probe |
| Wrong target | PASS | approval_scope_mismatch | probe |
| Wrong mode | PASS | approval_scope_mismatch | probe |
| Wrong scope | PASS | approval_scope_mismatch | probe |

## 6. Transition workflow

| From | To | Approval required | Operational result | Reason code | Result |
|---|---|---|---|---|---|
| READ_ONLY | READ_ONLY | — | DENY | unsupported_transition | PASS |
| READ_ONLY | WORKSPACE_WRITE | Yes | allow after approval; consumed | allowed | PASS |
| READ_ONLY | DELIVERY | Yes | allow after approval; consumed | allowed | PASS |
| WORKSPACE_WRITE | READ_ONLY | No | ALLOW | allowed | PASS |
| WORKSPACE_WRITE | WORKSPACE_WRITE | — | DENY | unsupported_transition | PASS |
| WORKSPACE_WRITE | DELIVERY | Yes | allow after approval; consumed | allowed | PASS |
| DELIVERY | READ_ONLY | No | ALLOW | allowed | PASS |
| DELIVERY | WORKSPACE_WRITE | No | ALLOW | allowed | PASS |
| DELIVERY | DELIVERY | — | DENY | unsupported_transition | PASS |

All nine cells verified; escalations require and consume a fresh single-use approval; de-escalations need none.

## 7. Cross-purpose and final-gate behavior

| Scenario | Result | Evidence |
|---|---|---|
| Transition approval used for action | DENY (approval_scope_mismatch) | probe |
| Action approval used for transition | DENY (approval_scope_mismatch) | probe |
| Approval reused for another capability | DENY (approval_scope_mismatch) | probe |
| Approval reused for another mode pair | DENY (approval_scope_mismatch) | probe |
| Scope mismatch preserves valid approval | PASS (state stays APPROVED) | probe |
| Advisory action authorization | allows without consuming | probe |
| Final action consumption | consumes atomically | probe |
| Advisory transition authorization | allows without consuming | probe |
| Final transition consumption | consumes atomically | probe |
| Revoked after advisory | final blocks (approval_revoked) | probe |
| Expired after advisory | final blocks (approval_expired) | probe |
| Consumed after advisory | final blocks (approval_consumed) | probe |

- Advisory/final API clarity: CLEAR — `authorize_action`/`authorize_transition` are advisory; `consume_action`/`consume_transition` are the final executable gates and revalidate state atomically.
- Integration-use conclusion: an application consumer can reliably distinguish and safely use both.

## 8. Raw lifecycle consume

| Check | Result | Evidence |
|---|---|---|
| Cannot authorize action | PASS | authorization denies after raw consume (approval_consumed) |
| Cannot authorize transition | PASS | transition denies after raw consume |
| Eligible-state behavior | PASS | consumes only APPROVED records |
| Unknown identifier behavior | PASS | ApprovalLifecycleError, no mutation |
| Pending behavior | PASS | pending requests have no record to consume |
| Revoked behavior | PASS | ApprovalLifecycleError, state unchanged |
| Expired behavior | PASS | refresh marks EXPIRED; consume denied |
| Consumed behavior | PASS | second consume denied |
| Trusted lifecycle distinction | PASS | documented primitive; not a final enforcement gate |

- Classification: OPERATIONALLY_CLEAR (trusted-caller lifecycle primitive; not needed by ordinary request handling).
- Required integration warning: only trusted application code should call `consume(approval_id)`; the security-relevant gates are `consume_action`/`consume_transition`.

## 9. Manager isolation and restart behavior

| Check | Result | Evidence |
|---|---|---|
| Manager A/B isolation | PASS | A's approval is APPROVAL_MISSING in B |
| Engine authority isolation | PASS | engine A allows its own; engine B denies A's |
| New manager lacks prior records | PASS | fresh manager returns APPROVAL_MISSING |
| Stale record cannot repopulate | PASS | manager state authoritative; forged/stale copies ineffective |
| Restart/lost state fails closed | PASS | new manager denies everything unknown |
| Persistence boundary documented | PASS | persistence and authenticated issuance are future concerns |

## 10. Concurrency

| Scenario | Attempts | Successes | Denials | Final state | Result |
|---|---:|---:|---:|---|---|
| Concurrent action consumers | 8 | 1 | 7 | CONSUMED | PASS |
| Concurrent transition consumers | 8 | 1 | 7 | CONSUMED | PASS |
| Wrong scope vs correct | 1+1 | 1 | 1 | CONSUMED | PASS |
| Revocation vs consumption | suite | — | — | REVOKED | PASS |
| Expiration boundary | suite | — | — | EXPIRED | PASS |

Zero exceptions during races; exactly one valid consumer succeeded.

## 11. Clock and error-consumer behavior

| Check | Result | Evidence |
|---|---|---|
| Fixed clock deterministic | PASS | advance exact |
| Exact expiration denied | PASS | at expiry instant → approval_expired |
| Post-expiration denied | PASS | after expiry → approval_expired |
| Naive time rejected | PASS | DomainError |
| Non-UTC time rejected | PASS | DomainError |
| Production UTC clock | PASS | UTC-aware zero offset |
| Stable reason codes | PASS | PolicyReasonCode on every decision |
| Domain-error separation | PASS | ApprovalLifecycleError subtype |
| Expected denial has no traceback | PASS | decisions, not exceptions |
| No raw sensitive disclosure | PASS | static sanitized messages |
| No ANSI/control injection | PASS | identifiers sanitized |
| No unsolicited output | PASS | no stdout/stderr during evaluation |

## 12. Fresh-process determinism and side effects

| Check | Result | Evidence |
|---|---|---|
| Repeated-process determinism | PASS | two fresh runs byte-identical |
| Import-order independence | PASS | imports emit nothing; behavior stable |
| Rule-order independence | PASS | deny-first/max-priority |
| Working-directory independence | PASS | ran from empty non-repo dir |
| Files created | none | run dir 0 files after workflows |
| Files modified | none | — |
| Subprocesses | none | no subprocess in domain |
| Git operations | none | — |
| Network operations | none | — |
| GitHub operations | none | — |
| Model calls | none | — |
| Telemetry or logging | none | no logging config |
| stdout/stderr noise | none | pure import + evaluation silent |

## 13. Phase 1 CLI regression

| Scenario | Exit | Result |
|---|---:|---|
| Help | 0 | PASS |
| Version text | 0 | `agent-harness 0.1.0` |
| Version JSON | 0 | valid, no ANSI |
| Health text | 0 | healthy |
| Health JSON | 0 | valid, no ANSI |
| Config-check text | 0 | `configuration: valid` |
| Config-check JSON | 0 | valid, no ANSI |
| Module execution | 0 | parity |
| Unexpected Phase 2 command | 2 | `inspect` → no such command (no Phase 2 CLI) |
| CLI side effects | none | no working-directory files |

## 14. Full validation

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
| Domain coverage | 100% (line + branch) | — | coverage |
| Diff check | clean | CLEAN | `git diff --check` |
| Scope check | PASS | PASS | git status |
| Static side-effect scan | CLEAN | CLEAN | pattern scan |
| Secret scan | CLEAN | CLEAN | pattern scan |

## 15. Findings

- FINDING-AH02-OPR-01 — INFO — Raw `consume(approval_id)` is a trusted-caller lifecycle primitive; not required by ordinary request handling and clearly distinguished from `consume_action`/`consume_transition`. NO_ACTION_REQUIRED.
- FINDING-AH02-OPR-02 — INFO — Approval identifiers are predictable references (`appr-<request_id>`), not credentials; authorization relies on authoritative bindings. NO_ACTION_REQUIRED.
- FINDING-AH02-OPR-03 — INFO — Transition decisions are pure (the domain models transitions as decisions; no global application-mode state is mutated). Application integration is responsible for applying the decision. NO_ACTION_REQUIRED.

No BLOCKER, HIGH, MEDIUM, or LOW findings.

## 16. Residual operational boundaries

- Approval authentication: identity is an untrusted reference; real authentication is future work. Does not block Phase 2 (approvals are in-memory domain data).
- Persistent approval storage: in-memory manager loses state on restart, failing closed safely. Future persistence phase.
- Filesystem-relative target resolution: Phase 3+.
- Worktree or sandbox enforcement: Phase 11+.
- Git and GitHub adapters: Phase 16.
- Runtime-model integration: Phase 7+.

None block Phase 2 publication; all currently fail closed.

## 17. Repository state

- Current branch: feature/ah-02-domain-contracts
- HEAD: f9f28a1...
- Feature commits: 0
- Staged files: none
- Authorized operational report: `reports/AH-02-OPR-01.md` (created)
- Other persistent changes caused by this task: none
- Remaining artifacts: none (temp dir removed)
- Remote operations: none
- GitHub operations: none

## 18. Commands executed

- Git/gh read-only checks; `python --version`, `python -m pip check`
- Fresh-process import checks (pure import stdout/stderr capture)
- Operational workflow probe (50 checks) and concurrency/clock/error probe (12 checks), run from an empty non-repo directory
- Fresh-process determinism (two runs compared by hash)
- Phase 1 CLI smoke (help, version, health, config-check text/JSON, module, unknown command)
- `pytest -p no:cacheprovider` and `pytest --cov --cov-branch` (coverage data outside the repo)
- Static side-effect and secret scans
- No credentials, tokens, or raw sensitive values were output.

## 19. Recommended next action

PROCEED_TO_AH-02-GIT-01

The domain package is operationally usable through supported public APIs with no private-import requirement, deterministic and fail-closed behavior, clear advisory-versus-consuming authorization semantics, atomic single-use consumption, manager isolation, and zero side effects. All 50 workflow checks and 12 concurrency/clock checks pass, 202/202 tests pass with the domain at 100% coverage, and the Phase 1 CLI is unchanged. The phase is ready for publication.

## 20. Non-modification attestation

- Only `reports/AH-02-OPR-01.md` was created or modified persistently.
- No production or test file was modified.
- No previous evidence report was modified.
- No Phase 1 file was modified.
- No dependency was added, removed, downloaded, installed, or updated in the repository environment.
- No file was staged.
- No commit was created or amended.
- No branch was created, switched, pushed, or deleted.
- No Pull Request or GitHub resource was modified.
- No container or service was started.
- No real filesystem, Git, network, GitHub, or runtime-model action was performed through the domain package.
- No credential, secret, or raw sensitive value was exposed.
- All temporary operational artifacts were removed.
