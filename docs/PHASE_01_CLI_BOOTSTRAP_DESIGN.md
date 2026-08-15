# Phase 1 — CLI Bootstrap Design

## 1. Phase objective

Phase 1 delivers an installable, testable CLI skeleton that proves:

1. The package can be installed in a Python 3.11 virtual environment.
2. The CLI entry point works.
3. Basic configuration can be validated.
4. Runtime health can be reported.
5. Output and errors follow stable contracts.
6. The bootstrap can be independently tested.
7. No repository-analysis or LLM functionality is introduced yet.

Phase 1 does not analyze repositories, call models, run Docker, modify Git repositories, or connect to GitHub.

## 2. Scope

Phase 1 includes:

- Python package metadata.
- `src` layout.
- CLI entry point.
- Version command.
- Health command.
- Configuration validation command.
- Structured text and JSON output.
- Exit-code contract.
- Logging contract.
- Typed configuration.
- Unit tests.
- CLI integration tests.
- Developer setup instructions.

Phase 1 excludes:

- Repository inspection.
- `ripgrep` integration.
- Git operations.
- Repository map.
- OpenCode integration.
- DeepSeek calls.
- RAG.
- Vector database.
- Worktrees.
- Docker sandbox.
- Ticket analysis.
- Code implementation agents.
- Coverage analysis.
- PR review.
- GitHub API integration.

## 3. Proposed project structure

Target structure for the implementation increment:

```text
agent-harness-cli/
├── pyproject.toml
├── README.md
├── .gitignore
├── .python-version
├── src/
│   └── agent_harness/
│       ├── __init__.py
│       ├── __main__.py
│       ├── cli.py
│       ├── version.py
│       ├── config.py
│       ├── logging_config.py
│       ├── errors.py
│       ├── exit_codes.py
│       └── output.py
├── tests/
│   ├── unit/
│   │   ├── test_config.py
│   │   ├── test_output.py
│   │   └── test_version.py
│   └── integration/
│       └── test_cli.py
├── docs/
├── reports/
└── errors/
```

File responsibilities:

| File | Responsibility |
|---|---|
| `pyproject.toml` | Package metadata, console entry point, build backend, dependencies, pytest configuration. |
| `src/agent_harness/__init__.py` | Package marker and re-exports of public API surface. |
| `src/agent_harness/__main__.py` | Enables `py -3.11 -m agent_harness`, routes to the same CLI application as the console command. |
| `src/agent_harness/cli.py` | Typer application definition, command implementations, and exit-code translation boundary. |
| `src/agent_harness/version.py` | Single source of truth for the package version. |
| `src/agent_harness/config.py` | Pydantic Settings definition and validation. |
| `src/agent_harness/logging_config.py` | Standard-library logging setup to stderr. |
| `src/agent_harness/errors.py` | Minimal exception hierarchy. |
| `src/agent_harness/exit_codes.py` | Exit-code constants. |
| `src/agent_harness/output.py` | Small text/JSON output abstraction. |
| `tests/unit/test_config.py` | Configuration unit tests. |
| `tests/unit/test_output.py` | Output contract unit tests. |
| `tests/unit/test_version.py` | Version source-of-truth unit tests. |
| `tests/integration/test_cli.py` | CLI integration tests. |

Do not create this structure during the architecture task.

## 4. Package and entry-point contract

```text
Distribution name: agent-harness-cli
Import package: agent_harness
Console command: agent-harness
Minimum Python: 3.11
Initial version: 0.1.0
```

Required entry points:

```bash
agent-harness --help
agent-harness version
agent-harness health
agent-harness config-check
py -3.11 -m agent_harness --help
```

The console command and module execution must route through the same CLI application. `cli.py` defines one application; `__main__.py` calls the same entry function.

## 5. Dependency policy

Runtime dependencies:

```text
Typer
Pydantic
pydantic-settings
```

Development dependencies:

```text
pytest
pytest-cov
```

Do not introduce:

- LangChain
- LangGraph
- Qdrant
- Chroma
- Docker SDK
- GitPython
- Tree-sitter
- HTTP clients
- LLM SDKs
- GitHub SDKs
- Rich as a direct dependency (unless Typer already supplies it transitively)

The implementer must select compatible, non-prerelease versions at implementation time and record the resolved environment (e.g., `pip freeze`) in the implementation report. This architecture task does not install or pin dependency versions.

## 6. Command contracts

### `agent-harness version`

Default text output:

```text
agent-harness 0.1.0
```

JSON output (`--output json`):

```json
{
  "command": "version",
  "status": "ok",
  "version": "0.1.0"
}
```

The version must come from one internal source of truth (`version.py`), referenced by the package metadata and the CLI.

### `agent-harness health`

Verifies only the CLI process and basic runtime. It must not check Git, GitHub, Docker, OpenCode, DeepSeek, network connectivity, or a target repository.

Default text output:

```text
status: healthy
version: 0.1.0
python: <detected-version>
```

JSON output:

```json
{
  "command": "health",
  "status": "healthy",
  "version": "0.1.0",
  "python_version": "<detected-version>"
}
```

Health succeeds only when:

- Python is 3.11 or newer.
- Package version is available.
- Core configuration can be instantiated safely.

### `agent-harness config-check`

Validates Phase 1 configuration without displaying secrets.

Success text output:

```text
configuration: valid
```

Success JSON output:

```json
{
  "command": "config-check",
  "status": "ok",
  "configuration": "valid"
}
```

Invalid configuration must:

- Return a nonzero exit code (`3`).
- Identify the invalid field safely.
- Never print a secret value.
- Never print the complete environment.

## 7. Global CLI options

```text
--output text|json
--verbose
--no-color
```

Rules:

- Default output is `text`.
- Machine-readable output uses `--output json`.
- Invalid output formats fail predictably with a usage error (`2`).
- `--verbose` controls diagnostics, not functional output.
- `--no-color` prevents ANSI output.
- JSON output must never contain ANSI control sequences.
- Functional output goes to stdout.
- Diagnostics and errors go to stderr.

Decision: `--output`, `--verbose`, and `--no-color` are global options defined on the Typer application, so they must appear before the subcommand, e.g.:

```bash
agent-harness --output json version
agent-harness --verbose health
agent-harness --no-color config-check
```

Invalid placement after the subcommand is rejected by Typer/Click as a usage error. All examples in this document follow this ordering.

## 8. Configuration contract

Phase 1 settings use Pydantic Settings.

Environment prefix: `AGENT_HARNESS_`

Initial settings:

```text
environment: str = "development"
log_level: str = "INFO"
output_format: "text" | "json" = "text"
read_only: bool = true
```

Requirements:

- `read_only` defaults to `true`.
- Phase 1 must not permit `read_only=false` to authorize writes.
- Environment variables override defaults.
- No `.env` file is loaded automatically.
- No configuration file is required in Phase 1.
- Secret fields are not introduced.
- Unknown environment variables outside the prefix are ignored.
- Invalid defined values produce a sanitized validation error.

Decision: `read_only=false` is REJECTED during Phase 1. The settings validator raises a sanitized `ConfigurationError` ("`read_only` cannot be disabled in Phase 1") when a value of `false` is attempted. This guarantees the CLI can never run with write authorization in Phase 1. Rejection returns exit code `3`.

## 9. Output contract

A small internal output abstraction with:

- Deterministic text output.
- Valid JSON output.
- Separate stdout (functional) and stderr (diagnostics/errors).
- No ANSI in JSON mode.
- No stack traces serialized into normal output.
- Stable field names (`command`, `status`, plus command-specific fields).
- Reusable by later commands.

The output abstraction is limited to Phase 1 needs: a `render(records, output_format)` helper returning pre-formatted strings, and a `success_status()` helper for the JSON envelope. No generic rendering framework is designed.

## 10. Logging contract

- Standard Python logging.
- Logs written to stderr.
- No log file by default.
- No telemetry.
- No network transport.
- No secret values.
- Default level `INFO`.
- `--verbose` enables additional diagnostics (`DEBUG`).
- JSON functional output remains valid even when diagnostics are enabled because logging goes to stderr, not stdout.
- Stack traces appear only for unexpected errors in verbose mode.

## 11. Exit-code contract

```text
0  SUCCESS
2  USAGE_ERROR
3  CONFIGURATION_ERROR
4  ENVIRONMENT_ERROR
10 INTERNAL_ERROR
```

- Typer/Click parsing errors use the documented usage-error behavior (`2`).
- Invalid configuration returns `3`.
- Unsupported Python/runtime health returns `4`.
- Unexpected exceptions return `10`.
- Commands must not call `sys.exit` from domain-independent helper functions.
- The CLI boundary (`cli.py`) translates exceptions into exit codes.

## 12. Error model

Minimal exception hierarchy:

```text
AgentHarnessError
ConfigurationError
AgentEnvironmentError
```

Requirements:

- Expected errors produce concise sanitized messages.
- Unexpected exceptions do not expose internals by default.
- Verbose mode may include diagnostic details.
- No error contains environment-variable dumps.
- Error handling must not swallow `KeyboardInterrupt`.

Decision note: configuration validation errors expose field names only and never raw input values.

## 13. Testing strategy

### Unit tests

Cover:

- Version source of truth.
- Default configuration.
- Environment-variable overrides.
- Rejection of `read_only=false`.
- Invalid log level.
- Text output.
- JSON output.
- Absence of ANSI in JSON.
- Exit-code constants.

### CLI integration tests

Cover:

```text
agent-harness --help
agent-harness version
agent-harness --output json version
agent-harness health
agent-harness --output json health
agent-harness config-check
agent-harness --output json config-check
invalid command
invalid output format
invalid configuration
read_only=false
```

Verify:

- Exit codes.
- stdout.
- stderr.
- JSON validity.
- No tracebacks for expected errors.
- No secret values.
- Module execution parity with console execution where practical.

Integration tests invoke the Typer application runner (e.g., `Typer`'s `CliRunner`) rather than spawning subprocesses, keeping tests fast and deterministic; where practical, one module-parity test compares `-m agent_harness` behavior.

## 14. Coverage gate

```text
Minimum line coverage: 90%
Minimum branch coverage: 80%
Changed-lines coverage: 100% for bootstrap source files where practical
```

Coverage percentage does not replace behavioral assertions. The implementation report must record actual results.

## 15. Developer workflow

Windows instructions (do not use bare `python`):

```bash
py -3.11 -m venv .venv
.venv\Scripts\python.exe -m pip install --upgrade pip
.venv\Scripts\python.exe -m pip install -e ".[dev]"
.venv\Scripts\python.exe -m pytest
```

Platform-neutral equivalents (do not assume the executable name):

```bash
python3.11 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -e ".[dev]"
.venv/bin/python -m pytest
```

## 16. Acceptance criteria

Phase 1 implementation is accepted only when:

- Python 3.11 compatibility is confirmed.
- Editable installation succeeds.
- Console entry point succeeds.
- Module entry point succeeds.
- All three commands satisfy their text and JSON contracts.
- Configuration is typed and safe.
- `read_only=false` is rejected.
- Expected errors use documented exit codes.
- Tests pass.
- Coverage gates pass.
- No network request occurs.
- No external tool is executed.
- No secret is logged.
- README reflects actual Phase 1 behavior only after implementation.
- No automatic Git mutation occurs.

## 17. Risks and decisions

| Risk | Mitigation |
|---|---|
| Typer global-option placement | Define `--output`, `--verbose`, `--no-color` on the application before subcommands; document the required order and test it. |
| Pydantic Settings environment parsing | Use `SettingsConfigDict(env_prefix="AGENT_HARNESS_", extra="ignore", env_file=None)`; test overrides explicitly. |
| Multiple version sources drifting | Single source of truth in `version.py`; package metadata reads from it; test that all entry points agree. |
| JSON output polluted by logging | Logging strictly to stderr; JSON written only to stdout; integration tests assert stdout parses as JSON. |
| Windows Python ambiguity | All instructions use `py -3.11`; never bare `python`; `.python-version` pins `3.11`. |
| Typer/Click exit-code behavior | Wrap command bodies so expected exceptions map to documented codes; treat Click usage errors as `2`. |
| Premature abstractions | Keep the output abstraction minimal; no generic framework beyond Phase 1 needs. |
| README getting ahead of implementation | README updated only after implementation; architecture task does not touch README. |

## 18. Explicitly deferred work

Phase 1 does not implement:

- Repository analysis.
- Git tooling.
- Search.
- OpenCode integration.
- Ticket workflows.
- Test execution against target repositories.
- Coverage parsing for target repositories.
- PR review.
- Worktrees.
- Sandbox.
- GitHub integration.
- RAG.

## Architecture decisions

1. `--output` is a global option on the Typer application and must appear before the subcommand.
2. Exact global-option syntax: `agent-harness --output json version`, `agent-harness --verbose health`, `agent-harness --no-color config-check`.
3. Version is stored in one internal source of truth (`src/agent_harness/version.py`); package metadata and CLI both read from it.
4. `read_only=false` is rejected with a sanitized `ConfigurationError`, exit code `3`.
5. Configuration is instantiated once at CLI startup and passed to commands, so health and config-check validate the same instance.
6. Errors cross from helpers via the `AgentHarnessError` hierarchy; `cli.py` translates them into exit codes. Helpers never call `sys.exit`.
7. JSON output stays clean because logging and diagnostics go to stderr and JSON is serialized only to stdout.
8. CLI tests use the Typer `CliRunner` (in-process) plus one module-parity test where practical.
9. Console and module entry points both call the same application function in `cli.py`; `__main__.py` is a thin wrapper.
10. Phase 1 avoids coupling later domain code to Typer by keeping command logic behind a thin CLI layer; domain helpers receive plain data, and only `cli.py` imports Typer.
