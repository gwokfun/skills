---
name: project-specs
description: "Save published specs and tickets locally and reconcile verified behavior with lasting project specifications. Use when a project enables spec maintenance or the user asks to preserve change documents; do not replace the issue tracker or generate new requirements."
---

# Project Specs

Preserve change history and maintain the project's current behavior specifications. This is a fork-owned, model-invoked helper for Codex. Read [the persistence contract](./references/contract.md) before writing or checking records.

## Scope and activation

Read the project's `docs/agents/workflow.md` and tracker configuration. The configured workflow must contain the exact line `Project spec maintenance: enabled` before the bundled tool can write. An explicit request without that configuration may receive a draft and activation instructions, not silent configuration changes. Missing or disabled maintenance keeps the standard skills unchanged.

This skill does not invoke user-only skills, create or edit issues, close tickets, change global configuration, commit, push, or spawn agents. The root owns document semantics and verifies the supplied evidence. Follow the project's existing architect and ownership rules.

## Capture published content

After `to-spec` publishes, save its actual published body and known issue reference. Confirming test seams does not mean the user approved the entire final body; record the actual approval basis. After `to-tickets` publishes its approved breakdown, save each known ticket separately. Use complete bodies already available in the conversation or complete tracker reads; stop on truncation instead of storing a summary as the original.

For a local tracker, capture the saved source file under its existing convention. Keep its source reference. Use stable change and ticket IDs across retries; partial publication does not authorize publishing again. The remote/local tracker remains authoritative for live task status. Captures are versioned content records, not a second queue.

Use the bundled tool's `capture` command with the source packet described in the contract. Original bodies are immutable. On source drift, report the difference and obtain an explicit reconciliation decision; an approved body revision goes in a new revision path. Never overwrite history or push local edits back to the tracker.

## Reconcile before review and commit

Read relevant current capability docs before designing changes. The designated integration session owns shared capability files; parallel workers or ticket sessions provide proposed deltas for that owner to merge serially. Preserve unrelated text and include only agreed behavior demonstrated by actual checks. Proposed or partially implemented requirements stay in change history.

After behavior verification, before `implement` invokes its internal `code-review`, prepare a complete updated capability body, the expected current file SHA-256 (or null for a new file), actual verification results, deviations, and hashes of the implementation files those results covered. Capture a spec first. Run `reconcile`, then `check`. Include both the updated capability and verification record in the task's reviewed paths.

Any behavior-changing fix requires new verification, a new update ID, reconciliation, and a new review snapshot. `check` rejects a changed implementation basis or documentation record. It validates recorded provenance, not the truth of a test claim. Do not mark a task Finished while reconciliation is pending or a supporting source is stale.

Use Git history or already existing commit references for traceability. Do not write the not-yet-created commit's SHA into a document contained in that same commit. Handle glossary terms and significant ADR decisions through existing domain conventions, without putting requirements in the glossary.

## Outcome

Return `status: complete | blocked | failed`, changed or checked paths, source references and revisions, evidence actually verified, and gaps. A successful local capture does not prove remote publication or task completion. Report failures and preserve completed files so the same known IDs can resume safely.
