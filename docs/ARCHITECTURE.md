# Architecture Baseline

## 1. Context and retrieval strategy

Approved retrieval order:

```text
Repository metadata
→ exact file search
→ exact text search
→ symbol search
→ repository map
→ dependency relationships
→ Git history
→ selective context assembly
→ semantic retrieval when justified
```

Explicit constraints:

- Vector RAG is not part of the initial foundation.
- Semantic retrieval will initially target documentation, ADRs, issues, and historical PRs.
- Source-code analysis must prioritize exact and structural evidence.
- Context must be selected and budgeted rather than loading the entire repository.

## 2. High-level architecture

Logical components:

```text
CLI
Application use cases
Domain contracts
Repository inspector
Exact search
Safe file reader
Repository map
Git adapter
Context builder
Evidence validator
Model provider interface
OpenCode-go adapter
Policy engine
Approval manager
Worktree manager
Sandbox runtime
Command runner
Test runner
Coverage analyzer
Diff and PR reviewer
Trajectory recorder
Report generator
Evaluation harness
```

Dependency direction:

```text
CLI
→ Application
→ Domain

Infrastructure
→ Domain interfaces
```

The domain layer must not depend directly on:

- Typer.
- OpenCode.
- DeepSeek.
- GitHub.
- Docker.
- LangGraph.
- Qdrant.
- Any concrete provider.

## 3. Component responsibilities

| Component | Responsibility |
|---|---|
| CLI | Parse commands, present results, enforce mode transitions. |
| Application use cases | Orchestrate workflows (analyze, refine ticket, implement, validate). |
| Domain contracts | Interfaces and domain models shared by use cases and infrastructure. |
| Repository inspector | Discover repository structure and metadata. |
| Exact search | Run exact file and text search (ripgrep). |
| Safe file reader | Read allowed files with size/type constraints. |
| Repository map | Build a structural map of the repository. |
| Git adapter | Read Git history, diffs, and status without mutation. |
| Context builder | Select and budget context for the model. |
| Evidence validator | Validate evidence claims against tool results. |
| Model provider interface | Abstraction over reasoning/coding models. |
| OpenCode-go adapter | Concrete adapter to OpenCode-go with DeepSeek V4 Flash. |
| Policy engine | Enforce operating modes and tool allowlists. |
| Approval manager | Track and record human approvals. |
| Worktree manager | Create and manage isolated worktrees. |
| Sandbox runtime | Run commands in an isolated sandbox. |
| Command runner | Execute allowlisted commands with limits. |
| Test runner | Run tests and collect structured output. |
| Coverage analyzer | Analyze coverage, including changed-lines coverage. |
| Diff and PR reviewer | Review local diff and (later) Pull Requests. |
| Trajectory recorder | Record auditable execution trajectories. |
| Report generator | Produce Markdown and JSON reports. |
| Evaluation harness | Benchmarks and evaluation of read-only behavior. |

## 4. Layering rules

- `CLI → Application → Domain`
- `Infrastructure → Domain interfaces`
- Domain defines contracts; infrastructure implements them.
- The model provider is behind an interface; OpenCode-go is one concrete adapter.
- Frameworks (Typer, Pydantic, Pytest, ripgrep, Tree-sitter) are introduced only when justified and versioned with the repository.

## 5. Data flow (planned)

1. CLI receives a command in a specific operating mode.
2. Application use case enforces mode and approval gates.
3. Read-only tools inspect the repository, search exactly, and build a repository map.
4. Context builder selects and budgets evidence for the model.
5. Model provider interface produces analysis through the OpenCode-go adapter.
6. Evidence validator checks conclusions against tool results.
7. Trajectory recorder logs steps and evidence.
8. Report generator emits Markdown and JSON reports.

## 6. Isolation model (planned)

- Code modification happens only inside an isolated worktree.
- Command execution happens only inside a sandbox.
- Worktree and sandbox management are separate logical components, introduced in later phases.

## 7. Model provider abstraction

- Domain defines a model-provider interface.
- OpenCode-go with DeepSeek V4 Flash is the primary concrete route.
- No domain code may import OpenCode, DeepSeek, or a provider SDK directly.

## 8. Deferred functionality

- Vector RAG and semantic retrieval over source code.
- Multi-repository analysis.
- Autonomous implementation.
- CI/CD integration.
- Qdrant, Chroma, or pgvector selection.
- LangGraph orchestration.
