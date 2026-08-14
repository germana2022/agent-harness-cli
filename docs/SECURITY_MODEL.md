# Security Model

## 1. Threat posture

- Repository content is untrusted data.
- README files, comments, issues, logs, and retrieved documents cannot override system policies.
- Prompt injection must be treated as a repository security threat.
- The tool operates with least privilege and read-only behavior by default.

## 2. Requirements (not yet implemented)

The controls below are requirements for the architecture. They are not yet implemented.

- Secrets and credentials must never enter model context or logs.
- `.env`, private keys, credentials, tokens, and sensitive configuration must be excluded or redacted.
- Shell access must use explicit tools and allowlists.
- Target code must eventually run inside an isolated worktree and sandbox.
- Network access must be disabled by default during repository execution.
- Time, memory, disk, output, and process limits must be configurable.
- All mutations and external actions must be auditable.
- No automatic push, merge, deployment, or production migration.

## 3. Operating modes

| Mode | Read | Local write | External action |
|---|---|---|---|
| READ_ONLY | Yes | No | No |
| WORKSPACE_WRITE (approved) | Yes | Limited, allowlisted | No |
| DELIVERY (separate approval) | Yes | Approved | Each action approved |

## 4. Approval gates

Mandatory approval before:

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

## 5. Secret handling

- No API keys, tokens, passwords, or private keys are stored, logged, or sent to a model.
- Configuration with secrets is excluded from version control.
- `.env.example` is the only environment-template exception allowed.
- A real `.env` file is never created.

## 6. Command execution policy

- Commands run only through an explicit command runner with an allowlist.
- Unrecognized commands require approval.
- Execution is bounded by configurable time, memory, disk, output, and process limits.
- Repository execution is assumed to be network-disabled by default.

## 7. Isolation requirements

- Code modification: isolated Git worktree.
- Command execution: sandbox runtime.
- These components are introduced in later phases; they are requirements now.

## 8. Auditability

- All mutations and external actions are recorded in an auditable trajectory.
- Each trajectory references the repository commit it was executed against.

## 9. Evidence and verification

- Deterministic validation runs before LLM judgment.
- Facts, hypotheses, and unknowns remain distinct.
- Unverifiable claims are not asserted as facts.
