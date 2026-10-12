## What it does

`setup-matt-pocock-skills` answers three questions about one repo: where issues live, what the triage labels are called, and where the domain docs sit. It records the answers as markdown files under `docs/agents/`.

Those files are the only thing that varies between repos. The skills themselves are identical everywhere. They read `docs/agents/issue-tracker.md` at run time and do what it says. That is why the set is not tied to GitHub, and why you never edit a skill file to point it at another tracker. Invoking it with "link the skills to a custom issue tracker" works with anything you can connect to programmatically, with no changes to the skills.

It is a prompt-driven skill, not a deterministic script. It reads your `git remote`, `CLAUDE.md` and `GLOSSARY.md`, proposes what it found, and waits for you to confirm before it writes anything.

This fork adds an explicit Codex initialization branch. It audits configuration and existing [sub-agent](https://www.aihero.dev/ai-coding-dictionary/subagent) definitions, proposes the requested models and workflow guards, and returns an analysis with Unified Diffs. The entire first phase is read-only. Only your `go` for that displayed initialization proposal permits applying it.

## When to reach for it

You invoke this by typing `/setup-matt-pocock-skills`; the [agent](https://www.aihero.dev/ai-coding-dictionary/agent) won't reach for it on its own. Its metadata marks it non-invokable on purpose, so no other skill can fire it for you.

Reach for it once per repo, before the first use of any other engineering skill. If [triage](https://aihero.dev/skills-triage), [to-spec](https://aihero.dev/skills-to-spec), [to-tickets](https://aihero.dev/skills-to-tickets) or [wayfinder](https://aihero.dev/skills-wayfinder) start guessing where your issues go, or apply labels your tracker doesn't have, this repo has not been set up yet. You can run it in a repo halfway through a project. The skill reads what is already there, so no earlier work is lost.

For this fork's Codex branch, explicitly ask the skill to initialize Codex subagents and the engineering workflow. A normal tracker setup request keeps the standard process. The branch requires this fork's bundled assets; installing the canonical upstream set alone does not include it.

## Prerequisites

It writes into the repo you run it in:

| It writes | Where |
| --- | --- |
| `issue-tracker.md` | `docs/agents/` |
| `domain.md` | `docs/agents/` |
| `triage-labels.md` | `docs/agents/`, only when the `triage` skill is installed |
| An `## Agent skills` block | whichever of `CLAUDE.md` or `AGENTS.md` already exists |

The standard setup records project configuration as markdown. The Codex branch separately proposes three user-level defaults (`model`, `model_reasoning_effort`, and `approvals_reviewer`) and project assets: missing native role files, managed blocks in `AGENTS.md`, `docs/agents/subagents.md`, and `docs/agents/workflow.md`, and their provenance in `.codex/workflow-state.json`. Every proposed file is visible before approval. Existing roles pinned to another model and conflicting override sources are preserved and reported.

Optional project-spec maintenance requires this fork's separately installed `project-specs` beta. Ask explicitly to enable local change history and capability docs. Setup checks availability and proposes the workflow setting; it does not install the helper or generate empty spec folders. Existing projects remain disabled unless explicitly enabled. Missing helper availability blocks the enabled proposal.

## The three decisions

It starts each section with the recommended answer, and skips any question its exploration already answered. Most runs need only two confirmations.

| Decision | What it proposes | When it asks |
| --- | --- | --- |
| **Issue tracker** | the one matching your `git remote` | always, because this is the one real choice |
| **Triage labels** | keep the five canonical names (`needs-triage`, `needs-info`, `ready-for-agent`, `ready-for-human`, `wontfix`) | only if the `triage` skill is installed |
| **Domain docs** | single-context: one `GLOSSARY.md` plus `docs/adr/` at the root | only if it spots monorepo signals, and then it offers a multi-context `GLOSSARY-MAP.md` |

The tracker options:

| Option | Where issues live | Needs |
| --- | --- | --- |
| **GitHub** | the repo's GitHub Issues | the `gh` CLI |
| **GitLab** | the repo's GitLab Issues | the `glab` CLI |
| **Local markdown** | files under `.scratch/<feature>/` in this repo | nothing, not even a remote |
| **Other** | wherever you say | one paragraph from you describing the workflow |

The first three ship as templates in the skill and work out of the box. Local markdown is a full option, not a fallback. The skill supports a solo project with no remote. One caveat: don't use local markdown if you use GitHub. They are alternatives, so pick one.

"Other" is a full option too. It is how Jira, Linear, Azure DevOps and Beads all work. You describe the workflow, the skill records your prose in `docs/agents/issue-tracker.md`, and the downstream skills follow the prose. Users have already built this: a Jira-over-[MCP](https://www.aihero.dev/ai-coding-dictionary/mcp) variant, a Gitea CLI shaped like `gh`, a hand-built local dashboard.

## Common questions

**Do I have to use GitHub?**

No. GitHub, GitLab and local markdown under `.scratch/` all ship as ready-made templates, and anything else works through the "other" path. This is the most-repeated question, in roughly these words: *"hard locked to github"*, *"can I use GitLab / Jira"*, *"what about Azure DevOps"*. The answer is always the same: setup chooses the tracker, not the skill.

**Do I need to re-run it after updating the skills?**

Re-run standard setup when tracker conventions need updating. Updating this fork's skills does not automatically regenerate consumer Codex configuration. An explicit Codex rerun checks managed-block digests: identical blocks produce no change, user-edited blocks or missing provenance produce a conflict report, and any new proposal needs its own `go`.

The previous version-1 Codex workflow can be proposed for upgrade to version 2 after its recorded digest is verified. Surrounding text is preserved, and the new maintenance switch defaults to disabled. The marker and provenance changes appear in the same reviewed Diff. An edited old block remains a conflict.

**It wrote to `CLAUDE.md`, but I'm on Codex.**

The standard path retains its Claude-first selection rule. This fork's explicit Codex initialization path targets `AGENTS.md`, creating it when needed even if `CLAUDE.md` exists. It preserves existing content and pointers. The choice depends on the initialization request, not just which [harness](https://www.aihero.dev/ai-coding-dictionary/harness) happens to be running.

**It didn't create my triage labels.**

`docs/agents/triage-labels.md` maps tracker strings to canonical roles. The standard GitHub path also checks for missing mapped labels and creates them after configuration is confirmed. The Codex branch's first phase only reports proposed label creation; external changes require explicit inclusion in the approved proposal. Two limits remain:

- If your tracker already uses the canonical names, the mapping is an identity table and there is nothing to configure. That is the intended common case, not a missing step.
- The triage-label step does not provision [wayfinder](https://aihero.dev/skills-wayfinder)'s `wayfinder:map` and `wayfinder:<type>` labels. Follow the tracker's wayfinding operations before publishing a map.

**Can I configure the other skills' behaviour here ([grilling](https://www.aihero.dev/ai-coding-dictionary/grilling) cadence, question format, tone)?**

The standard path configures tracker, labels, and doc layout. This fork's explicit Codex branch adds subagent and workflow instructions, including handoffs and architect guards. General preferences still belong in your project's instruction file or the invocation.

**Can I keep the config in `~/.claude` instead of committing it to every repo?**

Tracker and workflow documents remain project-local under `docs/agents/`. The Codex branch can propose global model defaults, but it does not move project workflow state into a shared user directory.

**Isn't it strange to have a skill that configures the other skills?**

One long-standing complaint says yes, in these words: *"having a skill to set up the other skill does not feel right to me: that means the LLM is configuring its own skills."* The trade-off is real. Without a setup step, every skill that touches issues would need its own copy of the tracker instructions. The output is markdown you can read and edit, and that limits the risk. You can read every file it wrote and change it by hand. Make day-to-day changes that way, not with another run.

## It's working if

- `docs/agents/issue-tracker.md` and `docs/agents/domain.md` exist, plus `triage-labels.md` if `triage` is installed.
- An `## Agent skills` section appears in the instruction file your harness reads, with a one-line summary pointing at each of those files.
- The tracker it proposed matches the remote you use, and the label strings match labels that exist in your tracker.
- Afterwards, `/to-tickets` publishes without asking you where issues live, and `/triage` applies labels rather than inventing them.
- Nothing in the skill files themselves changed. If setup edited a `SKILL.md`, something went wrong.
- A Codex initialization shows the complete report and Diff before any write, lists preserved model pins and unresolved overrides, and waits for your scoped `go`.
- A Codex rerun preserves surrounding user text and reports changed managed blocks instead of silently replacing them. Saved settings and observed runtime behavior are reported separately.

## Where it fits

`setup-matt-pocock-skills` is the **run-once setup** for the engineering flow, the precondition everything else assumes rather than a step in the chain. Its neighbours are its readers: [triage](https://aihero.dev/skills-triage), which applies the label vocabulary written here; [to-spec](https://aihero.dev/skills-to-spec) and [to-tickets](https://aihero.dev/skills-to-tickets), which publish into the tracker named here; and [wayfinder](https://aihero.dev/skills-wayfinder), which reads the "Wayfinding operations" section of the same tracker file to learn how to store maps and child [tickets](https://www.aihero.dev/ai-coding-dictionary/ticket). [domain-modeling](https://aihero.dev/skills-domain-modeling) later fills in the domain-doc layout that setup records. It creates `GLOSSARY.md` and ADRs only when you resolve a term or decision, so a repo with no domain docs after setup is normal. For which skill to reach for next, [ask-matt](https://aihero.dev/skills-ask-matt) routes the whole set.
