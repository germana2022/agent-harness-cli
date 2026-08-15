# AH-01-IMP-FIX-01 — Hardening Fix Report

## Status

COMPLETED

## Timestamp

2026-08-14

## Repository and branch

- Repository: `D:/agente-harness`
- Branch: `feature/ah-01-cli-bootstrap`
- Base commit: `3f421e4ad2b4a066941a94cef910a8694d5a1ee5`

## Verified findings

1. Raw invalid-value disclosure: a synthetic value in `AGENT_HARNESS_LOG_LEVEL` was reproduced verbatim in the configuration error.
2. Exception-name overlap: project-defined `EnvironmentError` overlapped the Python built-in alias.

## Files modified

- `src/agent_harness/errors.py` — renamed exception, replaced ValidationError message formatting with field-name-only sanitization, added control-character stripping.
- `src/agent_harness/config.py` — log-level validator message no longer echoes the raw value.
- `src/agent_harness/cli.py` — import and mapping updated to `AgentEnvironmentError`.
- `tests/unit/test_config.py` — updated sanitization tests; added regression tests for canary, long, newline, ANSI, multiple fields, control-character stripping, exception rename.
- `tests/integration/test_cli.py` — updated exception reference; added sanitization assertions and multiple-invalid-field and ANSI-injection scenarios.
- `docs/PHASE_01_CLI_BOOTSTRAP_DESIGN.md` — exception model updated to `AgentEnvironmentError`; added decision note.

## Files created

- `reports/AH-01-IMP-FIX-01.md`

## Sanitization strategy

- Pydantic `ValidationError` handling reads only structured `.errors()` locations, derives safe field names (control characters and ANSI stripped via regex `[\x00-\x1f\x7f]`), and returns either `invalid configuration field: <name>`, `invalid configuration fields: <a>, <b>` (unique, deterministically sorted), or `invalid configuration` when no safe location exists.
- Raw input values, `input_value`, `input_type`, complete Pydantic representations, validation URLs, and environment contents are never included.
- The log-level validator raises `ConfigurationError` naming only the field (`invalid log_level: must be one of ...`), without echoing the value.
- Exit code `3` preserved for all configuration errors.

## Safe field output

- Single field: `invalid configuration field: output_format`.
- Multiple fields: `invalid configuration fields: output_format, read_only`.
- Fallback: `invalid configuration`.

## Raw values exposed

- None. Confirmed for invalid log level, output format, boolean, `read_only=false`, multiple fields, and a credential-like canary.

## ANSI/control characters

- Control characters stripped from field-derived text; no ESC byte or ANSI sequence survives in error output (verified with `AGENT_HARNESS_OUTPUT_FORMAT="\x1b[31mxml\x1b[0m"`).

## read_only=false

- Still rejected with exit code `3`, identifies `read_only`, and does not reproduce the value `false`.

## Multiple invalid fields

- `AGENT_HARNESS_OUTPUT_FORMAT=xml` + `AGENT_HARNESS_READ_ONLY=maybe` → exit `3`, message `invalid configuration fields: output_format, read_only`, no raw values.

## Exception rename

- Old name: `EnvironmentError`
- New name: `AgentEnvironmentError`
- Source references remaining: none (only the intentional negative assertion in tests verifying the old name is absent).
- Historical references remaining: `reports/AH-01-TST-01.md`, `reports/AH-01-OPR-01.md` (preserved as recorded at the time; not edited).
- Exit-code behavior: environment mapping still returns exit code `4` (verified by `test_render_environment_error_maps_to_exit_4`).

## Tests

- Total: 57
- Passed: 57
- Failed: 0
- Line coverage: 97% (169 statements, 4 missed; only entry-point-only guards remain uncovered)
- Branch coverage: ~97.2% (36 branches, 1 partial)
- Coverage gate: PASS (line >= 90%, branch >= 80%)
- Successful-command regression: all six commands (version, JSON version, health, JSON health, config-check, JSON config-check) return exact expected output and exit 0.

## Security validation

- Synthetic canary: `[REDACTED_CANARY]` (newly generated, process-scoped, not stored in any file).
- stdout disclosure: none (stdout empty).
- stderr disclosure: none (canary absent from stderr).
- Traceback: none for expected configuration errors.
- Environment dump: none.

## Remaining references to old exception name

- Only historical reports `AH-01-TST-01.md` and `AH-01-OPR-01.md`, preserved unchanged.

## Known limitations

- `cli.py:133` and `__main__.py` entry-point-only guards remain uncovered in-process (documented, behaviorally verified via module execution).
- No dependency added; no successful-output contract changed.

## Git status

- Branch: `feature/ah-01-cli-bootstrap`
- Staged files: none
- Feature commits: none
- Remote operations: none
- Changes: `README.md` (Phase 1 update from implementation), plus untracked Phase 1 sources, tests, design doc, and reports.

## Confirmation

Only the authorized hardening files and fix report were modified. No dependency, unrelated feature, Git history, remote reference, or GitHub resource was changed.
