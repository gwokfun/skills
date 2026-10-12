<!-- matt-skills:codex-workflow:begin version=1 -->
# Codex engineering workflow

Review input: workspace snapshot

## Stages

`grill-with-docs -> to-spec -> to-tickets -> implement -> code-review`

The user starts the first four user-only skills explicitly. Initialization sets their working conventions; it never invokes them or builds an automatic execution engine.

| Stage | Root responsibility | Handoff |
| --- | --- | --- |
| grill-with-docs | Interview, resolve terminology and decisions; use explorer/researcher for bounded evidence | Agreed scope, glossary and ADRs |
| to-spec | Synthesize the conversation and confirm test seams; architect A before a large Execution Plan involving multiple modules | Published spec and acceptance criteria |
| to-tickets | Produce complete vertical slices, obtain approval, publish blockers-first | Self-contained tickets and blocking edges |
| implement | Start fresh per ticket; root implements, worker gets only explicit nonoverlapping ownership | Verified task changes and a frozen review snapshot |
| code-review | Check Standards and Spec independently and verify findings; architect C before long-task completion | Review evidence matching final task content |

Keep the first three stages in the same conversation until tickets exist. Start each implementation from its ticket and spec; use the configured tracker and existing `.scratch/<feature>/` convention for local work. Preserve `implement`'s built-in model-invoked `code-review` and existing commit authority. An additional user-invoked review in a fresh chat can cover the whole feature.

Do not default to `implement-spec`: its parallel worktrees and integration lifecycle require a separate explicit choice and a policy compatible with this project's role restrictions.

## Before implementation

Record the immutable baseline commit SHA, spec/ticket references, blocking edges, initial user changes, and task ownership in a tracker note or local feature handoff. Reuse an existing handoff instead of introducing another state engine. Do not start a blocked ticket. Record a separate feature baseline when an overall review is planned.

The user must supply or explicitly agree the review baseline; pin it before changes. Do not guess `HEAD~1` at close-out. If a baseline is missing, obtain it before invoking review.

## Workspace review contract

Use the installed `code-review` skill's workspace snapshot branch. Select explicit task file paths and capture one baseline-to-current snapshot containing committed, staged, unstaged, deleted, and selected untracked task changes. Both Standards and Spec read that same snapshot and frozen file content. Use two Fresh `explorer` agents for those read-only checks, with no nested delegation. Architect C is a separate check.

List included paths and identify unrelated or ignored changes excluded from review. In a file containing prior user edits, verify hunk ownership before claiming or committing the file. If task and prior edits cannot be separated reliably, report the unresolved ownership and leave automatic commit pending. A file allowlist alone does not establish hunk ownership.

The snapshot records its base SHA, content hashes, file modes, and snapshot identity. Any later task edit invalidates the affected review evidence. Regenerate and recheck after fixes. Match staged task content to the reviewed snapshot before committing, and check delivered task content again afterward. Reconcile the task's final file list with the snapshot; a newly introduced task file must not enter the commit unreviewed. Preserve unrelated staged user changes rather than unstaging them to make a check pass.

## Completion

Record commands/checks actually run and their results. Rule B applies literally to every test failure, including expected RED; do not silently exempt it. Check actionable review findings against the real files and spec. Before a long task is Finished, invoke architect C against the resulting final Diff and relevant verification evidence; resolve verified issues and repeat affected checks.

Reconcile acceptance criteria and ticket status through the configured tracker within existing authorization. `implement` does not itself close tickets, so record closure separately before treating dependent tickets as unblocked. Preserve the scope of authorization for commits, pushes, PRs, and external tracker changes.
<!-- matt-skills:codex-workflow:end -->
