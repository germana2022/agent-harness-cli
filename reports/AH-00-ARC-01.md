# AH-00-ARC-01 — Create Project Constitution and Architecture Baseline

## Status

COMPLETED

## Timestamp

2026-08-14

## Git root and branch

- Git root: `D:/agente-harness`
- Branch: `main`
- Origin: `https://github.com/germana2022/agent-harness-cli.git`
- Commit history: none

## Concept document recovery

- `documentation/mpv.md`: NOT_FOUND
- The file reported in AH-00-OPR-01 was no longer present in the working tree. No file was deleted or moved during this increment. The approved product vision was reconstructed from the AH-00-ARC-01 prompt.

## Files created

- `README.md`
- `.gitignore`
- `.python-version`
- `docs/PROJECT_CONSTITUTION.md`
- `docs/ARCHITECTURE.md`
- `docs/SECURITY_MODEL.md`
- `docs/ROADMAP.md`
- `docs/DEFINITION_OF_DONE.md`
- `docs/REPOSITORY_CONVENTIONS.md`
- `reports/AH-00-ARC-01.md`

Directories created: `docs/`, `reports/`, `errors/`. No files were created inside `errors/`.

## Files preserved

- No existing files required preservation. `documentation/mpv.md` was not present. No pre-existing file was overwritten or modified.

## Architecture decisions

- CLI-first, local-repository-first, read-only by default with explicit permission escalation.
- Domain layer depends on interfaces only; infrastructure implements domain contracts.
- Model provider is abstracted behind an interface; OpenCode-go with DeepSeek V4 Flash is the concrete route.
- Retrieval order prioritizes exact/structural evidence; vector RAG deferred.
- Operating modes: READ_ONLY, WORKSPACE_WRITE, DELIVERY with mandatory approval gates.
- Technology baseline: Python 3.11 (`py -3.11`), Typer, Pydantic, Pytest, ripgrep, Tree-sitter, Git, worktrees/Docker in later phases.
- LangGraph and vector databases deferred; no selection of Qdrant/Chroma/pgvector.

## Assumptions

- The local directory `D:\agente-harness` is the intended repository root; the directory name differs from the project name `agent-harness-cli` but is accepted per prior increments.
- The GitHub repository exists and is empty.
- Bare `python` resolves to Python 3.8 on the development machine; all instructions use `py -3.11`.

## Deferred functionality

- All application capabilities (Phases 1–18).
- Semantic retrieval, multi-repository analysis, GitHub write integration, worktree/sandbox execution, vector database selection, LangGraph orchestration.

## Validation performed

- Created files listed and confirmed: 10 files, no unexpected files.
- Internal Markdown links verified to resolve to existing files.
- README search for unsupported claims (`Supports`, `Executes`, `Implements`, `Provides`): no matches.
- `.python-version` contains exactly `3.11`.
- ROADMAP.md contains 19 phase headers, Phase 0 through Phase 18, in order.
- No `.env` file created; no `src/` or `tests/` directory created; `errors/` contains no files.
- `git diff --no-index NUL README.md` executed successfully as a read-back check.
- No files staged; no commit created.

## Warnings

- `documentation/mpv.md` remains missing. Verify it was not lost; the approved vision was reconstructed from the prompt.
- Security controls are documented as requirements, not implemented features.

## Git status

```text
?? .gitignore
?? .python-version
?? README.md
?? docs/
?? reports/
```

No files staged or committed.

## Confirmation

No application code was implemented. No file was staged or committed, and no local or remote Git history was changed.
