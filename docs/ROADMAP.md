# Approved Roadmap

Phase order is fixed. Each phase lists its objective, main deliverables, entry conditions, exit gate, and explicitly deferred functionality.

## Phase 0 — Repository and project constitution

- Objective: Establish the repository, documentation, and operating conventions for the project.
- Main deliverables: README, project constitution, architecture baseline, security model, roadmap, Definition of Done, repository conventions, `.python-version`, `.gitignore`.
- Entry conditions: Local repository initialized; origin configured to the approved GitHub repository.
- Exit gate: All foundation documents created, validated, and reviewed; no application code.
- Deferred: All application functionality.

## Phase 1 — CLI bootstrap

- Objective: Stand up the CLI entry point, project packaging, and command skeleton.
- Main deliverables: Python 3.11 project scaffold, Typer CLI skeleton, help output, config loading.
- Entry conditions: Phase 0 exit gate passed.
- Exit gate: CLI runs and prints help; basic config loads; no analysis capabilities yet.
- Deferred: Analysis, search, execution, model integration.

## Phase 2 — Domain contracts and policies

- Objective: Define domain contracts, operating-mode model, policy engine, and approval manager.
- Main deliverables: Domain interfaces, operating-mode enforcement, policy and allowlist scaffolding, approval record model.
- Entry conditions: Phase 1 exit gate passed.
- Exit gate: Mode transitions and approvals are modeled and unit-tested.
- Deferred: Concrete repository and model infrastructure.

## Phase 3 — Safe repository inspection

- Objective: Read-only repository inspection with strict boundaries.
- Main deliverables: Repository inspector, allowlist rules, safe traversal, metadata reporting.
- Entry conditions: Phase 2 exit gate passed.
- Exit gate: Inspector reports repository metadata without modifying anything.
- Deferred: Search, reading, mapping, command execution.

## Phase 4 — Exact search and controlled file reading

- Objective: Exact file and text search plus safe, constrained file reading.
- Main deliverables: ripgrep-based exact search, safe file reader with size/type limits, redaction hooks.
- Entry conditions: Phase 3 exit gate passed.
- Exit gate: Search and reading are constrained, tested, and evidence-backed.
- Deferred: Symbol analysis, repository map, semantic search.

## Phase 5 — Repository map and symbol analysis

- Objective: Build a structural repository map and initial symbol analysis.
- Main deliverables: Repository map builder, Tree-sitter-based symbol extraction, structural queries.
- Entry conditions: Phase 4 exit gate passed.
- Exit gate: Map and symbol index are generated for supported languages and validated.
- Deferred: Dependency relationships, Git-history analysis.

## Phase 6 — Trajectories, evidence and context management

- Objective: Record trajectories and manage evidence and context selection.
- Main deliverables: Trajectory recorder, evidence validator, context builder and budget.
- Entry conditions: Phase 5 exit gate passed.
- Exit gate: Trajectories are auditable; context is selected and budgeted.
- Deferred: Model invocation.

## Phase 7 — OpenCode-go and DeepSeek V4 Flash adapter

- Objective: Integrate the model-provider interface with OpenCode-go / DeepSeek V4 Flash.
- Main deliverables: Model-provider interface implementation, OpenCode-go adapter, controlled connectivity test, safe config handling.
- Entry conditions: Phase 6 exit gate passed.
- Exit gate: A controlled, read-only model request succeeds without exposing secrets.
- Deferred: Unattended use, autonomous workflows.

## Phase 8 — Code analysis

- Objective: Evidence-based code analysis on top of inspection, search, and model output.
- Main deliverables: Analysis use cases, evidence-labeled findings, report generation.
- Entry conditions: Phase 7 exit gate passed.
- Exit gate: Analysis reports distinguish facts, hypotheses, and unknowns.
- Deferred: Ticket workflows, implementation.

## Phase 9 — Ticket refinement, impact analysis and planning

- Objective: Turn tickets into refined, impact-analyzed, planned work.
- Main deliverables: Ticket refinement, impact analysis, technical planning use cases.
- Entry conditions: Phase 8 exit gate passed.
- Exit gate: A plan is produced against a ticket with evidence and acceptance criteria.
- Deferred: Implementation and execution.

## Phase 10 — Read-only MVP benchmark and evaluation

- Objective: Evaluate the read-only MVP against a benchmark.
- Main deliverables: Evaluation harness, benchmark scenarios, baseline metrics.
- Entry conditions: Phases 0–9 exit gates passed.
- Exit gate: Read-only behavior is benchmarked and reviewed before any write capability.
- Deferred: Write-enabled behavior, autonomous execution.

## Phase 11 — Worktrees, checkpoints and sandbox

- Objective: Add isolation for controlled implementation and execution.
- Main deliverables: Worktree manager, checkpoint mechanism, sandbox runtime, command runner with limits.
- Entry conditions: Phase 10 exit gate passed.
- Exit gate: Implementation and execution are isolated and auditable.
- Deferred: Test and coverage integration.

## Phase 12 — Build, tests and coverage

- Objective: Controlled build/test execution and coverage analysis.
- Main deliverables: Test runner, build runner, coverage analyzer, changed-lines coverage.
- Entry conditions: Phase 11 exit gate passed.
- Exit gate: Builds, tests, and changed-lines coverage are executed and reported.
- Deferred: Assisted implementation.

## Phase 13 — Assisted ticket implementation

- Objective: Guided, approved implementation inside isolated worktrees.
- Main deliverables: Implementation workflow, approval gates, patch production, local commits when authorized.
- Entry conditions: Phase 12 exit gate passed.
- Exit gate: A ticket is implemented and validated under approval with full evidence.
- Deferred: Remote delivery, PR creation.

## Phase 14 — Local diff and Pull Request review

- Objective: Review local diffs and, when authorized, Pull Requests.
- Main deliverables: Diff reviewer, PR review workflow with explicit approval for publishing.
- Entry conditions: Phase 13 exit gate passed.
- Exit gate: Review outputs are evidence-backed and approval-gated.
- Deferred: Version-controlled quality checks.

## Phase 15 — Version-controlled quality checks

- Objective: Version quality checks and configuration with the repository.
- Main deliverables: Check definitions, lint/format/test configurations, enforcement wiring.
- Entry conditions: Phase 14 exit gate passed.
- Exit gate: Checks are reproducible against a specific commit.
- Deferred: GitHub integration.

## Phase 16 — GitHub integration

- Objective: GitHub read and write operations with explicit human approval.
- Main deliverables: GitHub adapter, push/PR/issue/ticket operations, approval-managed external actions.
- Entry conditions: Phase 15 exit gate passed.
- Exit gate: Every external action requires separate approval and is recorded.
- Deferred: Semantic retrieval, historical memory.

## Phase 17 — Semantic retrieval and historical memory

- Objective: Add semantic retrieval over documentation, ADRs, issues, and historical PRs.
- Main deliverables: Semantic retrieval index, retrieval over docs and history, bounded context integration.
- Entry conditions: Phase 16 exit gate passed.
- Exit gate: Semantic retrieval augments exact evidence without replacing it.
- Deferred: Semantic retrieval over arbitrary source code.

## Phase 18 — Advanced security, debugging and architecture analysis

- Objective: Advanced security review, debugging assistance, and architecture analysis.
- Main deliverables: Security review enhancements, debugging workflow, architecture analysis use cases.
- Entry conditions: Phase 17 exit gate passed.
- Exit gate: Advanced analysis capabilities are evidence-backed and reviewable.
- Deferred: Fully autonomous operation; anything requiring unattended external writes.
