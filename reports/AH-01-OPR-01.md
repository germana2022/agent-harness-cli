# AH-01-OPR-01 — Production-Like CLI Smoke Validation

## Status

OPERATIONAL_HARDENING_REQUIRED

## Timestamp

2026-08-14

## Repository and branch

- Repository: `D:/agente-harness`
- Branch: `feature/ah-01-cli-bootstrap`
- Source commit/base state: `3f421e4ad2b4a066941a94cef910a8694d5a1ee5` (no feature commits; working tree = Phase 1 changes from QA)

## Temporary environment path

- `C:\Users\agust\AppData\Local\Temp\opencode\ah01-opr` (created and removed after validation)
- Virtual environment: `ah01-opr\venv`
- Execution directory: `ah01-opr\run` (empty, non-Git, outside repository, no application configuration)

## Python version

- 3.11.9 (`py -3.11 -m venv`)

## Non-editable installation result

- `python -m pip install D:/agente-harness` — SUCCESS
- Style: standard non-editable install (package located in `venv\Lib\site-packages`)

## pip check result

- "No broken requirements found."

## Installed package metadata

- Name: `agent-harness-cli`, Version: `0.1.0`
- Requires: `pydantic`, `pydantic-settings`, `typer`
- Runtime deps only; no dev extra installed (pytest not present, not required)

## Command matrix

| Command | Exit | stdout | stderr | Result |
|---|---:|---|---|---|
| `agent-harness --help` | 0 | usage help | empty | PASS |
| `agent-harness version` | 0 | `agent-harness 0.1.0` | empty | PASS |
| `agent-harness --output json version` | 0 | valid JSON | empty | PASS |
| `agent-harness health` | 0 | status/version/python | empty | PASS |
| `agent-harness --output json health` | 0 | valid JSON | empty | PASS |
| `agent-harness config-check` | 0 | `configuration: valid` | empty | PASS |
| `agent-harness --output json config-check` | 0 | valid JSON | empty | PASS |

Durations: 588–941 ms per command (no network or external-tool delay).

## Exit codes

- All success cases: 0.
- Failure cases below: exact expected codes.

## stdout/stderr validation

- Functional output on stdout only; stderr empty for all success cases.
- Errors reported on stderr; no success output on stdout for failures.
- No tracebacks for expected errors.

## JSON parser results

- All JSON commands parse with the standard-library JSON parser (`ConvertFrom-Json`).
- Stable fields: `command`, `status`, plus `version` / `python_version` / `configuration` as designed.
- No ANSI escape sequences.
- No logging prefixes.
- No extra nondeterministic fields (timestamps, paths, tokens, machine IDs).

## Verbose validation

- `--verbose --output json <command>`: stdout remains a single valid JSON document; stderr empty.

## Determinism results

- `version`, `--output json version`, `config-check`, `--output json config-check` executed twice: outputs identical across runs.

## Runtime independence

- All commands executed successfully from an empty, non-Git temporary directory outside the repository.
- Source inspection (per QA) shows no subprocess, network, Git, Docker, OpenCode, DeepSeek, or repository code in `src/`.
- No related errors or delays observed.

## Filesystem-side-effect check

- Execution directory was empty (0 files) before commands; after commands it contained only the QA capture files (`out_*.txt`, `err_tmp.txt`, `canary_*.txt`).
- The CLI created no configuration, logs, cache, reports, `.env`, database, telemetry, or hidden project files in the working directory.

## Raw invalid-value disclosure classification

- RAW_VALUE_ECHOED.
- A process-scoped synthetic canary value (`[REDACTED_CANARY]`) placed in `AGENT_HARNESS_LOG_LEVEL` was reproduced verbatim in the configuration-error message on stderr.
- The canary was never written to a file and was removed from the process after the test; it is not reproduced in this report.

## Maintainability observation

- Confirmed: `src/agent_harness/errors.py:18` defines `class EnvironmentError(AgentHarnessError)`, overlapping the Python built-in alias.
- Recommended future name: `RuntimeEnvironmentError` or `AgentEnvironmentError`.
- Non-operational; may be included in a hardening fix.

## Findings

- LOW — Raw invalid configuration value disclosure (`config.py` log-level validator): `[REDACTED_CANARY]` echoed verbatim in the error message. The field is not secret, but arbitrary environment values should not be unnecessarily reproduced. Recommended hardening: reject `log_level` with a message that names the field without echoing the raw value (or echo a redacted representation).
- LOW — `errors.py:18` custom `EnvironmentError` shadows the Python built-in alias (maintainability; no runtime failure observed).
- INFO — `cli.py:133` entry-point-only coverage exception, behaviorally verified through module execution (previously documented in QA).

## Git status

- Branch: `feature/ah-01-cli-bootstrap`
- Staged files: none
- Feature commits: none
- Files changed by operation: `reports/AH-01-OPR-01.md` (created only)
- Remote operations: none
- Non-editable build artifacts (`build/`, `*.egg-info`) are gitignored and do not appear in Git status.

## Confirmation

Only `reports/AH-01-OPR-01.md` was created or updated inside the repository. No source, test, dependency, documentation, Git history, remote reference, or GitHub resource was modified. The temporary operational environment was created and removed outside the repository.
