# AH-01-TST-01 — Independent CLI Bootstrap Quality Audit

## Status

PASS

## Timestamp

2026-08-14

## Repository identity

- Git root: `D:/agente-harness`
- Branch: `feature/ah-01-cli-bootstrap`
- HEAD: `3f421e4ad2b4a066941a94cef910a8694d5a1ee5`
- origin/main: `3f421e4ad2b4a066941a94cef910a8694d5a1ee5` (identical)

## Change inventory

Versus base commit `3f421e4`:

- Modified: `README.md` (authorized Phase 1 update).
- Added (untracked): `pyproject.toml`, `docs/PHASE_01_CLI_BOOTSTRAP_DESIGN.md`, `reports/AH-01-ARC-01.md`, `reports/AH-01-IMP-01.md`, `src/agent_harness/**` (9 files), `tests/**` (4 files).
- No Phase 0 document modified other than the README update.
- No `.env`, no lock file, no Dockerfile/workflow/yaml, no binary or unexpected executable.
- Generated artifacts (`__pycache__`, `.pytest_cache`, `*.egg-info`, `.coverage*`, `coverage.xml`, `.venv`) exist on disk but are ignored and absent from Git status.

## Independent environment

- QA Python: 3.11.9 (fresh `py -3.11 -m venv` at `C:\Users\agust\AppData\Local\Temp\opencode\ah01-qa\.venv`, outside the repository).
- pip: 26.2.1 after upgrade.
- Editable installation: `pip install -e "D:\agente-harness[dev]"` succeeded.
- pip check: "No broken requirements found."
- Console entry point present; `import agent_harness` reports version `0.1.0`.
- Temporary QA environment removed after audit.

## Dependency versions

- Direct runtime: typer 0.27.1, pydantic 2.13.4, pydantic-settings 2.15.0.
- Direct dev: pytest 9.1.1, pytest-cov 7.1.0.
- Transitive (allowed): python-dotenv 1.2.2 (pydantic-settings), rich 15.0.0 (typer), coverage 7.15.4 (pytest-cov).
- No prerelease requested; only lower bounds declared.

## Static architecture results

- Distribution `agent-harness-cli`, package `agent_harness`, requires-python `>=3.11`, version `0.1.0` from single source (`version.py`; pyproject uses dynamic attr).
- Console (`agent_harness.cli:main`) and module (`__main__.py` → `app`) route through the same Typer application.
- No `sys.exit` in helpers; only `cli.py` boundary translates errors to exit codes.
- No network, subprocess, Git, Docker, OpenCode, DeepSeek, or repository behavior in `src/`.
- `KeyboardInterrupt` re-raised (cli.py:68), not swallowed.
- Functional output to stdout; logging/errors to stderr.
- No global mutable state beyond the per-invocation `Invocation` (no cross-test contamination).
- Configuration instantiated once per invocation in the callback.

## Test counts

- Collected: 46; Passed: 46; Failed: 0; Skipped: 0; Warnings: 0.
- No test requires network, GitHub, Docker, OpenCode, credentials, or repository mutation (the only subprocess test invokes `sys.executable -m agent_harness`).

## Command matrix

| Command | Result | Exit | Evidence |
|---|---|---|---|
| `--help` | usage shown | 0 | console + module |
| `version` | `agent-harness 0.1.0` | 0 | exact |
| `--output json version` | valid JSON `command/status/version` | 0 | parsed |
| `health` | `status: healthy` / version / python 3.11.9 | 0 | exact |
| `--output json health` | valid JSON + `python_version` | 0 | parsed |
| `config-check` | `configuration: valid` | 0 | exact |
| `--output json config-check` | valid JSON | 0 | parsed |
| `python -m agent_harness --help/version` | parity | 0 | confirmed |

Console and module parity confirmed; only program name differs in help.

## Global options

- `--output text`, `--output json`, `--verbose`, `--no-color` all accepted before subcommands.
- Invalid `--output xml` → exit 2, sanitized error.
- `version --output json` (option after subcommand) → exit 2, "No such option" (consistent with design; options before subcommand only).
- JSON output contains no ANSI; `--verbose` JSON stdout remains a single valid document; stderr stayed empty for normal/verbose runs.

## Configuration matrix

- Defaults correct (`development`/`INFO`/`text`/`read_only=true`) with no `AGENT_HARNESS_*` vars.
- Overrides verified: `ENVIRONMENT=test`, `LOG_LEVEL=DEBUG`, `OUTPUT_FORMAT=json` (changes effective output), `READ_ONLY=true`.
- `READ_ONLY=false` → exit 3, sanitized `read_only cannot be disabled in Phase 1`.
- Invalid log level → exit 3, field identified.
- Invalid output format → exit 3, field identified.
- Invalid boolean → exit 3, field identified.
- No `.env` loaded; no persistent env change; no full environment dump.
- All scenarios process-scoped and restored.

## Exit-code results

- `0` success; `2` usage (invalid command, invalid option, option-after-subcommand); `3` configuration errors; unexpected internal error → `10` (covered by in-process test `test_unexpected_error_returns_internal`); unsupported-runtime `4` (covered by in-process test via `python_supported` boundary).
- Expected errors: no tracebacks, no success output on stdout, messages on stderr.

## Line and branch coverage

Independent in-process run (QA env):

- Line coverage: 96% (158 statements, 4 missed).
- Branch coverage: 30 branches, 1 partial (~96.7%).
- Gates: line ≥ 90% PASS, branch ≥ 80% PASS.

## Changed-lines calculation

All `src/agent_harness/**` files are new vs base; every executable line is a changed line.

- Changed executable lines: 158.
- Covered changed lines: 154.
- Uncovered changed lines: 4 (`__main__.py` lines 6-9, 3 lines; `cli.py:133`, 1 line).
- Changed-lines percentage: 97.5%.

`cli.py:133` classification: ENTRYPOINT_ONLY (module-only `if __name__ == "__main__":` guard). It is practically unreachable because executing `cli.py` directly fails on relative imports; module behavior is verified through subprocess execution (`-m agent_harness`) and `main()` is exercised by an in-process test. Disclosed numerically above.

`__main__.py` lines 6-9 classification: ENTRYPOINT_ONLY guard, behaviorally verified through subprocess module execution.

## README results

- Includes Phase 1 implemented status, Python 3.11 requirement, `py -3.11` instructions, editable install, all commands, global-option placement, text/JSON examples, test command, and limitations.
- Does not claim repository inspection, ticket implementation, target-repo tests, coverage parsing, PR review, OpenCode/DeepSeek integration, worktrees, sandbox, GitHub integration, or RAG are implemented.

## Security scan

- No API keys, tokens, passwords, private keys, authorization headers, connection strings, `.env`, or credential files found in tracked/untracked project files.
- No full environment dump in error output.
- Credential-like value test: a secret-shaped string placed in `AGENT_HARNESS_LOG_LEVEL` was reflected in the invalid-value error message (see findings; reported without reproducing the value).

## Findings

- LOW — `src/agent_harness/cli.py:133`: executable changed line uncovered in-process; entry-point-only guard, unreachable in practice (relative imports fail on direct script execution). Disclosed numerically; does not invalidate coverage gates (97.5% changed-lines, 96% line, ~96.7% branch).
- LOW — `src/agent_harness/config.py:29-30` (validator): the invalid `log_level` error echoes the raw rejected value (`invalid log_level '<value>'`). A credential-like string placed in that env var would be reflected in the error message. No secret field exists in Phase 1 and no stored secret is exposed; minor sanitation consideration.
- INFO — `errors.py` defines `EnvironmentError`, shadowing the builtin name (design-mandated hierarchy); no adverse effect observed.
- INFO — `python-dotenv` and `rich` present as transitive dependencies of approved packages; not scope violations.
- INFO — `--verbose` enables DEBUG logging but Phase 1 commands emit no log statements; stdout JSON remains valid.

## Git status

- Branch: `feature/ah-01-cli-bootstrap`
- Staged files: none
- Feature commits: none (HEAD == base == origin/main)
- Files changed by QA: `reports/AH-01-TST-01.md` (created only)
- Unexpected generated files: none in Git status
- Remote operations: none

## Commands executed

- `git rev-parse --show-toplevel`, `git branch --show-current`, `git rev-parse HEAD`, `git rev-parse origin/main`, `git status --short`, `git diff --cached --name-only`, `git diff --name-status 3f421e4`, `git log --oneline --decorate -3`
- `py -3.11 -m venv` (temp, outside repo), `pip install -e "D:\agente-harness[dev]"`, `pip check`
- `python -m pytest`, `python -m pytest --cov=agent_harness --cov-branch --cov-report=term-missing --cov-report=json:<temp>`
- Console and module command executions for all matrix cases with process-scoped env vars
- Static greps over `src/` and secret-pattern scans over project files

## Confirmation

Only `reports/AH-01-TST-01.md` was created or updated inside the repository. No source, test, dependency, architecture, Git history, remote reference, or GitHub resource was modified. The temporary QA environment and all coverage artifacts were created and removed outside the repository.
