# AH-01-ARC-01 — CLI Bootstrap Design Report

## Status

COMPLETED

## Timestamp

2026-08-14

## Repository and branch

- Repository: `D:/agente-harness`
- Branch: `feature/ah-01-cli-bootstrap`
- Base commit: `3f421e4ad2b4a066941a94cef910a8694d5a1ee5`
- Working tree before task: clean, `main` tracking `origin/main`

## Files created

- `docs/PHASE_01_CLI_BOOTSTRAP_DESIGN.md`
- `reports/AH-01-ARC-01.md`

## Scope

Design-only increment for the Phase 1 CLI bootstrap: package metadata, src layout, CLI entry point, version/health/config-check commands, text and JSON output, exit-code and logging contracts, typed configuration, unit and integration tests, developer workflow, coverage gates, and acceptance criteria. No implementation code.

## Important decisions

- `--output`, `--verbose`, `--no-color` are global options placed before the subcommand.
- Single version source of truth in `src/agent_harness/version.py`.
- Configuration instantiated once at CLI startup and shared by commands.
- `read_only=false` is rejected with a sanitized `ConfigurationError` (exit code `3`).
- Output abstraction keeps stdout (functional/JSON) separate from stderr (logging/diagnostics); JSON never contains ANSI.
- Logging via standard library to stderr; no log file, telemetry, or network transport.
- Exceptions translate to exit codes only at the CLI boundary; helpers never call `sys.exit`.
- CLI tests use the Typer `CliRunner` with one module-parity test where practical.
- Console and module entry points route through the same `cli.py` application.

## Dependency decisions

- Runtime: Typer, Pydantic, pydantic-settings.
- Development: pytest, pytest-cov.
- Explicitly excluded: LangChain, LangGraph, Qdrant, Chroma, Docker SDK, GitPython, Tree-sitter, HTTP/LLM/GitHub SDKs, direct Rich.
- Versions to be selected (compatible, non-prerelease) and recorded at implementation time; none installed in this task.

## Command contracts

- `version`: text `agent-harness 0.1.0`; JSON `{"command":"version","status":"ok","version":"0.1.0"}`.
- `health`: process/runtime only; text `status/version/python`; JSON adds `python_version`; success requires Python >= 3.11, version available, core configuration instantiable.
- `config-check`: text `configuration: valid`; JSON `{"command":"config-check","status":"ok","configuration":"valid"}`; invalid config returns exit code `3` without exposing secrets.

## Test and coverage requirements

- Unit tests: version source, default/overridden configuration, `read_only=false` rejection, invalid log level, text/JSON output, no ANSI in JSON, exit-code constants.
- Integration tests: all three commands in text and JSON modes, `--help`, invalid command, invalid output format, invalid configuration, `read_only=false`, plus stdout/stderr/exit-code/JSON-validity assertions and module parity.
- Coverage gate: line >= 90%, branch >= 80%, changed-lines coverage >= 100% where practical.

## Risks

Documented in the design (§17): global-option placement, Pydantic Settings parsing, version drift, JSON/logging pollution, Windows Python ambiguity, Typer/Click exit codes, premature abstractions, README overclaiming.

## Deferred functionality

Repository analysis, Git tooling, search, OpenCode integration, ticket workflows, target-repo test execution, target-repo coverage parsing, PR review, worktrees, sandbox, GitHub integration, RAG.

## Validation performed

- Preflight verified root `D:/agente-harness`, branch `main`, clean tree, local and remote hashes both `3f421e4`.
- Branch `feature/ah-01-cli-bootstrap` created and confirmed current.
- Design contains all 18 required sections.
- All 10 architecture decisions have explicit answers.
- No source code or dependency file created.
- No existing file modified.
- Relative Markdown links validated (no broken targets).
- No claim that Phase 1 is already implemented.

## Git status

```text
?? docs/PHASE_01_CLI_BOOTSTRAP_DESIGN.md
?? reports/AH-01-ARC-01.md
```

No files staged. Branch `feature/ah-01-cli-bootstrap` not pushed.

## Confirmation

Only the authorized Phase 1 design and architecture report were created. No implementation, dependency installation, commit, push, or GitHub modification occurred.
