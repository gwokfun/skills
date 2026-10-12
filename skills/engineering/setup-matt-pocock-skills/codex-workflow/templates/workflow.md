<!-- matt-skills:codex-workflow:begin version=2 -->
# Codex engineering workflow

Review input: workspace snapshot
Project spec maintenance: disabled

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

## Optional project specification maintenance

This section applies only when the exact setting above is `Project spec maintenance: enabled`. Disabled or absent means the standard flow continues without this helper. Installation alone does not enable it. An enabled project must have this fork's independently installed, model-invoked `project-specs` skill and its resources available; report a missing helper and pause the affected handoff/review instead of silently skipping maintenance. Do not install or alter configuration as a fallback.

Read relevant current `docs/specs/<capability-id>.md` before grilling or planning. Reuse stable change, capability and ticket IDs from the handoff. Keep full published content under tracked `docs/changes/<change-id>/`; the tracker remains authoritative for live task status. Never call a local content snapshot a live issue mirror.

- After `to-spec` actually publishes, call the Skill tool with `project-specs` to capture the complete published spec and known source reference. Record its actual version, observation time and approval basis; seam confirmation alone is not final-body approval. On a local tracker capture the saved source file.
- After `to-tickets` publishes the approved breakdown, call the Skill tool with `project-specs` to capture each known ticket. If publication is partial, preserve known IDs and resume local captures; do not recreate issues. Stop on truncated or unavailable source bodies.
- Inside `implement`, after actual behavior verification and BEFORE its internal `code-review` and commit, call the Skill tool with `project-specs` to reconcile the verified capability body and record checks, deviations, implementation hashes and expected document version. Run its `check` command. Then include all returned documentation paths in the task scope and frozen review snapshot, perform `code-review`, and commit only within existing authority. Do not postpone reconciliation until after `implement` returns.
- After any behavior-changing review fix, reverify, call `project-specs` with a new update ID, check again and regenerate the review snapshot. Never reuse a pass for changed implementation files or docs. Before accepting review, recheck source snapshots against complete current source bodies where necessary; source drift requires an explicit revision decision, not reverse writes to the tracker.

Assign one integration session to each shared capability file. Other ticket sessions and workers produce scoped proposed deltas for that owner to merge serially. Check the expected whole-file digest before writing; concurrent edits require rereading, reconciliation and review. Preserve user edits. Immutable history and new approved revisions keep the original decisions available. The helper records evidence but does not prove that checks ran; the root verifies each claim.

Use actual Git history or already known commit references for traceability rather than inserting a future commit SHA into itself. Do not mark the task Finished while local capture, reconciliation, ownership or evidence remains unresolved. This convention does not grant new tracker, commit, push or global configuration permissions.

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
