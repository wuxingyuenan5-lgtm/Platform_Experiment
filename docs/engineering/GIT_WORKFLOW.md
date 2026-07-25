# Git Workflow and Version Governance

本项目不再把“分支”当成想法草稿。一个非简单任务必须先有 Issue，再有唯一分支和唯一 PR。

## 1. 唯一关系

```text
一个工程目标
  → 一个 GitHub Issue
  → 一个 tasks/issue-<number>-<slug>.md
  → 一个 <type>/issue-<number>-<slug> 分支
  → 一个引用该 Issue 的开放 PR
  → squash merge 到 main
```

同一 Issue 同时存在两个开放 PR，CI 失败。

## 2. 开始任务前

1. 搜索开放 Issue、PR 和 `tasks/`，确认没有同一结果正在进行。
2. 已有 Issue 时复用，不再创建“类似但换名字”的任务。
3. 创建或更新任务包，先写目标、非目标、受保护语义和验收命令。
4. 从最新 `main` 创建分支。

分支格式：

```text
feature/issue-123-add-report
fix/issue-124-recover-order
refactor/issue-125-split-accounting-module
hardening/issue-126-runtime-safety
 docs/issue-127-update-runbook
chore/issue-128-tooling
```

正式格式不能有空格；上面的 `docs/` 行仅表示类型示例，实际为：

```text
docs/issue-127-update-runbook
```

## 3. 哪些任务可以不建 Issue

仅限同时满足以下条件的本地一次性工作：

- 单文件或极小范围；
- 不跨会话；
- 不涉及交易、权限、数据库、部署、契约或资金安全；
- 不需要合并到远端正式分支。

只要需要提交 PR，就应有 Issue。

## 4. PR 规则

PR 第一行必须是：

```text
Issue: #123
```

PR 必须写明：

- 一个可衡量结果；
- Included / Excluded；
- 哪些业务语义不变；
- 实际执行的测试与 CI；
- 风险和回滚；
- 是否替代旧 PR。

不要在一个 PR 中顺手加入无关清理。

## 5. 需要换分支时

禁止先开第二条分支再决定用哪条。

正确顺序：

1. 在旧 PR 留下 `Superseded by #<new-pr>`；
2. 关闭旧 PR；
3. 更新任务包中的 Branch；
4. 从最新 `main` 创建新分支；
5. 新 PR 引用同一 Issue，并说明替代理由。

旧分支的提交仍保留在关闭 PR 中，不需要让旧分支长期停留在一个看似可发布的状态。

## 6. 合并方式

- 只通过 PR 进入 `main`。
- 默认 squash merge。
- 合并前必须基于当前 `main` 重新验证。
- CI、Secret Scan、架构检查和审查意见全部通过。
- 合并后关闭 Issue，清理或归位 head branch。

`main` 是唯一正式代码基线。功能版本、历史 PR 分支和任务分支都不能被描述为“另一套主版本”。

## 7. 版本标记

根目录 `VERSION` 是整个平台产品发布版本的唯一声明源。以下 maintained release 声明必须与其一致：

- `platform-backend/pyproject.toml` 的包版本；
- `execution-runtime/pyproject.toml` 的包版本；
- `admin-risk/.env` 的前端展示版本。

FastAPI 应用元数据和 Platform–Runtime 合约版本描述的是组件/API 兼容性，不随每个产品发布版本机械递增。`scripts/check-version-consistency.py` 与 CI 会阻止产品发布版本漂移。

Tag 只用于经过验收、需要明确回滚或部署识别的稳定点，例如：

```text
engineering-baseline-2026-07
v0.7.0-rc1
v0.7.0
```

不要为每次提交打 Tag。普通工作通过 Issue、PR、squash commit 追踪。

## 8. 跨对话续接

新对话只需要提供：

```text
仓库：wuxingyuenan5-lgtm/Platform_Experiment
Issue：#123
任务包：tasks/issue-123-xxx.md
请先核验 main、Issue、分支和开放 PR，再继续。
```

Agent 默认读取：

1. `AGENTS.md`；
2. `docs/codex/current-state.md`；
3. 对应任务包；
4. 模块入口和直接相关文件。

不要复制整段旧聊天，也不要要求重新扫描全仓。

## 9. 分支清理判断

满足以下全部条件可清理或归位：

- PR 已关闭；
- 工作已由另一个合并 PR完整取代，或该分支只有临时生成脚本/诊断工作流；
- 重要历史可由关闭 PR 和 commit SHA 找回；
- 与当前 `main` 比较后没有未迁移的独立业务成果。

不确定时不删除，先在 Issue 中记录差异和归属。

## 10. 机器门禁

- `scripts/check-workstream.py`：Issue、分支、任务包、PR 唯一关系。
- `scripts/check-repository-structure.py`：架构、上下文、数据库和契约结构。
- `scripts/check-version-consistency.py`：产品发布版本一致性。
- Platform CI：Ruff、Pyright、Pytest、Frontend ESLint/type/build。
- Secret Scan：阻止凭证材料进入仓库。

规则被机器执行后，文档不再只是建议。
