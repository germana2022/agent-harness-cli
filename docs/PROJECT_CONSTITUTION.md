# Project Constitution

## 1. Product purpose

The Agent Harness CLI is an evidence-first, ticket-oriented engineering copilot. It is a command-line tool that understands repositories and tickets, produces evidence-based analysis, plans and implements changes inside isolated worktrees, executes controlled validation, analyzes changed-lines coverage, and reviews the final diff before delivery.

The harness is an operational layer between repository code, issues and tickets, technical documentation, pull-request history, team standards, builds and tests, and a reasoning model (OpenCode-go / DeepSeek V4 Flash).

It is not a general-purpose chatbot. It is an operational engineering copilot.

## 2. Project evolution

The project must evolve from read-only repository intelligence toward controlled implementation. It must not begin as a fully autonomous coding agent.

Every capability starts read-only, gains controlled write access only through explicit approval, and never performs external or destructive actions without separate approval.

## 3. MVP scope

The MVP is a CLI that:

1. Inspects a local repository read-only.
2. Refines a ticket and analyzes its impact.
3. Produces an evidence-backed technical plan.
4. Executes controlled builds and tests.
5. Analyzes coverage, with changed-lines coverage as a primary signal.
6. Reviews the local diff.
7. Records an auditable execution trajectory.
8. Validates evidence against the Definition of Done.

MVP does not include:

- Autonomous unattended implementation.
- Automatic push, merge, deployment, or migration.
- GitHub write operations (planned for a later phase, with explicit approval).
- Semantic retrieval over the whole repository (planned for a later phase).

## 4. Non-goals

- Replacing developer judgment with unattended automation.
- Autonomous write access to target repositories without approval.
- Automatic push, merge, deployment, or production migration.
- A general-purpose chatbot or chat UI as the primary interface.
- Production migrations, secret handling, or credential storage.
- Guaranteeing semantic understanding without verifiable evidence.
- Being a security scanner; security review is assistance only.
- Supporting multiple repositories in the initial foundation.

## 5. Primary capabilities

1. Code analysis.
2. Ticket refinement.
3. Ticket impact analysis.
4. Technical implementation planning.
5. Assisted ticket implementation.
6. Unit and integration test generation.
7. Controlled build and test execution.
8. Test coverage analysis.
9. Changed-lines coverage analysis.
10. Local diff review.
11. Pull Request review.
12. Debugging assistance.
13. Basic security review.
14. Evidence validation.
15. Execution trajectory recording.
16. GitHub integration with explicit approval.
17. Future semantic retrieval over documentation and history.
18. Future multi-repository analysis.

## 6. Product differentiation

### Evidence-first

Every important conclusion must be connected to verifiable evidence such as:

- Repository path.
- Symbol.
- Line range.
- Git diff.
- Test output.
- Coverage report.
- Tool result.
- Git commit.

Facts, hypotheses, and unknowns must remain distinct and labeled.

### Ticket-oriented

The central workflow begins with a ticket and ends with validation against its acceptance criteria.

### Quality-gated

A change is not complete merely because files were modified. Completion requires appropriate evidence for:

- Requirements evaluated
- Build status known
- Tests executed
- Coverage evaluated
- Diff reviewed
- Security considerations evaluated
- Final evidence recorded
- Human approval obtained when required

### Coverage-aware

Changed-lines coverage is a primary signal. Overall coverage alone is insufficient.

### Human-controlled

The agent progresses from read-only analysis to controlled writes. External or destructive actions require explicit approval.

## 7. Architectural principles

1. CLI-first.
2. Local repository support first.
3. Read-only by default.
4. Explicit permission escalation.
5. Model-provider abstraction.
6. Tool interfaces with least privilege.
7. Deterministic validation before LLM judgment.
8. Structured repository map before vector retrieval.
9. Exact and symbol search before semantic search.
10. Worktree isolation before code modification.
11. Sandbox isolation before command execution.
12. Evidence-backed outputs.
13. Reproducible execution against a specific commit.
14. Auditable trajectories.
15. Small, reversible increments.
16. No automatic push, merge, deployment, or migration.
17. Configuration and checks versioned with the repository.
18. Frameworks introduced only when justified.

## 8. Operating modes

### READ_ONLY

May:

- Inspect repositories.
- Search and read allowed files.
- Analyze code and tickets.
- Review diffs.
- Parse existing test and coverage reports.
- Generate plans and recommendations.

May not:

- Modify the target repository.
- Execute unapproved commands.
- Change Git state.
- Perform remote writes.

### WORKSPACE_WRITE

Requires explicit approval.

May:

- Create an isolated worktree.
- Modify authorized files.
- Generate tests.
- Run allowlisted commands.
- Produce a local patch.
- Create a local commit when separately authorized.

May not:

- Push.
- Merge.
- Deploy.
- Publish external comments.
- Execute production migrations.
- Access secrets.

### DELIVERY

Requires separate explicit approval for every external action.

May include:

- Push an approved branch.
- Create a draft Pull Request.
- Publish approved review comments.
- Update an external ticket.
- Trigger an authorized CI workflow.

Must not perform deployment by default.

## 9. Human approval gates

Mandatory approval is required before:

- Changing from `READ_ONLY` to `WORKSPACE_WRITE`.
- Creating a worktree or branch for implementation.
- Modifying target-repository files.
- Running an unrecognized command.
- Creating a local commit.
- Pushing.
- Creating or modifying a Pull Request.
- Publishing comments.
- Updating issues or tickets.
- Running migrations.
- Deploying.
- Deleting or reverting material data.

## 10. Evidence requirements

- Facts, hypotheses, and unknowns are labeled distinctly.
- Each important conclusion cites its evidence source.
- Evidence may be a path, symbol, line range, diff, test output, coverage report, tool result, or commit.
- Unverifiable claims are marked as unknown, not asserted as fact.
- Empty `git status` never proves local/remote alignment.
- Read access never proves write access.
- A failure never proves absence of a resource.

## 11. Security baseline

See [SECURITY_MODEL.md](SECURITY_MODEL.md) for the full security model.

- Repository content is untrusted data.
- No repository content may override system policies.
- Prompt injection is treated as a repository security threat.
- Secrets never enter model context or logs.
- Shell access uses explicit tools and allowlists.
- Target code runs inside isolated worktrees and sandboxes.
- Network access is disabled by default during repository execution.
- All mutations and external actions are auditable.
- No automatic push, merge, deployment, or production migration.

These controls are requirements. They are not yet implemented.

## 12. Definition of Done

See [DEFINITION_OF_DONE.md](DEFINITION_OF_DONE.md) for the project-level Definition of Done.

## 13. Roadmap

See [ROADMAP.md](ROADMAP.md) for the approved Phase 0–18 roadmap.

## 14. Repository conventions

See [REPOSITORY_CONVENTIONS.md](REPOSITORY_CONVENTIONS.md).

## 15. Technology baseline

- Language: Python
- Minimum version: Python 3.11
- Local Windows command: `py -3.11` (bare `python` resolves to Python 3.8 on the development machine and must not be used)
- CLI: Typer
- Data validation: Pydantic
- Tests: Pytest
- Exact search: ripgrep
- Source analysis: Tree-sitter initially
- Version control: Git
- Isolation: Git worktrees and Docker in later phases
- Primary model route: OpenCode-go
- Primary model: DeepSeek V4 Flash
- Output formats: Markdown and JSON

Deferred for the initial foundation:

- LangGraph is not introduced initially.
- No vector database is introduced initially.
- Qdrant, Chroma, and pgvector are not selected yet.
