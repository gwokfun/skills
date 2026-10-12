<!-- matt-skills:codex-subagents:begin version=1 -->
# Codex subagents

The root agent owns requirements, decisions, the implementation plan, direct verification, and delivery. It personally reads every exact file it will modify and every foundational design document.

## Delegation

- Use only `explorer`, `worker`, `researcher`, and `architect`. Specify `agent_type` explicitly; never fall back to `default` or `reviewer`. `approvals_reviewer = "auto_review"` is internal approval routing, not another manually spawned role.
- Keep small known tasks in the root. Delegate bounded exploration, independent checks, or independent work that reduces context load or provides useful parallelism.
- Create independent agents with `fork_turns="none"`. Give each one a unique goal, necessary context, scoped inputs and exclusions, permissions, prohibitions, success criteria, and expected evidence.
- `explorer` and `researcher` gather read-only evidence. Root implementation is the default. Give `worker` writes only with explicit, mutually exclusive file ownership; preserve user and other-agent changes.
- Invoke `architect` only under rules A, B, or C in `AGENTS.md`, with minimal inputs under D. It does not implement or run fixes.
- Respect the runtime's available slots and configured limits. Normally use at most three simultaneous exploration tasks and reserve a slot for follow-up or review; never change concurrency just to reach that count.
- Reports have `status: complete | blocked | failed`, `summary`, precise `evidence`, and `gaps`. Root checks cited locations and actual changes. Static configuration and agent reports are not runtime proof.
- An agent returns one complete report and stops. If it runs for about ten minutes, inspect usable partial results and stop an abnormal run before taking over or narrowing the task. Retry the same failed strategy at most once.

## Failure guard

Any test failure triggers architect B immediately, including the RED step of TDD. A worker reports it to the root, which pauses code changes and invokes architect. For non-test errors, count consecutive retries of the same operation and error class, excluding the original failure. Trigger after the second retry still fails; reset after success or a different operation/error. Architect diagnosis does not waive the next failure guard.

## Effective role inventory

The initializer fills this section with observed definition paths, configured models and efforts, preserved model pins, unresolved overrides, and availability for all four roles. Saved settings and verified fresh-session behavior must be identified separately. Keep explicit existing model pins; do not shadow them to meet preferred defaults.
<!-- matt-skills:codex-subagents:end -->
