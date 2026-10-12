# Persistence contract

Python 3.11+ is required. All commands take `--repo <absolute-project-root>` and `--change <stable-lowercase-id>`. IDs use lowercase letters, digits and hyphens, up to 64 characters. Resolve IDs once in the handoff; an issue title rename does not create a new change.

The project's workflow explicitly enables maintenance. Reuse existing capability naming when choosing an ID. The first version writes under tracked `docs/changes/` and `docs/specs/`; it does not migrate existing documentation. Check Git ignore rules and authorization before writing. Do not force-add ignored records.

## Layout and ownership

```text
docs/changes/<change-id>/spec.md
docs/changes/<change-id>/tickets/<ticket-id>.md
docs/changes/<change-id>/revisions/<revision-id>/spec.md
docs/changes/<change-id>/revisions/<revision-id>/tickets/<ticket-id>.md
docs/changes/<change-id>/verification/<capability-id>/<update-id>.md
docs/specs/<capability-id>.md
```

Each file has a JSON-compatible YAML frontmatter record followed by its complete Markdown body. Content is stored as UTF-8 with CRLF normalized to LF; body digests and captured-spec provenance use that canonical representation so Git newline conversion does not corrupt records. The expected current capability digest and implementation hashes cover actual whole-file bytes for conflict checks. Captures preserve the complete source text, and metadata does not claim a different approval than the source supports. The verification history stores the verified candidate, its implementation basis and the previous capability digest. It is not marked as applied simply because it exists: `check` must confirm it agrees with the current capability.

The tool serializes its writes with a temporary `docs/.project-specs.lock` and checks file digests immediately before replacement. Assign one integration session to shared capability files; this lock is not a permission system for arbitrary editors. A different file version requires rereading, merging, verifying and reviewing again. Following a hard process crash, inspect the lock's owner/PID and unfinished records before explicitly removing a stale lock. Never remove another live writer's lock.

Manual edits that invalidate frontmatter/body provenance are deliberately blocked, even with a matching current file digest. Preserve the exact edited file in the change's manual-edit history and compare it with the last valid verification record or Git version. Prepare and verify the merged body first. A separately reviewed repair may restore the last valid record and then reconcile the merged body with a new update ID and the restored file's digest, retaining the saved edits in review scope. Do not silently restamp invalid metadata or discard the edits. An existing plain document with no valid prior record needs an explicit reviewed adoption/migration; this tool does not perform it. The cooperative lock does not make replacement an atomic compare-and-swap against arbitrary external editors, so exclusive integration ownership and final review checks remain necessary.

## Capture packet

Prepare the packet outside tracked documentation, using actual publication results. Never include credentials or unrelated API response fields.

```json
{
  "schema_version": 1,
  "body": "# Actual published spec\n...\n",
  "source": {
    "tracker": "github",
    "ref": "https://github.com/owner/repo/issues/123",
    "revision": "actual updated_at or content digest",
    "observed_at": "2026-10-13T00:00:00Z",
    "approval_basis": "seams-confirmed"
  }
}
```

`tracker` is `github`, `gitlab`, or `local`. Remote references are complete HTTPS issue URLs. Local references are repository-relative existing files whose UTF-8 body must match the packet. `revision` identifies the observed source version; record a body digest when no source version is available. `observed_at` is the actual UTC observation time. Approval bases are `seams-confirmed`, `breakdown-approved`, `body-approved`, or `not-recorded`; do not invent approval. Spec publication requires a known source reference; unpublished drafts remain drafts outside these records.

```text
python <installed-project-specs>/scripts/store.py capture --repo <project> --change <id> --kind spec --input <packet.json>
python <installed-project-specs>/scripts/store.py capture --repo <project> --change <id> --kind ticket --ticket <id> --input <packet.json>
python <installed-project-specs>/scripts/store.py check-source --repo <project> --change <id> --kind spec --input <fresh-source-packet.json>
```

Same source and body is a no-op and preserves the first observation. A different body or source is drift. After explicit approval of the changed body, capture with `--revision <new-id>` and `approval_basis: body-approved`; the original remains intact. To compare that revision, pass the same `--revision` to `check-source`. Fetch current source bodies at handoff/review when needed, without applying local changes remotely. Ticket status alone is not synchronized here.

## Reconciliation packet

Only the integration owner prepares the full capability body. Gather actual checks first and retain the file content hashes those checks covered. Use a new stable update ID after each behavior-changing fix; retries reuse the exact same packet. Hash the entire current capability file, including frontmatter, for `expected_sha256`.

```json
{
  "schema_version": 1,
  "capability": "codex-initialization",
  "update": "ticket-123-pass-1",
  "writer": "integration-session-reference",
  "observed_at": "2026-10-13T00:00:00Z",
  "expected_sha256": null,
  "spec_revision": null,
  "body": "# Codex initialization\n\n## Requirements\n...\n",
  "verification": [{"check": "actual check command or manual observation", "result": "passed"}],
  "implementation": {"src/feature.py": "actual-file-sha256", "src/deleted.py": null},
  "deviations": []
}
```

`implementation` must include the task files the checks covered, with entire-file SHA-256 or null for deletion. Include relevant tests/configuration as well as code. Do not include the capability output, its verification record or runtime lock in that basis, since that would create a hash cycle. The root must verify completeness; the tool cannot discover an omitted task file or prove an assertion was tested. `verification` requires nonempty actual checks with `result: passed`; ordinary exceptions use `deviations` and the project's approved scope, not fabricated passes.

```text
python <installed-project-specs>/scripts/store.py reconcile --repo <project> --change <id> --input <packet.json>
python <installed-project-specs>/scripts/store.py check --repo <project> --change <id> --capability <id> --update <id>
```

`spec_revision` selects an approved captured revision, or null selects the original. Reconciliation first validates the captured spec, implementation hashes and expected capability version. It writes an immutable verification candidate, then atomically updates the capability. If interrupted between those steps, retry the same packet: the candidate is reused and the capability update is resumed. If capability replacement succeeded but the response was lost, the same packet is a no-op. User-edited files or different content at an existing update ID are conflicts, never permission to overwrite.

Check the capability and verification record before freezing review input and again after review. Changed code invalidates the recorded basis, requiring fresh evidence and a new update ID. All affected documents belong in the reviewed/staged task paths. Post-commit validation uses the actual commit and Git history, rather than regenerating documents after the review.
