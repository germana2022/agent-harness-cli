# Definition of Done

## 1. Purpose

A change is complete only when it satisfies the checks below with appropriate evidence. Individual increments may mark nonapplicable checks as `N/A`, but must explain why.

## 2. Checks

| # | Check | Evidence required |
|---|---|---|
| 1 | Scope compliance | Change matches the ticket/increment scope; no invented requirements. |
| 2 | Design review | Architecture and design decisions are recorded and reviewed when applicable. |
| 3 | Implementation | Code is implemented according to repository conventions. |
| 4 | Unit tests | Relevant unit tests exist and pass. |
| 5 | Integration tests (when applicable) | Integration tests exist and pass, or `N/A` with justification. |
| 6 | Static validation | Lint, format, and static checks pass. |
| 7 | Build | The project builds successfully. |
| 8 | Coverage | Coverage is evaluated and reported. |
| 9 | Changed-lines coverage | Changed-lines coverage is evaluated as a primary signal. |
| 10 | Security considerations | Security impact is considered; secrets are never exposed. |
| 11 | Evidence | Facts, hypotheses, and unknowns are distinct and evidence-backed. |
| 12 | Documentation | User and design documentation is updated as required. |
| 13 | Reproducibility | Results are reproducible against a specific commit. |
| 14 | No invented files or symbols | All referenced files and symbols are real and verifiable. |
| 15 | Human approval | Required approvals are obtained and recorded. |
| 16 | Git status | Working tree is clean or documented; only intended files changed. |
| 17 | Required reports | Implementation and QA reports exist for the increment. |

## 3. Application

- `N/A` marks a check as not applicable for the increment.
- Every `N/A` requires a one-line justification.
- Completion requires passing the applicable checks with recorded evidence.

## 4. Operating context

- Read-only analysis never requires the implementation checks.
- Write-enabled increments require implementation, test, coverage, and build checks.
- External actions additionally require per-action approval.
