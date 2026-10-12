# Opt-in Codex workspace review

Use this branch only when the target project's `docs/agents/workflow.md` explicitly contains `Review input: workspace snapshot`. Otherwise follow the standard fixed-point-to-HEAD process unchanged. This branch replaces the input capture and delegation in steps 1 and 4; retain the spec discovery, standards baseline, and separate reports in the other steps.

## Freeze the task input

Read the workflow handoff for the immutable base SHA agreed before implementation, the task's file scope, initial dirty state, spec, and test evidence. If the base is missing, obtain it from the user before reviewing; never infer it from today's HEAD. For whole-feature review use the recorded feature base. This comparison uses that exact base, rather than a moving three-dot merge-base.

Inspect committed, staged, unstaged, deleted, and untracked changes. Identify every task file, including both names of a rename. Record included and excluded paths and explain ownership at the hunk level when a file contains pre-existing user changes. A path list does not establish ownership. If task and user hunks cannot be separated, report the conflict and pause automatic committing. Do not stage, stash, reset, or commit to prepare the review.

Run the bundled [snapshot helper](./scripts/review_snapshot.py) with Python 3.11+ and Git. For example, using absolute paths appropriate to the target environment:

```text
python <installed-code-review>/scripts/review_snapshot.py capture --repo <project> --base <agreed-SHA> --path src/feature.py --path tests/test_feature.py --output <new-temporary-directory-outside-project>
```

Repeat `--path` for each exact repository-relative task file. The helper freezes the base-to-worktree patch and current file contents, with the base, HEAD, content/mode hashes, path list, and snapshot ID in `manifest.json`. Its selected working tree includes committed and uncommitted task content together. Deleted files remain in the manifest and patch. Use the frozen patch and copied files for review, including binary-file inspections where required. Collect the immutable commit list with `git log <manifest-base>..<manifest-head> --oneline` for spec discovery. Read unchanged context, standards, and the spec directly, but record their identity and verify they did not change before accepting the reports.

The helper writes only a new external snapshot directory. It does not stage or commit. It detects changes during capture; a later edit invalidates the review. It supports regular files and rejects symlinks, submodules, unmerged task files, ignored untracked files, directories, and custom Git filters. It also rejects a baseline file absent from the index while a same-name worktree file remains or has been recreated, because an index-based deletion patch would not describe that worktree content. Report that state for separate review without changing the user's index. If Python, Git, or supported inputs are unavailable, report the gap and pause this branch; never fall back to a HEAD diff that omits the task.

## Delegate the two axes

Create Fresh `explorer` agents with explicit `agent_type="explorer"` and `fork_turns="none"`, one per available axis. Respect loaded role definitions and preserved model pins. Do not create `default` or `reviewer`. If explorer is unavailable, report it and pause delegation. Parallelize only within available slots; use separate Fresh agents sequentially when needed. No Spec source still means no Spec agent.

Give each agent a self-contained read-only brief: the snapshot directory and ID, base SHA, included/excluded paths and ownership notes, the appropriate sources, required citations, report format, and the relevant brief from steps 3 and 4 of `SKILL.md`. Both agents must read the same frozen `review.patch` and `files/`. Explicitly prohibit editing, invoking this skill again, spawning other agents, or replacing frozen input with a fresh live diff. Require `status`, `summary`, `evidence`, and `gaps`; findings must cite `file:line`, a rule/spec line, and the relevant hunk. Keep their reasoning independent.

The root agent checks cited findings against the frozen input and reports Standards and Spec separately. Rule C's architect review is an additional boundary/diff check before a long task is Finished; architect does not replace either axis.

## Check validity and commit scope

After both reports and after every fix, run:

```text
python <installed-code-review>/scripts/review_snapshot.py check --repo <project> --snapshot <snapshot-directory>
```

If a check fails, or any supporting spec/standard/context changed, capture a new snapshot and obtain new reports. Before an authorized commit, stage only established task hunks, use literal Git pathspecs for explicit filenames, inspect the complete staged diff and task path list, and add `--index` to the check. It requires selected staged files to equal reviewed content and refuses unrelated staged paths. Preserve unrelated staged user work and resolve the commit scope explicitly; never unstage it to force this check through. The helper cannot establish hunk ownership or discover task paths omitted by its caller, so the root must verify both.

Immediately after committing, compare the actual commit's task file contents, modes, deletions, and full changed-path list with the snapshot. Do not use `check --index` after HEAD changes. A mismatch, extra task path, or concurrent edit means the final artifact still needs review; do not declare it reviewed or Finished. Committing is governed by the original task/skill authorization; this review branch does not grant it.
