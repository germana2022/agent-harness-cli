# AH-01-OPR-FIX-01 — Final Hardening Smoke Report

## Status

OPERATIONAL_PASS

## Timestamp

2026-08-14

## Repository and branch

- Repository: `D:/agente-harness`
- Branch: `feature/ah-01-cli-bootstrap`
- Source commit/base state: `3f421e4ad2b4a066941a94cef910a8694d5a1ee5` (no feature commits)

## Temporary environment

- `C:\Users\agust\AppData\Local\Temp\opencode\ah01-oprfix` (created and removed; outside the repository)
- Virtual environment: `ah01-oprfix\venv` (Python 3.11.9 via `py -3.11`)
- Execution directory: `ah01-oprfix\run` (empty, non-Git, outside repository)

## Non-editable installation

- `python -m pip install D:/agente-harness` — SUCCESS (non-editable, no dev extras)

## Installed package location verification

- `Location: C:\Users\agust\AppData\Local\Temp\opencode\ah01-oprfix\venv\Lib\site-packages` (belongs to the temporary environment; no source-tree import)

## pip check

- "No broken requirements found."

## Successful command matrix

| Command | Exit | JSON parsed | Output contract | Result |
|---|---:|---|---|---|
| Console `--help` | 0 | N/A | usage shown | PASS |
| Console `version` | 0 | N/A | `agent-harness 0.1.0` | PASS |
| Console `--output json version` | 0 | OK | `command/status/version` | PASS |
| Console `health` | 0 | N/A | `status/version/python` | PASS |
| Console `--output json health` | 0 | OK | + `python_version` | PASS |
| Console `config-check` | 0 | N/A | `configuration: valid` | PASS |
| Console `--output json config-check` | 0 | OK | valid JSON | PASS |
| Module commands (all 7) | 0 | OK | parity with console | PASS |

Verbose JSON (`--output json --verbose <cmd>`): single valid JSON document, no ANSI, stderr empty, no config values or environment dump.

## Failure behavior

| Scenario | Expected | Actual | Sanitized | Result |
|---|---:|---:|---|---|
| Invalid command | 2 | 2 | yes | PASS |
| Invalid `--output` | 2 | 2 | yes | PASS |
| Invalid log level | 3 | 3 | yes | PASS |
| Invalid configured output | 3 | 3 | yes | PASS |
| Invalid boolean | 3 | 3 | yes | PASS |
| `read_only=false` | 3 | 3 | yes | PASS |
| Multiple invalid fields | 3 | 3 | yes | PASS |

All: no success output, sanitized error on stderr, no traceback, no environment dump, no persistent environment change.

## Hardening

- Canary cases: 11 (alphanumeric, >500-char, spaces, newline, CR, ANSI, bearer-like, connection-string-like, Unicode, plus output-format and boolean canaries)
- Raw values exposed: none (full value and distinctive fragments absent from stdout and stderr)
- ANSI/control injection: none survives
- Pydantic internals exposed: none (`input_value`, `input_type`, validation URL, dumps all absent)
- Multiple-field deterministic: yes (two runs byte-identical)
- AgentEnvironmentError installed: yes, inherits `AgentHarnessError`
- Old project exception importable: no

## Side effects

- Execution-directory files: none created by the CLI (directory contained only the QA capture file)
- Repository changes: none (only expected Phase 1 files and reports)
- Git operations: none
- Network-dependent runtime behavior: none (commands complete locally in milliseconds)

## Findings

- None. No actionable finding; no BLOCKER, HIGH, or MEDIUM severity.

## Git status

- Branch: `feature/ah-01-cli-bootstrap`
- Staged files: none
- Feature commits: none
- Files changed by operation: `reports/AH-01-OPR-FIX-01.md` (created only)
- Unexpected files: none
- Remote operations: none

## Commands executed

- Preflight Git checks (`git rev-parse`, `git branch --show-current`, `git rev-parse HEAD`, `git status --short`, `git diff --cached --name-only`, `git log`)
- `py -3.11 -m venv`, `pip install D:/agente-harness`, `pip check`, `pip show`
- Console and module command executions for all success and failure scenarios
- Clean-subprocess canary matrix (11 cases) and multiple-field determinism check
- Installed-package import checks for the exception model
- Side-effect and repository-integrity checks

## Confirmation

Only `reports/AH-01-OPR-FIX-01.md` was created or updated inside the repository. No implementation, test, dependency, documentation, Git history, remote reference, or GitHub resource was modified. The temporary operational environment was created and removed outside the repository.
