# Repository Conventions

## 1. Branches

```text
main
feature/ah-<phase>-<description>
fix/ah-<phase>-<description>
```

- `main` is the integration branch.
- Feature branches follow `feature/ah-<phase>-<description>`.
- Fix branches follow `fix/ah-<phase>-<description>`.

## 2. Prompt IDs

```text
AH-[PHASE]-[ROLE]-[SEQUENCE]
AH-[PHASE]-IMP-FIX-[SEQUENCE]
```

Roles:

```text
ARC — Architect
IMP — Implementer
TST — Tester
OPR — Operator
SEC — Security Reviewer
```

`AH-[PHASE]-IMP-FIX-[SEQUENCE]` identifies implementer fix increments.

## 3. Reports

Reports are stored as:

```text
reports/AH-<ID>.md
```

## 4. Errors

Errors are stored as:

```text
errors/AH-<ID>-error.md
```

## 5. Development cycle

```text
Architecture
→ Implementation
→ Testing
→ Security review when applicable
→ Operational validation
→ Fix if required
→ Gate approval
→ Commit
→ Next increment
```

## 6. Commit convention

Commits follow the Conventional Commits style. Examples:

```text
docs: add project constitution and architecture baseline
feat(cli): add command skeleton
fix(search): constrain file reading by size
test(inspection): cover repository inspector boundaries
chore: update tooling configuration
```

Conventions are documented here; no commit is created by documentation increments.

## 7. Directory layout

```text
docs/       Documentation
reports/    Increment reports
errors/     Error records
```

`src/` and `tests/` will be introduced by implementation increments.

## 8. Tooling and environment

- Python 3.11 minimum, invoked with `py -3.11` on Windows.
- Bare `python` resolves to Python 3.8 on the development machine and must not be used.
- `.python-version` pins `3.11`.
