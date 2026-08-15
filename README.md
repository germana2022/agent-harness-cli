# Agent Harness CLI

An evidence-first, ticket-oriented engineering copilot CLI. It is designed to inspect repositories and tickets, produce evidence-backed analysis, plan and implement changes inside isolated worktrees, execute controlled validation, analyze changed-lines coverage, and review the final diff before delivery.

## Status

**Foundation / Pre-MVP.** The project constitution and architecture baseline are established. Phase 1 (CLI bootstrap) is implemented: the package installs and provides `version`, `health`, and `config-check` commands. All analysis, search, model, and integration capabilities remain planned.

## Implemented in Phase 1

- Installable Python 3.11 package (`agent-harness-cli`).
- Console command `agent-harness` and module entry point `py -3.11 -m agent_harness`.
- Commands: `version`, `health`, `config-check`.
- Global options: `--output text|json`, `--verbose`, `--no-color`.
- Typed configuration via `AGENT_HARNESS_*` environment variables with a mandatory read-only default.
- Text and JSON output, stable exit codes, and stderr logging.

## Getting started (Windows)

Python 3.11 or newer is required. Use `py -3.11` (bare `python` resolves to Python 3.8 on this machine).

```bash
py -3.11 -m venv .venv
.venv\Scripts\python.exe -m pip install --upgrade pip
.venv\Scripts\python.exe -m pip install -e ".[dev]"
```

Run commands:

```bash
agent-harness --help
agent-harness version
agent-harness --output json version
agent-harness health
agent-harness config-check
```

Global options appear before the subcommand. Run tests with:

```bash
.venv\Scripts\python.exe -m pytest
```

## Planned core capabilities

Target capabilities (not yet implemented):

- Repository inspection and code analysis.
- Ticket refinement and impact analysis.
- Technical implementation planning.
- Assisted ticket implementation.
- Unit and integration test generation.
- Controlled build and test execution.
- Test coverage analysis, including changed-lines coverage.
- Local diff and Pull Request review.
- Debugging and basic security assistance.
- Evidence validation and execution trajectory recording.
- GitHub integration with explicit human approval.
- Future semantic retrieval over documentation and history.

## Design principles

- Read-only by default; explicit permission escalation for any write.
- Evidence-first: every important conclusion tied to verifiable evidence.
- Deterministic validation before LLM judgment.
- Exact and structural search before semantic retrieval.
- Worktree and sandbox isolation before code modification or command execution.
- No automatic push, merge, deployment, or migration.

## Architecture summary

Planned high-level layers: a CLI entry point, application use cases, a domain layer with contracts, and infrastructure adapters (repository inspector, exact search, safe file reader, Git adapter, model provider, OpenCode-go adapter, worktree manager, sandbox runtime, test runner, coverage analyzer, diff/PR reviewer, trajectory recorder). The domain layer is designed to depend on interfaces only, not on any concrete provider or framework.

## Safety model

Designed safety controls include operating modes (`READ_ONLY`, `WORKSPACE_WRITE`, `DELIVERY`), mandatory human approval gates before writes and external actions, prompt-injection awareness, secret redaction, allowlisted command execution, and auditable trajectories. These controls are requirements, not yet implemented.

## Approved roadmap

See [docs/ROADMAP.md](docs/ROADMAP.md) for the approved 18-phase roadmap.

## Documentation

- [Project constitution](docs/PROJECT_CONSTITUTION.md)
- [Architecture](docs/ARCHITECTURE.md)
- [Security model](docs/SECURITY_MODEL.md)
- [Definition of Done](docs/DEFINITION_OF_DONE.md)
- [Repository conventions](docs/REPOSITORY_CONVENTIONS.md)

## Development status warning

This project is at foundation stage. Only the Phase 1 CLI bootstrap is implemented. Every other feature described in this README is planned, designed, or a target capability and is not yet implemented. Do not expect repository analysis, ticket workflows, coverage analysis, PR review, model integration, or GitHub integration to work.

## License

License not yet selected. A license file will be added in a later phase.

## Repository

https://github.com/germana2022/agent-harness-cli
