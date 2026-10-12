<!-- matt-skills:codex-agents:begin version=1 -->
## Codex engineering workflow

Read `docs/agents/subagents.md` for the role inventory and delegation rules.
Read `docs/agents/workflow.md` for stage handoffs and review inputs.

### Architect guards

- A: Before generating a large Execution Plan involving multiple modules, invoke a Fresh `architect` to review the architecture.
- B: On any test failure, including expected TDD RED, pause code changes and invoke `architect` to diagnose the investigation path. Also trigger when the same error persists through two consecutive retries.
- C: Before marking a long task Finished, invoke a Fresh `architect` to review the final Diff and verify boundary conditions against the Plan and verification evidence.
- D: Give `architect` only the relevant Plan, Error Trace, or Diff. Keep unrelated terminal logs and private configuration out of its context.

If a required role is unavailable, report the missing role and pause the guarded step. Do not substitute a canceled or general fallback role.
<!-- matt-skills:codex-agents:end -->
