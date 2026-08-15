# AH-01-TST-FIX-01 — Hardening QA Report

## Status

PASS

## Timestamp

2026-08-14

## Repository and branch

- Git root: `D:/agente-harness`
- Branch: `feature/ah-01-cli-bootstrap`
- Base commit: `3f421e4ad2b4a066941a94cef910a8694d5a1ee5`
- Feature commits: none
- Staged files: none

## Fix-scope validation

- Fix modified only the authorized active files: `src/agent_harness/config.py`, `src/agent_harness/errors.py`, `src/agent_harness/cli.py`, `tests/unit/test_config.py`, `tests/integration/test_cli.py`, `docs/PHASE_01_CLI_BOOTSTRAP_DESIGN.md`, plus `reports/AH-01-IMP-FIX-01.md`.
- No new dependency (`pyproject.toml` dependency set unchanged).
- No unrelated refactor; no successful-output contract change.
- No Phase 0 document or historical report modified.

## Independent environment

- QA Python: 3.11.9 (fresh `py -3.11 -m venv` outside the repository, removed after audit).
- Non-editable install of `D:/agente-harness` succeeded; `pip check` clean.
- Dependency set unchanged (typer, pydantic, pydantic-settings, pytest, pytest-cov + approved transitives).

## Installation result

- Standard non-editable install: SUCCESS.
- Console entry point present; module entry point works.

## Test and coverage results

- Collected: 57; Passed: 57; Failed: 0; Skipped: 0; Warnings: 0.
- Line coverage: 97% (169 statements, 4 missed).
- Branch coverage: ~97.2% (36 branches, 1 partial).
- Coverage gate: PASS (line >= 90%, branch >= 80%).
- Newly changed sanitization branches (`errors.py`) at 100% coverage, meaningfully exercised by the regression tests.
- Coverage measured against the installed package (site-packages), not the source tree.

## Successful-command regression

- `version`, `--output json version`, `health`, `--output json health`, `config-check`, `--output json config-check`: all exact expected output, exit 0, valid JSON, no ANSI, no stderr pollution.
- Module parity (`python -m agent_harness version` / `config-check`) confirmed.

## Sanitization matrix

13 fresh synthetic canary scenarios across `AGENT_HARNESS_LOG_LEVEL`, `AGENT_HARNESS_OUTPUT_FORMAT`, `AGENT_HARNESS_READ_ONLY` covering: alphanumeric canary, >500-char value, spaces, newline, carriage return, ANSI escape, bearer-token-like, connection-string-like, invalid boolean, and multiple-invalid-fields.

All cases (via clean subprocess capture):

- Exit code `3`.
- Empty stdout (no success result).
- Full raw value absent from stdout and stderr.
- Distinctive canary fragments absent (the only "fragment present" case was `output` matching the legitimate field name `output_format`, a substring, not a disclosure).
- No ESC/ANSI byte survives.
- No `input_value`, `input_type`, Pydantic validation URL, validation dump, traceback, or environment dump.
- Field names preserved safely.

## Multiple-field behavior

- `AGENT_HARNESS_OUTPUT_FORMAT=xml` + `AGENT_HARNESS_READ_ONLY=maybe` → `error: invalid configuration fields: output_format, read_only`, exit 3, plural wording, each field once, deterministic ordering, no raw values.
- Two clean subprocess runs produced identical stdout and stderr.

## Read-only policy

- `AGENT_HARNESS_READ_ONLY=false` → exit `3`, safe reference to `read_only`, value `false` not reproduced, no write mode enabled, no file created, environment variable not persisted.

## Exception rename

- `AgentEnvironmentError` exists, inherits from `AgentHarnessError` (verified by unit test).
- Active source imports and references use the new name (`errors.py`, `cli.py`).
- Active tests and design documentation use the new name.
- No compatibility alias named `EnvironmentError` remains (verified via word-boundary-aware search; only an intentional negative test assertion and historical reports remain).
- Exit-code behavior preserved: environment mapping returns `4` (verified by `test_render_environment_error_maps_to_exit_4`).

## Security scan

- No real secrets, tokens, passwords, private keys, authorization headers, connection strings, raw test canaries in reports, environment dumps, or validation outputs found in changed source, tests, design doc, or new report.
- INFO — `tests/unit/test_config.py` lines 167/172 contain a deliberate synthetic fixture string used to assert the value is NOT echoed; it is a non-secret test value, not persisted in reports.

## Findings

- None actionable. No BLOCKER, HIGH, or MEDIUM finding.
- INFO — Historical reports `AH-01-TST-01.md` and `AH-01-OPR-01.md` still mention the old `EnvironmentError` name (preserved evidence, not edited).
- INFO — Entry-point-only coverage exception (`cli.py:133`, `__main__.py` guard) remains, behaviorally verified via module execution.
- INFO — Synthetic test fixture string in `test_config.py` (intentional non-echo assertion).

## Git integrity

- Branch: `feature/ah-01-cli-bootstrap`
- Staged files: none
- Feature commits: none
- Files changed by QA: `reports/AH-01-TST-FIX-01.md` (created only)
- Unexpected files: none; no temporary QA artifacts inside the repository
- Remote operations: none

## Commands executed

- `git rev-parse --show-toplevel`, `git branch --show-current`, `git rev-parse HEAD`, `git status --short`, `git diff --cached --name-only`, `git log --oneline --decorate -3`
- `py -3.11 -m venv` (temp, outside repo), `pip install D:/agente-harness`, `pip install "D:/agente-harness[dev]"`, `pip check`
- `python -m pytest`, `python -m pytest --cov=agent_harness --cov-branch --cov-report=term-missing --cov-report=json:<temp>`
- Console and module command executions for successful-command regression
- Clean subprocess-based sanitization matrix (13 cases) and multiple-field determinism check
- Static greps over `src/`, `tests/`, `docs/` for old exception name, sanitization patterns, prohibited behaviors, and secret patterns

## Confirmation

Only `reports/AH-01-TST-FIX-01.md` was created or updated inside the repository. No implementation, test, dependency, design, Git history, remote reference, or GitHub resource was modified.
