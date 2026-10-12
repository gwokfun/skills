# Codex 工作流扩展与上游维护

本扩展只面向 Codex。初始化是一份供目标项目执行的提示词；开发、安装或更新本仓库不会自动更改当前用户的 Codex 配置。

## 使用入口

确保安装的是这个 fork 的 `setup-matt-pocock-skills` 和 `code-review`，以及工作流中的其他现有技能。README 中的规范安装命令指向上游，单独安装上游版本不会包含本扩展。避免同时安装同名的上游和 fork 技能；在 Codex 中核对实际加载的技能路径。

从本地仓库安装时，可以在目标项目目录执行以下选择安装。先确认安装器支持这些参数，并检查实际安装位置：

```text
npx skills add D:/matt-skills --agent codex --skill setup-matt-pocock-skills code-review grill-with-docs to-spec to-tickets implement grilling domain-modeling tdd codebase-design --copy --yes
```

初始化技能的整个目录都必须安装，包括 `codex-workflow/` 内的资源；审查技能必须带有 `WORKSPACE-REVIEW.md` 和 `scripts/review_snapshot.py`。只复制 `SKILL.md` 不完整。`grilling`、`domain-modeling`、`tdd` 和 `codebase-design` 是已有流程使用的基础技能，也需要安装。工作流不会自动启动其他 user-invoked 技能。

在目标项目显式调用：

```text
$setup-matt-pocock-skills 初始化 Codex 子代理与工程工作流，先输出只读分析报告和 Unified Diff。
```

阅读该次提案后，再回复 `go`。初始化先检查真实客户端、全局及项目配置、模型固定项和覆盖来源；不会把开发本扩展时的 `go` 当作初始化授权。首阶段禁止任何实际文件、标签、分支或状态写入。

## 目标设置与实际结果

| 对象 | 目标模型 | 推理力度 | 用途 |
| --- | --- | --- | --- |
| 主会话 | gpt-6.1-sol | high | 需求、取舍、实施和最终验收 |
| explorer | gpt-6-luna | medium | 只读代码扫描与定位 |
| worker | gpt-6.1-sol | medium | 明确文件所有权内的局部编码和测试 |
| researcher | gpt-6-luna | medium | 只读外部文档和 API 检索 |
| architect | gpt-6-astra | high | 仅按 A、B、C 触发的独立审查 |

`approvals_reviewer = "auto_review"` 是内部审批机制，不是可手工编排的 reviewer 角色。不同模型的既有固定项保持原样，不通过项目定义或调用参数覆盖。活动 profile、项目配置、启动参数等冲突仅报告；初始化的 `go` 不授权顺手修复它们。实际清单需要区分目标设置、已保存配置和已经核验的运行时结果。

角色文件采用当前 Codex 支持的独立 TOML 格式；旧客户端的格式、信任状态和模型可用性必须先检查。模型或权限没有运行验证时明确列为缺口，不能从静态模板推断只读权限已生效。

## 工作流与边界

```text
grill-with-docs -> to-spec -> to-tickets -> implement -> code-review
```

前三阶段保持需求上下文连续，按 ticket 开启新的实施会话。根 Agent 默认实施；只有互斥文件范围适合并行时才授权 worker。`implement` 保留内部调用 `code-review` 和提交的既有语义。收尾可再开独立审查会话核验整个 feature，使用之前记录的 feature 基线。

- A：大型跨模块 Execution Plan 生成前，由 Fresh architect 审查。
- B：任何测试失败，包括预期的 TDD RED，或同一非测试错误连续两次重试仍失败，暂停改动并由 Fresh architect 诊断。该规则会增加每次 RED 的审查成本，按原要求保留。
- C：长任务标记 Finished 前，由 Fresh architect 检查实际 Diff 和边界条件。
- D：仅给 architect 当前相关 Plan、Error Trace 或 Diff，不传无关日志。

`docs/agents/workflow.md` 中的 `Review input: workspace snapshot` 显式启用提交前快照审查。记录不可变基线、任务文件与初始用户改动；两个 Fresh explorer 分别审查 Standards 和 Spec。修改使旧快照失效。提交前检查索引和任务所有权，提交后核对实际产物。工具只支持普通文件，不能替根 Agent 判断哪些 hunk 属于用户。

## 扩展的归属与更新

开发基线：`49dd158d1076134a641b33efb035946536778336`。上游：`https://github.com/mattpocock/skills`。当前 fork：`https://github.com/gwokfun/skills`。没有新增技能或修改插件 manifest；所有初始化资源归属于现有 setup 技能，审查资源归属于现有 code-review 技能。

| 维护范围 | 文件 |
| --- | --- |
| 初始化提示词、模型定义、生成文档模板 | `skills/engineering/setup-matt-pocock-skills/codex-workflow/` |
| 最小初始化入口与 Codex 发现描述 | setup 技能的 `SKILL.md`、`agents/openai.yaml` |
| 可选工作区审查入口、说明和辅助工具 | code-review 技能的 `SKILL.md`、`WORKSPACE-REVIEW.md`、`scripts/review_snapshot.py` |
| 使用说明与路由同步 | 根 README、engineering README、ask-matt 技能及 setup、review、implement、ask-matt 的 docs 页 |
| 隔离验证 | `tests/codex_workflow/` |

更新上游时，在单独的同步分支合并上游，再核对以上小范围入口。保留上游标准流程，检查其模板、调用权限、两轴审查与安装契约是否变化，然后调整 fork 的独立资源。不要把扩展目录散落进五个技能，也不要直接修改已安装副本来解决冲突。

消费者的生成配置独立维护：三个文档使用带版本的管理块，`.codex/workflow-state.json` 保存各块的 SHA-256。上游更新不会自动重新初始化。显式重跑时，相同内容不改动；块内用户修改、缺失状态或标记冲突先报告并给出 Diff。原生角色文件仍由用户所有，既有模型固定项不受模板更新覆盖。管理块之外的文字保留原样。

## 验证与发布前检查

在临时项目中验证本地安装是否携带嵌套资源，并运行隔离测试：

```text
python -B -m unittest discover -s tests/codex_workflow -v
git diff --check
node scripts/sync-plugin-version.mjs --check
```

检查角色与全局片段可被 TOML 解析，用户调用权限保持一致，初始化首阶段没有写入，且固定模型和覆盖来源保留。以实际客户端验证加载；单纯解析成功不代表目标模型在当前会话运行。若上游改变了插件 manifest，按仓库要求补做插件验证。

提交或发布 fork 前核对完整差异。更新消费者安装与批准消费者初始化是两件独立的事；更新本扩展不会授权全局环境校准或自动迁移生成配置。
