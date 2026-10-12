# Codex subagent and workflow initialization

This is a reusable initialization prompt for the target environment where the user runs it. Developing or installing these assets does not authorize initializing the skill author's environment. Read this file only for an explicit Codex initialization request.

## Phase 1: inspect and propose, with zero writes

Do not create directories, reports, backups, state files, native definitions, Git branches, commits, labels, or other local or external state during this phase. Output the report and Unified Diff in the chat. Existing approval settings do not waive the initialization user's `go` requirement.

### Establish the target and supported format

Identify the target project and the actual Codex executable/client in use. Establish its version from read-only executable/package metadata or already available client evidence. Do not launch CLI commands that might bootstrap home directories, PATH helpers, caches, logs, or session state during this phase, even if named `--version` or `--help`. If a write-free check is unavailable, report the version/loading gap and defer command-based checks until approval. Inspect current official documentation:

- [Subagents](https://learn.chatgpt.com/docs/agent-configuration/subagents)
- [Configuration precedence](https://learn.chatgpt.com/docs/config-file/config-basic)
- [Configuration reference](https://learn.chatgpt.com/docs/config-file/config-reference)

The CLI on PATH and the desktop runtime can differ. The [native role templates](./roles/) use standalone TOML files with `name`, `description`, and `developer_instructions`. Verify the target loader supports that format before proposing them. For a legacy client, report the incompatibility and any documented alternative; do not guess keys or silently upgrade it. Confirm that project configuration will load for the target project's trust state; do not change trust settings yourself.

### Inspect configuration layers and role assets

Resolve the real Codex user configuration directory from the client's configuration and `CODEX_HOME`, falling back to `~/.codex`. Read only relevant fields, preserve secrets, and report unreadable or unknown layers as gaps:

- The user `config.toml`, user `agents/` TOML files, and selected profile files.
- The target project's applicable `.codex/config.toml` layers and `.codex/agents/` files.
- Referenced `[agents.<role>].config_file` definitions when supported by that client.
- Relevant selected profile, command aliases/wrappers, startup flags, environment overrides, and managed constraints when available. Do not dump credentials, complete process arguments, or unrelated configuration.

For each allowed role, list definition paths, precedence, configured model/effort, and whether the live loaded role is verified. Existing custom definitions, including legacy referenced files, count as existing assets. Built-in roles do not provide the requested explicit custom model settings; a missing custom definition can be proposed from a template. Duplicate, invalid, or unrecognized definitions are conflicts, not permission to overwrite.

Use [global-defaults.toml](./global-defaults.toml) for the proposed main defaults and the four [role templates](./roles/) as the single source of target role settings. They specify main `gpt-6.1-sol/high`, `approvals_reviewer = "auto_review"`, explorer `gpt-6-luna/medium`, worker `gpt-6.1-sol/medium`, researcher `gpt-6-luna/medium`, and architect `gpt-6-astra/high`.

- If an existing role explicitly specifies a different model, skip the role and list it as a preserved model pin. Do not shadow it with a project definition or override it in a spawn request.
- If an existing role has no model pin or has the target model with a different effort, list the needed adjustment and propose a minimal edit only. Preserve its instructions and unrelated fields.
- Propose new native files only for custom roles absent across the applicable user and project layers. Prefer project scope for those missing roles and show the scope in the Diff; do not duplicate a user role just because the project directory is empty.
- Propose the three main defaults as minimal edits to the actual user `config.toml`. The defaults fragment is never a replacement for that file. Preserve approval policy, sandbox, concurrency, providers, plugins, MCP servers, and unrelated settings.
- List profile, project, default-subagent, CLI, and live-session conflicts separately. Leave conflicting sources unchanged, even after `go`, unless a later instruction explicitly authorizes their resolution. Do not claim the target topology is achieved when a model pin or override remains.
- If a requested model or setting is unavailable or incompatible, report the gap without substituting a model.

### Draft the project workflow

Read the target project's `AGENTS.md`, `CLAUDE.md`, `docs/agents/`, and existing tracker/domain conventions. Preserve configured choices. If tracker or domain setup is missing, reuse the standard templates in this skill's parent directory: [GitHub](../issue-tracker-github.md), [GitLab](../issue-tracker-gitlab.md), [local files](../issue-tracker-local.md), [labels](../triage-labels.md), and [domain docs](../domain.md). Resolve required tracker choices with the user; draft all changes without executing label or tracker mutations. Include label creation in the proposal only if needed and explicitly in scope.

Draft these project outputs from the templates:

- [AGENTS.md block](./templates/AGENTS.md): append/update a bounded Codex block in the target project's `AGENTS.md`, preserving existing content and any `CLAUDE.md` pointer. Create `AGENTS.md` for this explicit Codex request even if only `CLAUDE.md` exists. This branch overrides the standard setup's Claude-first selection rule.
- [subagents.md](./templates/subagents.md): `docs/agents/subagents.md`, with delegation rules and the actual role inventory, preserved pins, and unresolved conflicts.
- [workflow.md](./templates/workflow.md): `docs/agents/workflow.md`, with the skill chain, handoffs, and opt-in workspace review contract.
- `.codex/workflow-state.json`: provenance for these three managed blocks, described below. Draft it in memory; it is not a native Codex configuration file.

Ensure `AGENTS.md` also points to the existing or proposed tracker, domain, and label documents. Put those pointers in the managed block and omit labels when triage is not installed. Fill the role inventory from observed evidence, not the preferred models alone. Note unavailable roles explicitly. Rules A-D remain literal, including rule B on expected TDD RED failures; explain that consequence without inventing an exemption.

### Preserve edits and support reruns

Each template contains one named begin/end block with `version=1`. Keep user text outside the block intact. The state file schema is:

```json
{
  "schema_version": 1,
  "template_version": 1,
  "blocks": {
    "AGENTS.md": {"block_id": "codex-agents", "sha256": "<digest>"},
    "docs/agents/subagents.md": {"block_id": "codex-subagents", "sha256": "<digest>"},
    "docs/agents/workflow.md": {"block_id": "codex-workflow", "sha256": "<digest>"}
  }
}
```

Replace each digest with SHA-256 of the exact block text including markers, normalized to LF, UTF-8 without a BOM. For hashing, take the begin marker through the end marker, discard any newline immediately after the end marker, then append exactly one LF. Preserve the target file's encoding and line endings when applying edits. On rerun, compare the current block with the recorded digest before proposing a replacement. Identical content is a no-op. User changes inside blocks require a conflict report and reviewed Diff. Missing state, missing/duplicate/altered markers, or unsupported versions must not cause wholesale replacement or another appended block; report the conflict and require explicit resolution. Existing native role definitions are user-owned and never become managed blocks.

### Report and stop

Return an analysis with:

1. Target project, client/version, configuration layers, and verified versus inferred loading behavior.
2. Role inventory: matches, proposed adjustments, preserved pins, missing definitions, conflicts, and gaps.
3. Exact files and any external operations proposed, with a distinction between global defaults and project setup.
4. A single complete set of Unified Diffs for all proposed file changes, including new files as `/dev/null` additions. Include `---`/`+++` headers and correct hunk counts. Never replace a file's Diff with a template link, summary, or "unchanged template" assertion. Fill each template's instruction section with actual content rather than appending a duplicate heading. Compute provenance from the exact displayed managed blocks. Avoid secret-bearing context; use zero-context hunks where needed.
5. Validation planned after approval and unresolved blockers.

Stop here until the user explicitly says `go` for this displayed initialization proposal. A `go` to develop, install, or update matt-skills is not approval for this initialization. If it arrives before a concrete proposal, complete the read-only proposal and obtain approval for it. A changed proposal or newly discovered conflict needs approval for the affected change.

## Phase 2: apply the approved proposal

Re-read each target and check that it still matches the inspected version. Apply only approved hunks and explicitly approved external operations. Preserve model pins and leave reported override sources untouched. Write provenance only after successful block edits, using the actual generated content's digests; do not record partial edits as complete. Do not commit or push initialization changes unless requested.

Validate TOML with a real parser, then check the actual client's supported configuration/role loading in a fresh session where possible. Check generated pointers, managed-block identity, and a read-only rerun for idempotence. Report saved configuration separately from observed runtime model/effort and permissions. Role instructions and `sandbox_mode` defaults alone do not prove read-only enforcement because live parent overrides can apply. Report unavailable validation instead of declaring success.

Finish with the files applied, preserved pins and remaining conflicts, checks actually run, and how to start the existing skill chain. No user-only skill is invoked automatically.
